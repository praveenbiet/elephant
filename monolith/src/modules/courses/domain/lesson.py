from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

class LessonType(str, Enum):
    """Lesson types in the platform."""
    VIDEO = "video"
    READING = "reading"
    QUIZ = "quiz"
    ASSIGNMENT = "assignment"
    DISCUSSION = "discussion"
    CODE_LAB = "code_lab"
    PRESENTATION = "presentation"

@dataclass
class Lesson:
    """
    Lesson domain entity representing a lesson within a course section.
    """
    section_id: str
    title: str
    type: LessonType
    position: int
    id: Optional[str] = None
    content_id: Optional[str] = None  # ID of associated content (video, quiz, etc.)
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    is_free_preview: bool = False
    is_downloadable: bool = False
    preview_image_url: Optional[str] = None
    attachments: List[Dict[str, str]] = field(default_factory=list)
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
        Convert lesson entity to dictionary representation.
        
        Returns:
            Dictionary representation of the lesson
        """
        return {
            "id": self.id,
            "section_id": self.section_id,
            "title": self.title,
            "type": self.type.value if isinstance(self.type, LessonType) else self.type,
            "position": self.position,
            "content_id": self.content_id,
            "description": self.description,
            "duration_minutes": self.duration_minutes,
            "is_free_preview": self.is_free_preview,
            "is_downloadable": self.is_downloadable,
            "preview_image_url": self.preview_image_url,
            "attachments": self.attachments,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def update(
        self,
        title: Optional[str] = None,
        type: Optional[LessonType] = None,
        position: Optional[int] = None,
        content_id: Optional[str] = None,
        description: Optional[str] = None,
        duration_minutes: Optional[int] = None,
        is_free_preview: Optional[bool] = None,
        is_downloadable: Optional[bool] = None,
        preview_image_url: Optional[str] = None,
        attachments: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        """
        Update lesson attributes.
        
        Args:
            title: Lesson title
            type: Type of lesson
            position: Order position within the section
            content_id: Associated content ID
            description: Lesson description
            duration_minutes: Lesson duration in minutes
            is_free_preview: Whether the lesson is available for free preview
            is_downloadable: Whether the lesson content can be downloaded
            preview_image_url: URL to preview image
            attachments: List of attachment objects
        """
        if title is not None:
            self.title = title
        if type is not None:
            self.type = type
        if position is not None:
            self.position = position
        if content_id is not None:
            self.content_id = content_id
        if description is not None:
            self.description = description
        if duration_minutes is not None:
            self.duration_minutes = duration_minutes
        if is_free_preview is not None:
            self.is_free_preview = is_free_preview
        if is_downloadable is not None:
            self.is_downloadable = is_downloadable
        if preview_image_url is not None:
            self.preview_image_url = preview_image_url
        if attachments is not None:
            self.attachments = attachments
            
        self.updated_at = datetime.utcnow()
    
    def add_attachment(self, name: str, url: str, mime_type: str) -> None:
        """
        Add an attachment to the lesson.
        
        Args:
            name: Attachment name/title
            url: URL to the attachment file
            mime_type: MIME type of the attachment
        """
        attachment = {
            "name": name,
            "url": url,
            "mime_type": mime_type
        }
        
        if self.attachments is None:
            self.attachments = []
            
        self.attachments.append(attachment)
        self.updated_at = datetime.utcnow()
    
    def remove_attachment(self, url: str) -> None:
        """
        Remove an attachment from the lesson.
        
        Args:
            url: URL of the attachment to remove
        """
        if self.attachments:
            self.attachments = [a for a in self.attachments if a.get("url") != url]
            self.updated_at = datetime.utcnow() 