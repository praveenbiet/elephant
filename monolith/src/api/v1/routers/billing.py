from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, validator

from src.common.database import get_db
from src.common.auth import get_current_user
from src.modules.billing.services.payment_service import PaymentService
from src.modules.billing.services.invoice_service import InvoiceService

router = APIRouter(prefix="/billing", tags=["Billing"])

# Request/Response Models
class PaymentMethodBase(BaseModel):
    """Base payment method model."""
    type: str = Field(..., description="Payment method type: 'card', 'paypal', etc.")
    is_default: bool = False

class CardPaymentMethodRequest(PaymentMethodBase):
    """Card payment method request model."""
    card_number: str = Field(..., description="Credit card number", regex=r"^\d{16}$")
    expiry_month: int = Field(..., ge=1, le=12)
    expiry_year: int = Field(..., ge=2023, le=2050)
    cardholder_name: str
    
    @validator("type")
    def validate_type(cls, v):
        if v != "card":
            raise ValueError("Type must be 'card' for card payment methods")
        return v

class PayPalPaymentMethodRequest(PaymentMethodBase):
    """PayPal payment method request model."""
    email: str
    
    @validator("type")
    def validate_type(cls, v):
        if v != "paypal":
            raise ValueError("Type must be 'paypal' for PayPal payment methods")
        return v

class PaymentMethodResponse(BaseModel):
    """Payment method response model."""
    id: UUID
    type: str
    is_default: bool
    last_four: Optional[str] = None
    expiry_month: Optional[int] = None
    expiry_year: Optional[int] = None
    cardholder_name: Optional[str] = None
    email: Optional[str] = None
    created_at: str
    
    class Config:
        from_attributes = True

class InvoiceItem(BaseModel):
    """Invoice item model."""
    description: str
    amount: float
    quantity: int
    
    class Config:
        from_attributes = True

class Invoice(BaseModel):
    """Invoice model."""
    id: UUID
    invoice_number: str
    user_id: UUID
    amount: float
    status: str
    invoice_date: str
    due_date: str
    payment_date: Optional[str] = None
    items: List[InvoiceItem]
    
    class Config:
        from_attributes = True

class CreateInvoiceRequest(BaseModel):
    """Create invoice request model."""
    items: List[Dict[str, Any]]
    due_date: str

class PayInvoiceRequest(BaseModel):
    """Pay invoice request model."""
    payment_method_id: UUID

