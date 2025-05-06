from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from enum import Enum

class CourseStatus(str, Enum):
    """Status of a course."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class CourseLevel(str, Enum):
    """Difficulty level of a course."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ALL_LEVELS = "all_levels"

@dataclass
class Course:
    """
    Course domain entity representing a course in the e-learning platform.
    """
    title: str
    instructor_id: str
    description: str
    level: CourseLevel
    status: CourseStatus
    id: Optional[str] = None
    slug: Optional[str] = None
    short_description: Optional[str] = None
    image_url: Optional[str] = None
    category_id: Optional[str] = None
    subcategory_ids: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    price: Optional[float] = None
    sale_price: Optional[float] = None
    duration_minutes: Optional[int] = None
    skills_gained: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    language: str = "en"
    caption_languages: List[str] = field(default_factory=list)
    meta_keywords: Optional[str] = None
    meta_description: Optional[str] = None
    featured: bool = False
    published_at: Optional[datetime] = None
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
        Convert course entity to dictionary representation.
        
        Returns:
            Dictionary representation of the course
        """
        return {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "instructor_id": self.instructor_id,
            "description": self.description,
            "short_description": self.short_description,
            "image_url": self.image_url,
            "level": self.level.value if isinstance(self.level, CourseLevel) else self.level,
            "status": self.status.value if isinstance(self.status, CourseStatus) else self.status,
            "category_id": self.category_id,
            "subcategory_ids": self.subcategory_ids,
            "tags": self.tags,
            "price": self.price,
            "sale_price": self.sale_price,
            "duration_minutes": self.duration_minutes,
            "skills_gained": self.skills_gained,
            "requirements": self.requirements,
            "language": self.language,
            "caption_languages": self.caption_languages,
            "meta_keywords": self.meta_keywords,
            "meta_description": self.meta_description,
            "featured": self.featured,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def update(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        short_description: Optional[str] = None,
        image_url: Optional[str] = None,
        level: Optional[CourseLevel] = None,
        category_id: Optional[str] = None,
        subcategory_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        price: Optional[float] = None,
        sale_price: Optional[float] = None,
        duration_minutes: Optional[int] = None,
        skills_gained: Optional[List[str]] = None,
        requirements: Optional[List[str]] = None,
        language: Optional[str] = None,
        caption_languages: Optional[List[str]] = None,
        meta_keywords: Optional[str] = None,
        meta_description: Optional[str] = None,
        featured: Optional[bool] = None,
    ) -> None:
        """
        Update course attributes.
        
        Args:
            Various optional attributes to update
        """
        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        if short_description is not None:
            self.short_description = short_description
        if image_url is not None:
            self.image_url = image_url
        if level is not None:
            self.level = level
        if category_id is not None:
            self.category_id = category_id
        if subcategory_ids is not None:
            self.subcategory_ids = subcategory_ids
        if tags is not None:
            self.tags = tags
        if price is not None:
            self.price = price
        if sale_price is not None:
            self.sale_price = sale_price
        if duration_minutes is not None:
            self.duration_minutes = duration_minutes
        if skills_gained is not None:
            self.skills_gained = skills_gained
        if requirements is not None:
            self.requirements = requirements
        if language is not None:
            self.language = language
        if caption_languages is not None:
            self.caption_languages = caption_languages
        if meta_keywords is not None:
            self.meta_keywords = meta_keywords
        if meta_description is not None:
            self.meta_description = meta_description
        if featured is not None:
            self.featured = featured
            
        self.updated_at = datetime.utcnow()
    
    def publish(self) -> None:
        """Publish the course, making it available to users."""
        self.status = CourseStatus.PUBLISHED
        self.published_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def unpublish(self) -> None:
        """Unpublish the course, making it a draft."""
        self.status = CourseStatus.DRAFT
        self.updated_at = datetime.utcnow()
    
    def archive(self) -> None:
        """Archive the course, making it unavailable for new enrollments."""
        self.status = CourseStatus.ARCHIVED
        self.updated_at = datetime.utcnow()
    
    def is_published(self) -> bool:
        """Check if the course is published."""
        return self.status == CourseStatus.PUBLISHED
    
    def is_on_sale(self) -> bool:
        """Check if the course is currently on sale."""
        return self.sale_price is not None and self.sale_price < self.price
    
    def get_effective_price(self) -> float:
        """Get the effective price (sale price if available, otherwise regular price)."""
        if self.is_on_sale():
            return self.sale_price
        return self.price 