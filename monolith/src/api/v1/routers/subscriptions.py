from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.common.database import get_db
from src.common.auth import get_current_user
from src.modules.subscription.services.subscription_service import SubscriptionService
from src.modules.subscription.services.plan_service import PlanService

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

# Request/Response Models
class PlanFeature(BaseModel):
    """Subscription plan feature model."""
    name: str
    description: str
    
    class Config:
        from_attributes = True

class Plan(BaseModel):
    """Subscription plan model."""
    id: UUID
    name: str
    description: str
    price_monthly: float
    price_yearly: float
    features: List[PlanFeature]
    is_active: bool
    
    class Config:
        from_attributes = True

class SubscriptionBase(BaseModel):
    """Base subscription model."""
    plan_id: UUID
    billing_cycle: str = Field(..., description="Billing cycle: 'monthly', 'yearly'")

class SubscriptionCreateRequest(SubscriptionBase):
    """Subscription creation request model."""
    pass

class SubscriptionUpdateRequest(BaseModel):
    """Subscription update request model."""
    plan_id: Optional[UUID] = None
    billing_cycle: Optional[str] = Field(None, description="Billing cycle: 'monthly', 'yearly'")
    auto_renew: Optional[bool] = None

class SubscriptionResponse(BaseModel):
    """Subscription response model."""
    id: UUID
    user_id: UUID
    plan: Plan
    status: str
    billing_cycle: str
    start_date: str
    end_date: str
    auto_renew: bool
    cancel_at_period_end: bool
    
    class Config:
        from_attributes = True

class CancelSubscriptionRequest(BaseModel):
    """Cancel subscription request model."""
    cancel_immediately: bool = False

# Routes
@router.get("/plans", response_model=List[Plan])
async def list_plans(
    db: AsyncSession = Depends(get_db)
):
    """
    List subscription plans.
    
    Returns a list of available subscription plans.
    """
    plan_service = PlanService(db)
    plans = await plan_service.list_active_plans()
    
    return [
        Plan(
            id=plan.id,
            name=plan.name,
            description=plan.description,
            price_monthly=plan.price_monthly,
            price_yearly=plan.price_yearly,
            features=[
                PlanFeature(
                    name=feature.name,
                    description=feature.description
                ) for feature in plan.features
            ],
            is_active=plan.is_active
        ) for plan in plans
    ]

