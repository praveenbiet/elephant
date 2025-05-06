from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List

@dataclass
class Review:
    """
    Review domain entity representing a review for a course.
    """
    user_id: str
    course_id: str
    rating: int  # 1-5 stars
    id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    instructor_response: Optional[str] = None
    instructor_response_at: Optional[datetime] = None
    is_verified_purchase: bool = False
    is_featured: bool = False
    is_hidden: bool = False
    helpfulness_votes: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize timestamps if not provided and validate rating."""
        now = datetime.utcnow()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
            
        # Ensure rating is within range
        self.rating = max(1, min(5, self.rating))
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert review entity to dictionary representation.
        
        Returns:
            Dictionary representation of the review
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "course_id": self.course_id,
            "rating": self.rating,
            "title": self.title,
            "content": self.content,
            "instructor_response": self.instructor_response,
            "instructor_response_at": self.instructor_response_at.isoformat() if self.instructor_response_at else None,
            "is_verified_purchase": self.is_verified_purchase,
            "is_featured": self.is_featured,
            "is_hidden": self.is_hidden,
            "helpfulness_votes": self.helpfulness_votes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def update(
        self,
        rating: Optional[int] = None,
        title: Optional[str] = None,
        content: Optional[str] = None
    ) -> None:
        """
        Update review attributes.
        
        Args:
            rating: Review rating (1-5 stars)
            title: Review title
            content: Review content
        """
        if rating is not None:
            self.rating = max(1, min(5, rating))
        if title is not None:
            self.title = title
        if content is not None:
            self.content = content
            
        self.updated_at = datetime.utcnow()
    
    def add_instructor_response(self, response: str) -> None:
        """
        Add an instructor response to the review.
        
        Args:
            response: Instructor's response text
        """
        self.instructor_response = response
        self.instructor_response_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def remove_instructor_response(self) -> None:
        """Remove instructor response from the review."""
        self.instructor_response = None
        self.instructor_response_at = None
        self.updated_at = datetime.utcnow()
    
    def mark_as_featured(self) -> None:
        """Mark the review as featured."""
        self.is_featured = True
        self.updated_at = datetime.utcnow()
    
    def unmark_as_featured(self) -> None:
        """Unmark the review as featured."""
        self.is_featured = False
        self.updated_at = datetime.utcnow()
    
    def hide(self) -> None:
        """Hide the review (e.g., for inappropriate content)."""
        self.is_hidden = True
        self.updated_at = datetime.utcnow()
    
    def unhide(self) -> None:
        """Unhide the review."""
        self.is_hidden = False
        self.updated_at = datetime.utcnow()
    
    def vote_as_helpful(self) -> None:
        """Increment the helpfulness votes for the review."""
        self.helpfulness_votes += 1
        self.updated_at = datetime.utcnow()
    
    def vote_as_unhelpful(self) -> None:
        """Decrement the helpfulness votes for the review (to a minimum of 0)."""
        self.helpfulness_votes = max(0, self.helpfulness_votes - 1)
        self.updated_at = datetime.utcnow()
    
    def verify_purchase(self) -> None:
        """Mark the review as a verified purchase."""
        self.is_verified_purchase = True
        self.updated_at = datetime.utcnow()
    
    def is_verified(self) -> bool:
        """Check if the review is from a verified purchaser."""
        return self.is_verified_purchase 