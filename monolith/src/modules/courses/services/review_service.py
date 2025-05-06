from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import get_logger
from src.modules.courses.domain.review import Review
from src.modules.courses.persistence.review_repository import ReviewRepository
from src.modules.courses.persistence.course_repository import CourseRepository
from src.modules.courses.persistence.enrollment_repository import EnrollmentRepository
from src.modules.courses.domain.enrollment import EnrollmentStatus

logger = get_logger(__name__)

class ReviewService:
    """
    Service for course review-related operations.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.review_repository = ReviewRepository(db)
        self.course_repository = CourseRepository(db)
        self.enrollment_repository = EnrollmentRepository(db)
    
    async def get_review_by_id(self, review_id: str) -> Optional[Review]:
        """Get a review by ID."""
        return await self.review_repository.get_by_id(review_id)
    
    async def get_review_by_user_and_course(self, user_id: str, course_id: str) -> Optional[Review]:
        """Get a review by user ID and course ID."""
        return await self.review_repository.get_by_user_and_course(user_id, course_id)
    
    async def create_review(self, review_data: Dict[str, Any]) -> Optional[Review]:
        """
        Create a new course review.
        
        Args:
            review_data: Dictionary with review data
            
        Returns:
            Created review domain entity or None if creation failed
        """
        try:
            user_id = review_data['user_id']
            course_id = review_data['course_id']
            
            # Verify course exists
            course = await self.course_repository.get_by_id(course_id)
            if not course:
                logger.error(f"Course {course_id} not found for review creation")
                return None
            
            # Check if user is enrolled in the course
            enrollment = await self.enrollment_repository.get_by_user_and_course(user_id, course_id)
            is_verified_purchase = False
            
            if enrollment:
                # Only consider verified if enrollment is active or completed
                is_verified_purchase = enrollment.status in [EnrollmentStatus.ACTIVE, EnrollmentStatus.COMPLETED]
            else:
                logger.warning(f"User {user_id} is not enrolled in course {course_id} but submitting a review")
            
            # Check if user already has a review for this course
            existing_review = await self.review_repository.get_by_user_and_course(user_id, course_id)
            if existing_review:
                logger.info(f"User {user_id} already has a review for course {course_id}, updating instead")
                
                # Update existing review
                existing_review.rating = review_data['rating']
                if 'title' in review_data:
                    existing_review.title = review_data['title']
                if 'content' in review_data:
                    existing_review.content = review_data['content']
                existing_review.updated_at = datetime.utcnow()
                
                return await self.review_repository.update(existing_review)
            
            # Generate ID if not provided
            review_id = review_data.get('id') or str(uuid.uuid4())
            
            # Create review domain entity
            review = Review(
                id=review_id,
                user_id=user_id,
                course_id=course_id,
                rating=review_data['rating'],
                title=review_data.get('title'),
                content=review_data.get('content'),
                is_verified_purchase=is_verified_purchase,
                is_featured=False,
                is_hidden=False,
                helpfulness_votes=0
            )
            
            return await self.review_repository.create(review)
            
        except Exception as e:
            logger.error(f"Error creating review: {str(e)}", exc_info=True)
            return None
    
    async def update_review(self, review_id: str, review_data: Dict[str, Any]) -> Optional[Review]:
        """
        Update an existing review.
        
        Args:
            review_id: ID of the review to update
            review_data: Dictionary with updated review data
            
        Returns:
            Updated review domain entity or None if update failed
        """
        try:
            # Get existing review
            review = await self.review_repository.get_by_id(review_id)
            if not review:
                logger.error(f"Review with ID {review_id} not found for update")
                return None
            
            # Update review attributes (only allow updating certain fields by the reviewer)
            if 'rating' in review_data:
                review.rating = review_data['rating']
            if 'title' in review_data:
                review.title = review_data['title']
            if 'content' in review_data:
                review.content = review_data['content']
            
            # These fields should only be updated by admin/instructor
            if 'is_featured' in review_data:
                review.is_featured = review_data['is_featured']
            if 'is_hidden' in review_data:
                review.is_hidden = review_data['is_hidden']
            
            review.updated_at = datetime.utcnow()
            
            return await self.review_repository.update(review)
            
        except Exception as e:
            logger.error(f"Error updating review {review_id}: {str(e)}", exc_info=True)
            return None
    
    async def delete_review(self, review_id: str) -> bool:
        """
        Delete a review.
        
        Args:
            review_id: ID of the review to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return await self.review_repository.delete(review_id)
            
        except Exception as e:
            logger.error(f"Error deleting review {review_id}: {str(e)}", exc_info=True)
            return False
    
    async def add_instructor_response(self, review_id: str, response: str) -> Optional[Review]:
        """
        Add an instructor response to a review.
        
        Args:
            review_id: Review ID
            response: Instructor's response text
            
        Returns:
            Updated review domain entity, or None if update failed
        """
        try:
            return await self.review_repository.add_instructor_response(review_id, response)
            
        except Exception as e:
            logger.error(f"Error adding instructor response to review {review_id}: {str(e)}", exc_info=True)
            return None
    
    async def toggle_featured_status(self, review_id: str, is_featured: bool) -> Optional[Review]:
        """
        Toggle the featured status of a review.
        
        Args:
            review_id: Review ID
            is_featured: Whether the review should be featured
            
        Returns:
            Updated review domain entity, or None if update failed
        """
        try:
            return await self.review_repository.toggle_featured_status(review_id, is_featured)
            
        except Exception as e:
            logger.error(f"Error toggling featured status for review {review_id}: {str(e)}", exc_info=True)
            return None
    
    async def toggle_hidden_status(self, review_id: str, is_hidden: bool) -> Optional[Review]:
        """
        Toggle the hidden status of a review.
        
        Args:
            review_id: Review ID
            is_hidden: Whether the review should be hidden
            
        Returns:
            Updated review domain entity, or None if update failed
        """
        try:
            return await self.review_repository.toggle_hidden_status(review_id, is_hidden)
            
        except Exception as e:
            logger.error(f"Error toggling hidden status for review {review_id}: {str(e)}", exc_info=True)
            return None
    
    async def vote_as_helpful(self, review_id: str) -> Optional[Review]:
        """
        Increment the helpfulness votes for a review.
        
        Args:
            review_id: Review ID
            
        Returns:
            Updated review domain entity, or None if update failed
        """
        try:
            return await self.review_repository.vote_as_helpful(review_id)
            
        except Exception as e:
            logger.error(f"Error voting review {review_id} as helpful: {str(e)}", exc_info=True)
            return None
    
    async def get_course_reviews(
        self, 
        course_id: str,
        page: int = 1,
        page_size: int = 20,
        include_hidden: bool = False,
        verified_only: bool = False,
        featured_only: bool = False,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Review], int]:
        """
        Get reviews for a course with pagination and filtering.
        
        Args:
            course_id: Course ID
            page: Page number (1-indexed)
            page_size: Number of results per page
            include_hidden: Whether to include hidden reviews
            verified_only: Whether to return only verified purchase reviews
            featured_only: Whether to return only featured reviews
            sort_by: Field to sort by
            sort_order: Sort order ("asc" or "desc")
            
        Returns:
            Tuple of (list of reviews, total count)
        """
        try:
            return await self.review_repository.get_course_reviews(
                course_id=course_id,
                page=page,
                page_size=page_size,
                include_hidden=include_hidden,
                verified_only=verified_only,
                featured_only=featured_only,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
        except Exception as e:
            logger.error(f"Error getting reviews for course {course_id}: {str(e)}", exc_info=True)
            return [], 0
    
    async def get_user_reviews(
        self, 
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Review], int]:
        """
        Get reviews by a user with pagination and sorting.
        
        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of results per page
            sort_by: Field to sort by
            sort_order: Sort order ("asc" or "desc")
            
        Returns:
            Tuple of (list of reviews, total count)
        """
        try:
            return await self.review_repository.get_user_reviews(
                user_id=user_id,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
        except Exception as e:
            logger.error(f"Error getting reviews for user {user_id}: {str(e)}", exc_info=True)
            return [], 0
    
    async def get_course_rating_stats(self, course_id: str) -> Dict[str, Any]:
        """
        Get rating statistics for a course.
        
        Args:
            course_id: Course ID
            
        Returns:
            Dictionary with rating statistics
        """
        try:
            return await self.review_repository.get_course_rating_stats(course_id)
            
        except Exception as e:
            logger.error(f"Error getting rating stats for course {course_id}: {str(e)}", exc_info=True)
            return {
                "average_rating": 0.0,
                "total_reviews": 0,
                "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            } 