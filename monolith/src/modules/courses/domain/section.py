from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional

@dataclass
class Section:
    """
    Section domain entity representing a section within a course.
    """
    course_id: str
    title: str
    position: int
    id: Optional[str] = None
    description: Optional[str] = None
    is_free_preview: bool = False
    duration_minutes: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert section entity to dictionary representation.
        
        Returns:
            Dictionary representation of the section
        """
        return {
            "id": self.id,
            "course_id": self.course_id,
            "title": self.title,
            "position": self.position,
            "description": self.description,
            "is_free_preview": self.is_free_preview,
            "duration_minutes": self.duration_minutes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def update(
        self,
        title: Optional[str] = None,
        position: Optional[int] = None,
        description: Optional[str] = None,
        is_free_preview: Optional[bool] = None,
        duration_minutes: Optional[int] = None
    ) -> None:
        """
        Update section attributes.
        
        Args:
            title: Section title
            position: Order position within the course
            description: Section description
            is_free_preview: Whether the section is available for free preview
            duration_minutes: Section duration in minutes
        """
        if title is not None:
            self.title = title
        if position is not None:
            self.position = position
        if description is not None:
            self.description = description
        if is_free_preview is not None:
            self.is_free_preview = is_free_preview
        if duration_minutes is not None:
            self.duration_minutes = duration_minutes
            
        self.updated_at = datetime.utcnow() 