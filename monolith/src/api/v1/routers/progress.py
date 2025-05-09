from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_active_user, get_current_user, get_db
from src.modules.courses.services.progress_service import ProgressService
from src.modules.courses.services.enrollment_service import EnrollmentService
from src.modules.courses.services.course_service import CourseService
from src.modules.courses.domain.progress import LessonProgress, ProgressStatus
from src.api.v1.schemas.progress import (
    LessonProgressUpdate, LessonProgressResponse, SectionProgressResponse,
    CourseProgressResponse, RecentActivityResponse, LearningStatsResponse
)

router = APIRouter(
    prefix="/progress",
    tags=["progress"],
    responses={404: {"description": "Not found"}},
)

# Dependency to get ProgressService
def get_progress_service(db: AsyncSession = Depends(get_db)) -> ProgressService:
    return ProgressService(db)

def get_enrollment_service(db: AsyncSession = Depends(get_db)) -> EnrollmentService:
    return EnrollmentService(db)

def get_course_service(db: AsyncSession = Depends(get_db)) -> CourseService:
    return CourseService(db)

@router.get("/lesson/{lesson_id}", response_model=LessonProgressResponse)
async def get_lesson_progress(
    lesson_id: str = Path(..., description="Lesson ID"),
    progress_service: ProgressService = Depends(get_progress_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get progress for a specific lesson.
    """
    progress = await progress_service.get_lesson_progress(current_user["id"], lesson_id)
    
    if not progress:
        # Return empty progress if not found
        return {
            "lesson_id": lesson_id,
            "progress_percentage": 0.0,
            "status": "not_started",
            "last_position_seconds": 0
        }
        
    return progress

@router.post("/lesson/{lesson_id}/update", response_model=LessonProgressResponse)
async def update_lesson_progress(
    progress_data: LessonProgressUpdate,
    lesson_id: str = Path(..., description="Lesson ID"),
    progress_service: ProgressService = Depends(get_progress_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Update progress for a specific lesson.
    """
    updated_progress = await progress_service.update_lesson_progress(
        current_user["id"], 
        lesson_id, 
        progress_data.progress_percentage,
        progress_data.position_seconds
    )
    
    if not updated_progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update lesson progress"
        )
        
    return updated_progress

@router.post("/lesson/{lesson_id}/complete", response_model=LessonProgressResponse)
async def complete_lesson(
    lesson_id: str = Path(..., description="Lesson ID"),
    progress_service: ProgressService = Depends(get_progress_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Mark a lesson as completed.
    """
    completed_progress = await progress_service.mark_lesson_completed(
        current_user["id"], lesson_id
    )
    
    if not completed_progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to mark lesson as completed"
        )
        
    return completed_progress

@router.post("/lesson/{lesson_id}/reset", response_model=LessonProgressResponse)
async def reset_lesson_progress(
    lesson_id: str = Path(..., description="Lesson ID"),
    progress_service: ProgressService = Depends(get_progress_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Reset progress for a specific lesson.
    """
    reset_progress = await progress_service.reset_lesson_progress(
        current_user["id"], lesson_id
    )
    
    if not reset_progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No progress found to reset"
        )
        
    return reset_progress

@router.get("/course/{course_id}", response_model=CourseProgressResponse)
async def get_course_progress(
    course_id: str = Path(..., description="Course ID"),
    progress_service: ProgressService = Depends(get_progress_service),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
    course_service: CourseService = Depends(get_course_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get detailed progress for a course.
    """
    # Check if user is enrolled in the course
    enrollment_check = await enrollment_service.check_user_enrollment(
        current_user["id"], course_id
    )
    
    if not enrollment_check["is_enrolled"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not enrolled in this course"
        )
    
    # Get course details
    course = await course_service.get_course_by_id(course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Get progress details
    progress = await progress_service.get_course_progress(current_user["id"], course_id)
    
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failed to retrieve course progress"
        )
    
    return progress

@router.get("/section/{section_id}", response_model=SectionProgressResponse)
async def get_section_progress(
    section_id: str = Path(..., description="Section ID"),
    progress_service: ProgressService = Depends(get_progress_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get progress for all lessons in a section.
    """
    progress = await progress_service.get_section_progress(current_user["id"], section_id)
    
    if not progress["section"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found"
        )
    
    return {
        "section_id": progress["section"].id,
        "title": progress["section"].title,
        "progress_percentage": progress["progress_percentage"],
        "lessons": [
            {
                "lesson_id": lp["lesson"].id,
                "title": lp["lesson"].title,
                "type": lp["lesson"].type,
                "status": lp["progress"].status if lp["progress"] else "not_started",
                "progress_percentage": lp["progress"].progress_percentage if lp["progress"] else 0.0,
                "last_position_seconds": lp["progress"].last_position_seconds if lp["progress"] else 0
            }
            for lp in progress["lessons"]
        ]
    }

@router.get("/recent-activity", response_model=RecentActivityResponse)
async def get_recent_activity(
    limit: int = Query(5, gt=0, le=20, description="Number of activities to return"),
    days: int = Query(7, gt=0, le=30, description="Number of days to look back"),
    progress_service: ProgressService = Depends(get_progress_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get user's recent learning activity across all courses.
    """
    activities = await progress_service.get_recent_activity(
        current_user["id"], limit, days
    )
    
    return {
        "activities": activities
    }

@router.get("/learning-stats", response_model=LearningStatsResponse)
async def get_learning_stats(
    progress_service: ProgressService = Depends(get_progress_service),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get overall learning statistics for the user.
    """
    stats = await progress_service.get_learning_stats(current_user["id"])
    
    return stats 