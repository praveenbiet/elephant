from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum

class ProgressStatus(str, Enum):
    """Status of lesson progress."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

@dataclass
class LessonProgress:
    """
    LessonProgress domain entity representing a student's progress in a specific lesson.
    """
    user_id: str
    lesson_id: str
    id: Optional[str] = None
    status: ProgressStatus = ProgressStatus.NOT_STARTED
    progress_percentage: float = 0.0
    last_position_seconds: int = 0  # For video lessons, tracks playback position
    completed_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        now = datetime.utcnow()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
    
    def to_dict(self):
        """
        Convert lesson progress entity to dictionary representation.
        
        Returns:
            Dictionary representation of the lesson progress
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "lesson_id": self.lesson_id,
            "status": self.status.value if isinstance(self.status, ProgressStatus) else self.status,
            "progress_percentage": self.progress_percentage,
            "last_position_seconds": self.last_position_seconds,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def update_progress(self, progress_percentage: float, position_seconds: Optional[int] = None):
        """
        Update the progress for this lesson.
        
        Args:
            progress_percentage: New progress percentage (0.0 to 100.0)
            position_seconds: Current position in seconds for video content
        """
        self.progress_percentage = max(0.0, min(100.0, progress_percentage))
        self.last_activity_at = datetime.utcnow()
        
        if position_seconds is not None:
            self.last_position_seconds = max(0, position_seconds)
        
        # Update status based on progress
        if self.progress_percentage >= 100.0:
            self.complete()
        elif self.progress_percentage > 0.0:
            self.status = ProgressStatus.IN_PROGRESS
            
        self.updated_at = datetime.utcnow()
    
    def complete(self):
        """Mark the lesson as completed."""
        self.status = ProgressStatus.COMPLETED
        self.progress_percentage = 100.0
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def restart(self):
        """Reset progress to beginning of lesson."""
        self.status = ProgressStatus.IN_PROGRESS
        self.progress_percentage = 0.0
        self.last_position_seconds = 0
        self.completed_at = None
        self.last_activity_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def record_activity(self):
        """Record user activity in the lesson."""
        self.last_activity_at = datetime.utcnow()
        self.updated_at = datetime.utcnow() 