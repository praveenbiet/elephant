from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

# Progress status enum
class ProgressStatus(str):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

# Request models
class LessonProgressUpdate(BaseModel):
    """Request model for updating lesson progress."""
    progress_percentage: float = Field(..., ge=0.0, le=100.0, description="Progress percentage (0-100)")
    position_seconds: Optional[int] = Field(None, ge=0, description="Current position in seconds for video content")
    
    class Config:
        schema_extra = {
            "example": {
                "progress_percentage": 45.5,
                "position_seconds": 325
            }
        }

# Response models
class LessonProgressResponse(BaseModel):
    """Response model for lesson progress."""
    lesson_id: str
    progress_percentage: float
    status: str
    last_position_seconds: int
    completed_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "lesson_id": "550e8400-e29b-41d4-a716-446655440000",
                "progress_percentage": 45.5,
                "status": "in_progress",
                "last_position_seconds": 325,
                "completed_at": None,
                "last_activity_at": "2023-08-15T14:30:45.123Z"
            }
        }

class LessonProgressInCourse(BaseModel):
    """Lesson progress information within a course view."""
    lesson_id: str
    title: str
    type: str
    status: str
    progress_percentage: float
    last_position_seconds: Optional[int] = None
    
    class Config:
        schema_extra = {
            "example": {
                "lesson_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Introduction to Python",
                "type": "video",
                "status": "in_progress",
                "progress_percentage": 45.5,
                "last_position_seconds": 325
            }
        }

class SectionProgressResponse(BaseModel):
    """Response model for section progress."""
    section_id: str
    title: str
    progress_percentage: float
    lessons: List[LessonProgressInCourse]
    
    class Config:
        schema_extra = {
            "example": {
                "section_id": "550e8400-e29b-41d4-a716-446655440001",
                "title": "Getting Started",
                "progress_percentage": 35.0,
                "lessons": [
                    {
                        "lesson_id": "550e8400-e29b-41d4-a716-446655440000",
                        "title": "Introduction to Python",
                        "type": "video",
                        "status": "completed",
                        "progress_percentage": 100.0,
                        "last_position_seconds": 450
                    },
                    {
                        "lesson_id": "550e8400-e29b-41d4-a716-446655440002",
                        "title": "Setting Up Your Environment",
                        "type": "video",
                        "status": "in_progress",
                        "progress_percentage": 45.5,
                        "last_position_seconds": 325
                    }
                ]
            }
        }

class CourseBasicInfo(BaseModel):
    """Basic course information."""
    id: str
    title: str
    image_url: Optional[str] = None

class EnrollmentInfo(BaseModel):
    """Enrollment information within course progress."""
    status: str
    progress_percentage: float
    completed_at: Optional[datetime] = None
    certificate_id: Optional[str] = None

class CourseProgressResponse(BaseModel):
    """Response model for course progress."""
    course: CourseBasicInfo
    overall_percentage: float
    status_counts: Dict[str, int]
    section_progress: List[SectionProgressResponse]
    enrollment: Optional[EnrollmentInfo] = None
    
    class Config:
        schema_extra = {
            "example": {
                "course": {
                    "id": "550e8400-e29b-41d4-a716-446655440010",
                    "title": "Complete Python Bootcamp",
                    "image_url": "https://example.com/images/python-course.jpg"
                },
                "overall_percentage": 35.0,
                "status_counts": {
                    "not_started": 5,
                    "in_progress": 3,
                    "completed": 2
                },
                "section_progress": [
                    {
                        "section_id": "550e8400-e29b-41d4-a716-446655440001",
                        "title": "Getting Started",
                        "progress_percentage": 75.0,
                        "lessons": [
                            {
                                "lesson_id": "550e8400-e29b-41d4-a716-446655440000",
                                "title": "Introduction to Python",
                                "type": "video",
                                "status": "completed",
                                "progress_percentage": 100.0
                            },
                            {
                                "lesson_id": "550e8400-e29b-41d4-a716-446655440002",
                                "title": "Setting Up Your Environment",
                                "type": "video",
                                "status": "in_progress",
                                "progress_percentage": 50.0
                            }
                        ]
                    }
                ],
                "enrollment": {
                    "status": "active",
                    "progress_percentage": 35.0,
                    "completed_at": None,
                    "certificate_id": None
                }
            }
        }

class ActivityItem(BaseModel):
    """Response model for a single activity item."""
    progress_id: str
    lesson_id: str
    lesson_title: str
    lesson_type: str
    section_id: str
    section_title: str
    course_id: str
    course_title: str
    course_image: Optional[str] = None
    status: str
    progress_percentage: float
    last_position_seconds: int
    last_activity_at: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "progress_id": "550e8400-e29b-41d4-a716-446655440020",
                "lesson_id": "550e8400-e29b-41d4-a716-446655440000",
                "lesson_title": "Introduction to Python",
                "lesson_type": "video",
                "section_id": "550e8400-e29b-41d4-a716-446655440001",
                "section_title": "Getting Started",
                "course_id": "550e8400-e29b-41d4-a716-446655440010",
                "course_title": "Complete Python Bootcamp",
                "course_image": "https://example.com/images/python-course.jpg",
                "status": "in_progress",
                "progress_percentage": 45.5,
                "last_position_seconds": 325,
                "last_activity_at": "2023-08-15T14:30:45.123Z"
            }
        }

class RecentActivityResponse(BaseModel):
    """Response model for recent activity list."""
    activities: List[ActivityItem]

class LearningStatsResponse(BaseModel):
    """Response model for learning statistics."""
    enrolled_courses: int
    completed_courses: int
    active_courses: int
    lessons_accessed: int
    lessons_completed: int
    minutes_watched: int
    last_activity_at: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "enrolled_courses": 5,
                "completed_courses": 2,
                "active_courses": 3,
                "lessons_accessed": 45,
                "lessons_completed": 32,
                "minutes_watched": 540,
                "last_activity_at": "2023-08-15T14:30:45.123Z"
            }
        } 