@router.get("/plans/{plan_id}", response_model=Plan)
async def get_plan(
    plan_id: UUID = Path(..., description="The ID of the plan to retrieve"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific subscription plan by ID.
    
    Returns the details of a subscription plan.
    """
    plan_service = PlanService(db)
    plan = await plan_service.get_plan(plan_id)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    return Plan(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        price_monthly=plan.price_monthly,
        price_yearly=plan.price_yearly,
        features=[
            PlanFeature(
                name=feature.name,
                description=feature.description
            ) for feature in plan.features
        ],
        is_active=plan.is_active
    )

@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: SubscriptionCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new subscription.
    
    Creates a new subscription for the current user.
    """
    subscription_service = SubscriptionService(db)
    plan_service = PlanService(db)
    
    # Check if plan exists and is active
    plan = await plan_service.get_plan(subscription_data.plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or inactive plan"
        )
    
    # Validate billing cycle
    if subscription_data.billing_cycle not in ["monthly", "yearly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid billing cycle. Must be 'monthly' or 'yearly'"
        )
    
    try:
        subscription = await subscription_service.create_subscription(
            user_id=UUID(current_user["sub"]),
            plan_id=subscription_data.plan_id,
            billing_cycle=subscription_data.billing_cycle
        )
        
        return SubscriptionResponse(
            id=subscription.id,
            user_id=subscription.user_id,
            plan=Plan(
                id=subscription.plan.id,
                name=subscription.plan.name,
                description=subscription.plan.description,
                price_monthly=subscription.plan.price_monthly,
                price_yearly=subscription.plan.price_yearly,
                features=[
                    PlanFeature(
                        name=feature.name,
                        description=feature.description
                    ) for feature in subscription.plan.features
                ],
                is_active=subscription.plan.is_active
            ),
            status=subscription.status,
            billing_cycle=subscription.billing_cycle,
            start_date=subscription.start_date.isoformat(),
            end_date=subscription.end_date.isoformat(),
            auto_renew=subscription.auto_renew,
            cancel_at_period_end=subscription.cancel_at_period_end
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/current", response_model=Optional[SubscriptionResponse])
async def get_current_subscription(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current subscription.
    
    Returns the current active subscription for the user, if any.
    """
    subscription_service = SubscriptionService(db)
    subscription = await subscription_service.get_active_subscription(
        user_id=UUID(current_user["sub"])
    )
    
    if not subscription:
        return None
    
    return SubscriptionResponse(
        id=subscription.id,
        user_id=subscription.user_id,
        plan=Plan(
            id=subscription.plan.id,
            name=subscription.plan.name,
            description=subscription.plan.description,
            price_monthly=subscription.plan.price_monthly,
            price_yearly=subscription.plan.price_yearly,
            features=[
                PlanFeature(
                    name=feature.name,
                    description=feature.description
                ) for feature in subscription.plan.features
            ],
            is_active=subscription.plan.is_active
        ),
        status=subscription.status,
        billing_cycle=subscription.billing_cycle,
        start_date=subscription.start_date.isoformat(),
        end_date=subscription.end_date.isoformat(),
        auto_renew=subscription.auto_renew,
        cancel_at_period_end=subscription.cancel_at_period_end
    )

@router.put("/current", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_data: SubscriptionUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current subscription.
    
    Updates the current subscription for the user.
    """
    subscription_service = SubscriptionService(db)
    plan_service = PlanService(db)
    
    # Get current subscription
    current_subscription = await subscription_service.get_active_subscription(
        user_id=UUID(current_user["sub"])
    )
    
    if not current_subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    # Validate plan if provided
    if subscription_data.plan_id:
        plan = await plan_service.get_plan(subscription_data.plan_id)
        if not plan or not plan.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or inactive plan"
            )
    
    # Validate billing cycle if provided
    if subscription_data.billing_cycle and subscription_data.billing_cycle not in ["monthly", "yearly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid billing cycle. Must be 'monthly' or 'yearly'"
        )
    
    try:
        subscription = await subscription_service.update_subscription(
            subscription_id=current_subscription.id,
            plan_id=subscription_data.plan_id,
            billing_cycle=subscription_data.billing_cycle,
            auto_renew=subscription_data.auto_renew
        )
        
        return SubscriptionResponse(
            id=subscription.id,
            user_id=subscription.user_id,
            plan=Plan(
                id=subscription.plan.id,
                name=subscription.plan.name,
                description=subscription.plan.description,
                price_monthly=subscription.plan.price_monthly,
                price_yearly=subscription.plan.price_yearly,
                features=[
                    PlanFeature(
                        name=feature.name,
                        description=feature.description
                    ) for feature in subscription.plan.features
                ],
                is_active=subscription.plan.is_active
            ),
            status=subscription.status,
            billing_cycle=subscription.billing_cycle,
            start_date=subscription.start_date.isoformat(),
            end_date=subscription.end_date.isoformat(),
            auto_renew=subscription.auto_renew,
            cancel_at_period_end=subscription.cancel_at_period_end
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/current/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    cancel_data: CancelSubscriptionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel subscription.
    
    Cancels the current subscription for the user.
    If cancel_immediately is True, the subscription is canceled immediately.
    Otherwise, it will be canceled at the end of the billing period.
    """
    subscription_service = SubscriptionService(db)
    
    # Get current subscription
    current_subscription = await subscription_service.get_active_subscription(
        user_id=UUID(current_user["sub"])
    )
    
    if not current_subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    try:
        subscription = await subscription_service.cancel_subscription(
            subscription_id=current_subscription.id,
            cancel_immediately=cancel_data.cancel_immediately
        )
        
        return SubscriptionResponse(
            id=subscription.id,
            user_id=subscription.user_id,
            plan=Plan(
                id=subscription.plan.id,
                name=subscription.plan.name,
                description=subscription.plan.description,
                price_monthly=subscription.plan.price_monthly,
                price_yearly=subscription.plan.price_yearly,
                features=[
                    PlanFeature(
                        name=feature.name,
                        description=feature.description
                    ) for feature in subscription.plan.features
                ],
                is_active=subscription.plan.is_active
            ),
            status=subscription.status,
            billing_cycle=subscription.billing_cycle,
            start_date=subscription.start_date.isoformat(),
            end_date=subscription.end_date.isoformat(),
            auto_renew=subscription.auto_renew,
            cancel_at_period_end=subscription.cancel_at_period_end
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/history", response_model=List[SubscriptionResponse])
async def get_subscription_history(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get subscription history.
    
    Returns a list of all subscriptions for the user, including past ones.
    """
    subscription_service = SubscriptionService(db)
    subscriptions = await subscription_service.get_subscription_history(
        user_id=UUID(current_user["sub"]),
        limit=limit,
        offset=offset
    )
    
    return [
        SubscriptionResponse(
            id=subscription.id,
            user_id=subscription.user_id,
            plan=Plan(
                id=subscription.plan.id,
                name=subscription.plan.name,
                description=subscription.plan.description,
                price_monthly=subscription.plan.price_monthly,
                price_yearly=subscription.plan.price_yearly,
                features=[
                    PlanFeature(
                        name=feature.name,
                        description=feature.description
                    ) for feature in subscription.plan.features
                ],
                is_active=subscription.plan.is_active
            ),
            status=subscription.status,
            billing_cycle=subscription.billing_cycle,
            start_date=subscription.start_date.isoformat(),
            end_date=subscription.end_date.isoformat(),
            auto_renew=subscription.auto_renew,
            cancel_at_period_end=subscription.cancel_at_period_end
        ) for subscription in subscriptions
    ]
