from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_db
from src.common.auth import get_current_user
from src.modules.courses.services.progress_service import ProgressService
from src.modules.courses.domain.progress import ProgressStatus

router = APIRouter(prefix="/progress", tags=["progress"])

@router.get("/lessons/{lesson_id}")
async def get_lesson_progress(
    lesson_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get progress for a specific lesson.
    
    Args:
        lesson_id: Lesson ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dictionary containing progress information
    """
    progress_service = ProgressService(db)
    progress = await progress_service.get_lesson_progress(current_user["id"], lesson_id)
    
    if not progress:
        raise HTTPException(status_code=404, detail="Progress not found")
    
    return progress

@router.put("/lessons/{lesson_id}")
async def update_lesson_progress(
    lesson_id: str,
    progress_percentage: float = Query(..., ge=0.0, le=100.0),
    position_seconds: Optional[int] = Query(None, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update progress for a specific lesson.
    
    Args:
        lesson_id: Lesson ID
        progress_percentage: New progress percentage (0.0 to 100.0)
        position_seconds: Current position in seconds for video content
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dictionary containing updated progress information
    """
    progress_service = ProgressService(db)
    progress = await progress_service.update_lesson_progress(
        current_user["id"], lesson_id, progress_percentage, position_seconds
    )
    
    if not progress:
        raise HTTPException(status_code=404, detail="Progress not found")
    
    return progress

@router.post("/lessons/{lesson_id}/complete")
async def mark_lesson_completed(
    lesson_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Mark a lesson as completed.
    
    Args:
        lesson_id: Lesson ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dictionary containing updated progress information
    """
    progress_service = ProgressService(db)
    progress = await progress_service.mark_lesson_completed(current_user["id"], lesson_id)
    
    if not progress:
        raise HTTPException(status_code=404, detail="Progress not found")
    
    return progress

@router.get("/courses/{course_id}")
async def get_course_progress(
    course_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get overall progress for a course.
    
    Args:
        course_id: Course ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dictionary containing course progress information
    """
    progress_service = ProgressService(db)
    progress = await progress_service.get_course_progress(current_user["id"], course_id)
    
    if not progress:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return progress

@router.get("/sections/{section_id}")
async def get_section_progress(
    section_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get progress for a specific section.
    
    Args:
        section_id: Section ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dictionary containing section progress information
    """
    progress_service = ProgressService(db)
    progress = await progress_service.get_section_progress(current_user["id"], section_id)
    
    if not progress:
        raise HTTPException(status_code=404, detail="Section not found")
    
    return progress

@router.get("/recent")
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(7, ge=1, le=30),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get recent learning activity for a user.
    
    Args:
        limit: Maximum number of activities to return
        days: Number of days to look back
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of recent activities
    """
    progress_service = ProgressService(db)
    activities = await progress_service.get_recent_activity(
        current_user["id"], limit, days
    )
    
    return activities

@router.get("/stats")
async def get_learning_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get learning statistics for a user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Dictionary containing learning statistics
    """
    progress_service = ProgressService(db)
    stats = await progress_service.get_learning_stats(current_user["id"])
    
    return stats 