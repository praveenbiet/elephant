from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import relationship

from src.common.database import Base

class ReviewModel(Base):
    """Course review database model."""
    __tablename__ = "reviews"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, CheckConstraint("rating >= 1 AND rating <= 5"), nullable=False)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)
    instructor_response = Column(Text, nullable=True)
    instructor_response_at = Column(DateTime, nullable=True)
    is_verified_purchase = Column(Boolean, default=False, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    is_hidden = Column(Boolean, default=False, nullable=False)
    helpfulness_votes = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    course = relationship("CourseModel", back_populates="reviews")
    
    # Indices
    __table_args__ = (
        Index("ix_reviews_user_id", "user_id"),
        Index("ix_reviews_course_id", "course_id"),
        Index("ix_reviews_rating", "rating"),
        Index("ix_reviews_is_verified_purchase", "is_verified_purchase"),
        Index("ix_reviews_is_featured", "is_featured"),
        Index("ix_reviews_is_hidden", "is_hidden"),
        Index("ix_reviews_created_at", "created_at"),
        Index("uq_reviews_user_course", "user_id", "course_id", unique=True),
    )
    
    def __repr__(self):
        return f"<Review by user {self.user_id} for course {self.course_id}>" 