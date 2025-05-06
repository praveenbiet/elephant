from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional

@dataclass
class Category:
    """
    Category domain entity representing a course category.
    """
    name: str
    id: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    image_url: Optional[str] = None
    position: int = 0
    is_active: bool = True
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
        Convert category entity to dictionary representation.
        
        Returns:
            Dictionary representation of the category
        """
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "icon_url": self.icon_url,
            "image_url": self.image_url,
            "position": self.position,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def update(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        icon_url: Optional[str] = None,
        image_url: Optional[str] = None,
        position: Optional[int] = None,
        is_active: Optional[bool] = None
    ) -> None:
        """
        Update category attributes.
        
        Args:
            name: Category name
            description: Category description
            icon_url: URL to icon
            image_url: URL to image
            position: Display order position
            is_active: Whether the category is active
        """
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if icon_url is not None:
            self.icon_url = icon_url
        if image_url is not None:
            self.image_url = image_url
        if position is not None:
            self.position = position
        if is_active is not None:
            self.is_active = is_active
            
        self.updated_at = datetime.utcnow()

@dataclass
class Subcategory:
    """
    Subcategory domain entity representing a subcategory within a course category.
    """
    category_id: str
    name: str
    id: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    position: int = 0
    is_active: bool = True
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
        Convert subcategory entity to dictionary representation.
        
        Returns:
            Dictionary representation of the subcategory
        """
        return {
            "id": self.id,
            "category_id": self.category_id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "image_url": self.image_url,
            "position": self.position,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def update(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        image_url: Optional[str] = None,
        position: Optional[int] = None,
        is_active: Optional[bool] = None
    ) -> None:
        """
        Update subcategory attributes.
        
        Args:
            name: Subcategory name
            description: Subcategory description
            image_url: URL to image
            position: Display order position
            is_active: Whether the subcategory is active
        """
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if image_url is not None:
            self.image_url = image_url
        if position is not None:
            self.position = position
        if is_active is not None:
            self.is_active = is_active
            
        self.updated_at = datetime.utcnow() 