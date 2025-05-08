from typing import List, Optional, Dict, Any
from uuid import UUID
import pendulum

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field

from src.common.database import get_db
from src.common.auth import get_current_admin_user
from src.modules.admin.services.user_service import AdminUserService

router = APIRouter(prefix="/users", tags=["Admin Users"])

# Request/Response Models
class UserBase(BaseModel):
    """Base user model."""
    email: EmailStr
    first_name: str
    last_name: str

class UserCreateRequest(UserBase):
    """User creation request model."""
    password: str = Field(..., min_length=8)
    is_active: bool = True
    is_admin: bool = False

class UserUpdateRequest(BaseModel):
    """User update request model."""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None

class UserResponse(UserBase):
    """User response model."""
    id: UUID
    is_active: bool
    is_admin: bool
    created_at: str
    last_login: Optional[str] = None
    
    class Config:
        from_attributes = True

class UserDetailResponse(UserResponse):
    """Detailed user response model."""
    subscription_status: Optional[str] = None
    subscription_plan: Optional[str] = None
    subscription_end_date: Optional[str] = None
    total_logins: int
    course_enrollments: int
    assessment_completions: int
    
    class Config:
        from_attributes = True

class UserActivityLog(BaseModel):
    """User activity log model."""
    action: str
    timestamp: str
    details: Dict[str, Any]
    
    class Config:
        from_attributes = True

class PasswordResetRequest(BaseModel):
    """Password reset request model."""
    password: str = Field(..., min_length=8)

# Routes
@router.get("", response_model=List[UserResponse])
async def list_users(
    search: Optional[str] = Query(None, description="Search by name or email"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_admin: Optional[bool] = Query(None, description="Filter by admin status"),
    sort_by: str = Query("created_at", description="Sort by field: 'created_at', 'email', 'last_login'"),
    sort_order: str = Query("desc", description="Sort order: 'asc' or 'desc'"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List users.
    
    Returns a list of users, optionally filtered by various criteria.
    """
    admin_user_service = AdminUserService(db)
    
    # Validate sort_by
    valid_sort_fields = ["created_at", "email", "first_name", "last_name", "last_login"]
    if sort_by not in valid_sort_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort field. Must be one of: {', '.join(valid_sort_fields)}"
        )
    
    # Validate sort_order
    valid_sort_orders = ["asc", "desc"]
    if sort_order not in valid_sort_orders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort order. Must be one of: {', '.join(valid_sort_orders)}"
        )
    
    users = await admin_user_service.list_users(
        search=search,
        is_active=is_active,
        is_admin=is_admin,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )
    
    return [
        UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        ) for user in users
    ]

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user.
    
    Creates a new user with the specified details.
    """
    admin_user_service = AdminUserService(db)
    
    try:
        user = await admin_user_service.create_user(
            email=user_data.email,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            is_active=user_data.is_active,
            is_admin=user_data.is_admin
        )
        
        return UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: UUID = Path(..., description="The ID of the user to retrieve"),
    current_user: Dict[str, Any] = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific user by ID.
    
    Returns detailed user information.
    """
    admin_user_service = AdminUserService(db)
    user = await admin_user_service.get_user_details(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserDetailResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None,
        subscription_status=user.subscription_status,
        subscription_plan=user.subscription_plan,
        subscription_end_date=user.subscription_end_date.isoformat() if user.subscription_end_date else None,
        total_logins=user.total_logins,
        course_enrollments=user.course_enrollments,
        assessment_completions=user.assessment_completions
    )

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_data: UserUpdateRequest,
    user_id: UUID = Path(..., description="The ID of the user to update"),
    current_user: Dict[str, Any] = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a user.
    
    Updates a user's information.
    """
    admin_user_service = AdminUserService(db)
    
    # Check if user exists
    existing_user = await admin_user_service.get_user(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        user = await admin_user_service.update_user(
            user_id=user_id,
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            is_active=user_data.is_active,
            is_admin=user_data.is_admin
        )
        
        return UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_user_password(
    password_data: PasswordResetRequest,
    user_id: UUID = Path(..., description="The ID of the user to reset password for"),
    current_user: Dict[str, Any] = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reset user password.
    
    Resets a user's password to the specified value.
    """
    admin_user_service = AdminUserService(db)
    
    # Check if user exists
    existing_user = await admin_user_service.get_user(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        await admin_user_service.reset_password(
            user_id=user_id,
            new_password=password_data.password
        )
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{user_id}/activity", response_model=List[UserActivityLog])
async def get_user_activity(
    user_id: UUID = Path(..., description="The ID of the user to get activity for"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user activity logs.
    
    Returns a list of activity logs for the specified user.
    """
    admin_user_service = AdminUserService(db)
    
    # Check if user exists
    existing_user = await admin_user_service.get_user(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    activities = await admin_user_service.get_user_activity(
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    
    return [
        UserActivityLog(
            action=activity.action,
            timestamp=activity.timestamp.isoformat(),
            details=activity.details
        ) for activity in activities
    ]

@router.post("/{user_id}/impersonate", response_model=Dict[str, str])
async def impersonate_user(
    user_id: UUID = Path(..., description="The ID of the user to impersonate"),
    current_user: Dict[str, Any] = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Impersonate a user.
    
    Generates a temporary token that allows the admin to impersonate the specified user.
    """
    admin_user_service = AdminUserService(db)
    
    # Check if user exists
    existing_user = await admin_user_service.get_user(user_id)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Can't impersonate yourself
    if str(user_id) == current_user["sub"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot impersonate yourself"
        )
    
    try:
        impersonation_token = await admin_user_service.create_impersonation_token(
            admin_id=UUID(current_user["sub"]),
            user_id=user_id
        )
        
        return {"token": impersonation_token}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
