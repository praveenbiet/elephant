from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.common.database import get_db
from src.common.auth import get_current_user
from src.modules.user_progress.services.progress_service import ProgressService
from src.modules.user_progress.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/user-progress", tags=["User Progress"])

# Request/Response Models
class ProgressRecord(BaseModel):
    """Progress record model."""
    item_type: str
    item_id: UUID
    completion_percentage: int
    completed: bool
    last_accessed_at: str
    time_spent_seconds: int
    
    class Config:
        from_attributes = True

class ProgressSummary(BaseModel):
    """User progress summary model."""
    total_courses: int
    completed_courses: int
    total_videos: int
    completed_videos: int
    total_assessments: int
    completed_assessments: int
    total_learning_paths: int
    completed_learning_paths: int
    overall_completion_percentage: int
    total_time_spent_hours: float

class CourseProgressSummary(BaseModel):
    """Course progress summary model."""
    course_id: UUID
    course_title: str
    completion_percentage: int
    completed: bool
    total_videos: int
    completed_videos: int
    total_assessments: int
    completed_assessments: int
    last_accessed_at: str
    time_spent_hours: float

class LearningPathProgressSummary(BaseModel):
    """Learning path progress summary model."""
    learning_path_id: UUID
    learning_path_title: str
    completion_percentage: int
    completed: bool
    total_items: int
    completed_items: int
    last_accessed_at: str
    time_spent_hours: float

class ProgressUpdateRequest(BaseModel):
    """Progress update request model."""
    item_type: str = Field(..., description="Type of item: 'course', 'video', 'assessment', 'learning_path'")
    item_id: UUID
    completion_percentage: Optional[int] = Field(None, ge=0, le=100)
    completed: Optional[bool] = None
    time_spent_seconds: Optional[int] = Field(None, ge=0)

class TimeSeriesPoint(BaseModel):
    """Time series data point."""
    date: str
    value: float

class TimeSeriesData(BaseModel):
    """Time series data model."""
    metric: str
    data: List[TimeSeriesPoint]

# Routes
@router.get("/summary", response_model=ProgressSummary)
async def get_progress_summary(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user progress summary.
    
    Returns a summary of the user's overall progress across the platform.
    """
    analytics_service = AnalyticsService(db)
    
    summary = await analytics_service.get_user_progress_summary(
        user_id=UUID(current_user["sub"])
    )
    
    return ProgressSummary(
        total_courses=summary["total_courses"],
        completed_courses=summary["completed_courses"],
        total_videos=summary["total_videos"],
        completed_videos=summary["completed_videos"],
        total_assessments=summary["total_assessments"],
        completed_assessments=summary["completed_assessments"],
        total_learning_paths=summary["total_learning_paths"],
        completed_learning_paths=summary["completed_learning_paths"],
        overall_completion_percentage=summary["overall_completion_percentage"],
        total_time_spent_hours=summary["total_time_spent_hours"]
    )

@router.get("/courses", response_model=List[CourseProgressSummary])
async def get_course_progress(
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user course progress.
    
    Returns a summary of the user's progress for each course they have accessed.
    """
    analytics_service = AnalyticsService(db)
    
    courses = await analytics_service.get_user_course_progress(
        user_id=UUID(current_user["sub"]),
        limit=limit,
        offset=offset
    )
    
    return [
        CourseProgressSummary(
            course_id=course["course_id"],
            course_title=course["course_title"],
            completion_percentage=course["completion_percentage"],
            completed=course["completed"],
            total_videos=course["total_videos"],
            completed_videos=course["completed_videos"],
            total_assessments=course["total_assessments"],
            completed_assessments=course["completed_assessments"],
            last_accessed_at=course["last_accessed_at"].isoformat(),
            time_spent_hours=course["time_spent_hours"]
        ) for course in courses
    ]

@router.get("/learning-paths", response_model=List[LearningPathProgressSummary])
async def get_learning_path_progress(
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user learning path progress.
    
    Returns a summary of the user's progress for each learning path they have enrolled in.
    """
    analytics_service = AnalyticsService(db)
    
    learning_paths = await analytics_service.get_user_learning_path_progress(
        user_id=UUID(current_user["sub"]),
        limit=limit,
        offset=offset
    )
    
    return [
        LearningPathProgressSummary(
            learning_path_id=path["learning_path_id"],
            learning_path_title=path["learning_path_title"],
            completion_percentage=path["completion_percentage"],
            completed=path["completed"],
            total_items=path["total_items"],
            completed_items=path["completed_items"],
            last_accessed_at=path["last_accessed_at"].isoformat(),
            time_spent_hours=path["time_spent_hours"]
        ) for path in learning_paths
    ]

@router.get("/items/{item_type}/{item_id}", response_model=ProgressRecord)
async def get_item_progress(
    item_type: str = Path(..., description="Type of item: 'course', 'video', 'assessment', 'learning_path'"),
    item_id: UUID = Path(..., description="ID of the item"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get progress for a specific item.
    
    Returns the user's progress for a specific course, video, assessment, or learning path.
    """
    progress_service = ProgressService(db)
    
    if item_type not in ["course", "video", "assessment", "learning_path"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item type. Must be one of: 'course', 'video', 'assessment', 'learning_path'"
        )
    
    progress = await progress_service.get_item_progress(
        user_id=UUID(current_user["sub"]),
        item_type=item_type,
        item_id=item_id
    )
    
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No progress found for {item_type} with ID {item_id}"
        )
    
    return ProgressRecord(
        item_type=progress.item_type,
        item_id=progress.item_id,
        completion_percentage=progress.completion_percentage,
        completed=progress.completed,
        last_accessed_at=progress.last_accessed_at.isoformat(),
        time_spent_seconds=progress.time_spent_seconds
    )

@router.post("/update", status_code=status.HTTP_204_NO_CONTENT)
async def update_progress(
    progress_data: ProgressUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update progress for an item.
    
    Updates the user's progress for a specific course, video, assessment, or learning path.
    """
    progress_service = ProgressService(db)
    
    if progress_data.item_type not in ["course", "video", "assessment", "learning_path"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item type. Must be one of: 'course', 'video', 'assessment', 'learning_path'"
        )
    
    try:
        await progress_service.update_progress(
            user_id=UUID(current_user["sub"]),
            item_type=progress_data.item_type,
            item_id=progress_data.item_id,
            completion_percentage=progress_data.completion_percentage,
            completed=progress_data.completed,
            time_spent_seconds=progress_data.time_spent_seconds
        )
        return None
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/activity", response_model=TimeSeriesData)
async def get_activity_data(
    metric: str = Query(..., description="Metric to retrieve: 'daily_time', 'weekly_completion', 'monthly_assessments'"),
    period: str = Query("30d", description="Time period: '7d', '30d', '90d', '365d'"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user activity time series data.
    
    Returns time series data for various activity metrics.
    """
    analytics_service = AnalyticsService(db)
    
    valid_metrics = ["daily_time", "weekly_completion", "monthly_assessments"]
    if metric not in valid_metrics:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric. Must be one of: {', '.join(valid_metrics)}"
        )
    
    valid_periods = ["7d", "30d", "90d", "365d"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
        )
    
    time_series = await analytics_service.get_user_activity_time_series(
        user_id=UUID(current_user["sub"]),
        metric=metric,
        period=period
    )
    
    return TimeSeriesData(
        metric=metric,
        data=[
            TimeSeriesPoint(
                date=point["date"].isoformat(),
                value=point["value"]
            ) for point in time_series
        ]
    )
