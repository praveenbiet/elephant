from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from src.common.database import Base

class CategoryModel(Base):
    """Course category database model."""
    __tablename__ = "categories"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon_url = Column(String(255), nullable=True)
    image_url = Column(String(255), nullable=True)
    position = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    subcategories = relationship("SubcategoryModel", back_populates="category", cascade="all, delete-orphan")
    courses = relationship("CourseModel", back_populates="category")
    
    # Indices
    __table_args__ = (
        Index("ix_categories_position", "position"),
        Index("ix_categories_is_active", "is_active"),
    )
    
    def __repr__(self):
        return f"<Category {self.name}>"

class SubcategoryModel(Base):
    """Course subcategory database model."""
    __tablename__ = "subcategories"
    
    id = Column(String(36), primary_key=True)
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    image_url = Column(String(255), nullable=True)
    position = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    category = relationship("CategoryModel", back_populates="subcategories")
    
    # Indices
    __table_args__ = (
        Index("ix_subcategories_category_id", "category_id"),
        Index("ix_subcategories_position", "position"),
        Index("ix_subcategories_is_active", "is_active"),
    )
    
    def __repr__(self):
        return f"<Subcategory {self.name} in category {self.category_id}>" 