from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.common.database import get_db
from src.common.auth import get_current_user
from src.modules.notification.services.notification_service import NotificationService
from src.modules.notification.services.preference_service import PreferenceService

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# Request/Response Models
class Notification(BaseModel):
    """Notification model."""
    id: UUID
    user_id: UUID
    title: str
    message: str
    type: str
    is_read: bool
    created_at: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    
    class Config:
        from_attributes = True

class NotificationPreference(BaseModel):
    """Notification preference model."""
    type: str
    email_enabled: bool
    push_enabled: bool
    in_app_enabled: bool
    
    class Config:
        from_attributes = True

class NotificationPreferenceUpdate(BaseModel):
    """Notification preference update model."""
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None

class BatchMarkReadRequest(BaseModel):
    """Batch mark notifications as read request model."""
    notification_ids: List[UUID]

class NotificationCountResponse(BaseModel):
    """Notification count response model."""
    total: int
    unread: int

# Routes
@router.get("", response_model=List[Notification])
async def list_notifications(
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    type: Optional[str] = Query(None, description="Filter by notification type"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List notifications.
    
    Returns a list of notifications for the user, optionally filtered by read status or type.
    """
    notification_service = NotificationService(db)
    notifications = await notification_service.list_notifications(
        user_id=UUID(current_user["sub"]),
        is_read=is_read,
        type=type,
        limit=limit,
        offset=offset
    )
    
    return [
        Notification(
            id=notification.id,
            user_id=notification.user_id,
            title=notification.title,
            message=notification.message,
            type=notification.type,
            is_read=notification.is_read,
            created_at=notification.created_at.isoformat(),
            related_entity_type=notification.related_entity_type,
            related_entity_id=notification.related_entity_id
        ) for notification in notifications
    ]

@router.get("/count", response_model=NotificationCountResponse)
async def count_notifications(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Count notifications.
    
    Returns the total and unread notification counts for the user.
    """
    notification_service = NotificationService(db)
    counts = await notification_service.count_notifications(
        user_id=UUID(current_user["sub"])
    )
    
    return NotificationCountResponse(
        total=counts["total"],
        unread=counts["unread"]
    )

@router.put("/{notification_id}/read", response_model=Notification)
async def mark_as_read(
    notification_id: UUID = Path(..., description="The ID of the notification to mark as read"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a notification as read.
    
    Updates a specific notification to mark it as read.
    """
    notification_service = NotificationService(db)
    
    # Check if notification exists and belongs to user
    notification = await notification_service.get_notification(
        user_id=UUID(current_user["sub"]),
        notification_id=notification_id
    )
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    # No need to update if already read
    if notification.is_read:
        return Notification(
            id=notification.id,
            user_id=notification.user_id,
            title=notification.title,
            message=notification.message,
            type=notification.type,
            is_read=notification.is_read,
            created_at=notification.created_at.isoformat(),
            related_entity_type=notification.related_entity_type,
            related_entity_id=notification.related_entity_id
        )
    
    updated_notification = await notification_service.mark_as_read(
        notification_id=notification_id
    )
    
    return Notification(
        id=updated_notification.id,
        user_id=updated_notification.user_id,
        title=updated_notification.title,
        message=updated_notification.message,
        type=updated_notification.type,
        is_read=updated_notification.is_read,
        created_at=updated_notification.created_at.isoformat(),
        related_entity_type=updated_notification.related_entity_type,
        related_entity_id=updated_notification.related_entity_id
    )

@router.put("/batch-mark-read", status_code=status.HTTP_204_NO_CONTENT)
async def batch_mark_as_read(
    data: BatchMarkReadRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark multiple notifications as read.
    
    Updates multiple notifications to mark them as read.
    """
    notification_service = NotificationService(db)
    
    if not data.notification_ids:
        return None
    
    await notification_service.batch_mark_as_read(
        user_id=UUID(current_user["sub"]),
        notification_ids=data.notification_ids
    )
    
    return None

@router.put("/mark-all-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_as_read(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark all notifications as read.
    
    Updates all unread notifications for the user to mark them as read.
    """
    notification_service = NotificationService(db)
    
    await notification_service.mark_all_as_read(
        user_id=UUID(current_user["sub"])
    )
    
    return None

@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: UUID = Path(..., description="The ID of the notification to delete"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a notification.
    
    Removes a specific notification.
    """
    notification_service = NotificationService(db)
    
    # Check if notification exists and belongs to user
    notification = await notification_service.get_notification(
        user_id=UUID(current_user["sub"]),
        notification_id=notification_id
    )
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    success = await notification_service.delete_notification(
        notification_id=notification_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return None

@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_notifications(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete all notifications.
    
    Removes all notifications for the user.
    """
    notification_service = NotificationService(db)
    
    await notification_service.delete_all_notifications(
        user_id=UUID(current_user["sub"])
    )
    
    return None

@router.get("/preferences", response_model=List[NotificationPreference])
async def list_notification_preferences(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List notification preferences.
    
    Returns the user's notification preferences for different notification types.
    """
    preference_service = PreferenceService(db)
    preferences = await preference_service.list_preferences(
        user_id=UUID(current_user["sub"])
    )
    
    return [
        NotificationPreference(
            type=preference.type,
            email_enabled=preference.email_enabled,
            push_enabled=preference.push_enabled,
            in_app_enabled=preference.in_app_enabled
        ) for preference in preferences
    ]

@router.put("/preferences/{notification_type}", response_model=NotificationPreference)
async def update_notification_preference(
    preference_data: NotificationPreferenceUpdate,
    notification_type: str = Path(..., description="The notification type to update preferences for"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update notification preference.
    
    Updates the user's notification preferences for a specific notification type.
    """
    preference_service = PreferenceService(db)
    
    # Get at least one update field
    if preference_data.email_enabled is None and preference_data.push_enabled is None and preference_data.in_app_enabled is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one preference field must be provided"
        )
    
    try:
        preference = await preference_service.update_preference(
            user_id=UUID(current_user["sub"]),
            notification_type=notification_type,
            email_enabled=preference_data.email_enabled,
            push_enabled=preference_data.push_enabled,
            in_app_enabled=preference_data.in_app_enabled
        )
        
        return NotificationPreference(
            type=preference.type,
            email_enabled=preference.email_enabled,
            push_enabled=preference.push_enabled,
            in_app_enabled=preference.in_app_enabled
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