# Routes
@router.post("/payment-methods/card", response_model=PaymentMethodResponse, status_code=status.HTTP_201_CREATED)
async def create_card_payment_method(
    payment_method_data: CardPaymentMethodRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new card payment method.
    
    Adds a credit card as a payment method for the user.
    """
    payment_service = PaymentService(db)
    
    try:
        payment_method = await payment_service.create_card_payment_method(
            user_id=UUID(current_user["sub"]),
            card_number=payment_method_data.card_number,
            expiry_month=payment_method_data.expiry_month,
            expiry_year=payment_method_data.expiry_year,
            cardholder_name=payment_method_data.cardholder_name,
            is_default=payment_method_data.is_default
        )
        
        return PaymentMethodResponse(
            id=payment_method.id,
            type=payment_method.type,
            is_default=payment_method.is_default,
            last_four=payment_method.last_four,
            expiry_month=payment_method.expiry_month,
            expiry_year=payment_method.expiry_year,
            cardholder_name=payment_method.cardholder_name,
            created_at=payment_method.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/payment-methods/paypal", response_model=PaymentMethodResponse, status_code=status.HTTP_201_CREATED)
async def create_paypal_payment_method(
    payment_method_data: PayPalPaymentMethodRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new PayPal payment method.
    
    Adds a PayPal account as a payment method for the user.
    """
    payment_service = PaymentService(db)
    
    try:
        payment_method = await payment_service.create_paypal_payment_method(
            user_id=UUID(current_user["sub"]),
            email=payment_method_data.email,
            is_default=payment_method_data.is_default
        )
        
        return PaymentMethodResponse(
            id=payment_method.id,
            type=payment_method.type,
            is_default=payment_method.is_default,
            email=payment_method.email,
            created_at=payment_method.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/payment-methods", response_model=List[PaymentMethodResponse])
async def list_payment_methods(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List payment methods.
    
    Returns a list of payment methods for the user.
    """
    payment_service = PaymentService(db)
    payment_methods = await payment_service.list_payment_methods(
        user_id=UUID(current_user["sub"])
    )
    
    result = []
    for method in payment_methods:
        response = PaymentMethodResponse(
            id=method.id,
            type=method.type,
            is_default=method.is_default,
            created_at=method.created_at.isoformat()
        )
        
        if method.type == "card":
            response.last_four = method.last_four
            response.expiry_month = method.expiry_month
            response.expiry_year = method.expiry_year
            response.cardholder_name = method.cardholder_name
        elif method.type == "paypal":
            response.email = method.email
        
        result.append(response)
    
    return result

@router.put("/payment-methods/{payment_method_id}/default", response_model=PaymentMethodResponse)
async def set_default_payment_method(
    payment_method_id: UUID = Path(..., description="The ID of the payment method to set as default"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Set default payment method.
    
    Sets the specified payment method as the default for the user.
    """
    payment_service = PaymentService(db)
    
    try:
        payment_method = await payment_service.set_default_payment_method(
            user_id=UUID(current_user["sub"]),
            payment_method_id=payment_method_id
        )
        
        response = PaymentMethodResponse(
            id=payment_method.id,
            type=payment_method.type,
            is_default=payment_method.is_default,
            created_at=payment_method.created_at.isoformat()
        )
        
        if payment_method.type == "card":
            response.last_four = payment_method.last_four
            response.expiry_month = payment_method.expiry_month
            response.expiry_year = payment_method.expiry_year
            response.cardholder_name = payment_method.cardholder_name
        elif payment_method.type == "paypal":
            response.email = payment_method.email
        
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/payment-methods/{payment_method_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_method(
    payment_method_id: UUID = Path(..., description="The ID of the payment method to delete"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete payment method.
    
    Removes a payment method for the user.
    """
    payment_service = PaymentService(db)
    
    try:
        success = await payment_service.delete_payment_method(
            user_id=UUID(current_user["sub"]),
            payment_method_id=payment_method_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment method not found"
            )
        
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/invoices", response_model=List[Invoice])
async def list_invoices(
    status: Optional[str] = Query(None, description="Filter by status: 'pending', 'paid', 'overdue'"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List invoices.
    
    Returns a list of invoices for the user.
    """
    invoice_service = InvoiceService(db)
    
    if status and status not in ["pending", "paid", "overdue"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be one of: 'pending', 'paid', 'overdue'"
        )
    
    invoices = await invoice_service.list_invoices(
        user_id=UUID(current_user["sub"]),
        status=status,
        limit=limit,
        offset=offset
    )
    
    return [
        Invoice(
            id=invoice.id,
            invoice_number=invoice.invoice_number,
            user_id=invoice.user_id,
            amount=invoice.amount,
            status=invoice.status,
            invoice_date=invoice.invoice_date.isoformat(),
            due_date=invoice.due_date.isoformat(),
            payment_date=invoice.payment_date.isoformat() if invoice.payment_date else None,
            items=[
                InvoiceItem(
                    description=item.description,
                    amount=item.amount,
                    quantity=item.quantity
                ) for item in invoice.items
            ]
        ) for invoice in invoices
    ]

@router.get("/invoices/{invoice_id}", response_model=Invoice)
async def get_invoice(
    invoice_id: UUID = Path(..., description="The ID of the invoice to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific invoice by ID.
    
    Returns the details of an invoice.
    """
    invoice_service = InvoiceService(db)
    invoice = await invoice_service.get_invoice(
        user_id=UUID(current_user["sub"]),
        invoice_id=invoice_id
    )
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    return Invoice(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        user_id=invoice.user_id,
        amount=invoice.amount,
        status=invoice.status,
        invoice_date=invoice.invoice_date.isoformat(),
        due_date=invoice.due_date.isoformat(),
        payment_date=invoice.payment_date.isoformat() if invoice.payment_date else None,
        items=[
            InvoiceItem(
                description=item.description,
                amount=item.amount,
                quantity=item.quantity
            ) for item in invoice.items
        ]
    )

@router.post("/invoices/{invoice_id}/pay", response_model=Invoice)
async def pay_invoice(
    payment_data: PayInvoiceRequest,
    invoice_id: UUID = Path(..., description="The ID of the invoice to pay"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Pay an invoice.
    
    Processes payment for an invoice using the specified payment method.
    """
    invoice_service = InvoiceService(db)
    payment_service = PaymentService(db)
    
    # Verify invoice exists and belongs to user
    invoice = await invoice_service.get_invoice(
        user_id=UUID(current_user["sub"]),
        invoice_id=invoice_id
    )
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    if invoice.status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice has already been paid"
        )
    
    # Verify payment method exists and belongs to user
    payment_method = await payment_service.get_payment_method(
        user_id=UUID(current_user["sub"]),
        payment_method_id=payment_data.payment_method_id
    )
    
    if not payment_method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    try:
        updated_invoice = await invoice_service.pay_invoice(
            invoice_id=invoice_id,
            payment_method_id=payment_data.payment_method_id
        )
        
        return Invoice(
            id=updated_invoice.id,
            invoice_number=updated_invoice.invoice_number,
            user_id=updated_invoice.user_id,
            amount=updated_invoice.amount,
            status=updated_invoice.status,
            invoice_date=updated_invoice.invoice_date.isoformat(),
            due_date=updated_invoice.due_date.isoformat(),
            payment_date=updated_invoice.payment_date.isoformat() if updated_invoice.payment_date else None,
            items=[
                InvoiceItem(
                    description=item.description,
                    amount=item.amount,
                    quantity=item.quantity
                ) for item in updated_invoice.items
            ]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
