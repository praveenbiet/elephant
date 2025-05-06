import uuid
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy import select, update, delete, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from src.common.logger import get_logger
from src.modules.courses.domain.review import Review
from src.modules.courses.models.review import ReviewModel

logger = get_logger(__name__)

class ReviewRepository:
    """
    Repository for course review-related database operations.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, review_id: str) -> Optional[Review]:
        """
        Get a review by ID.
        
        Args:
            review_id: Review ID
            
        Returns:
            Review domain entity if found, None otherwise
        """
        try:
            query = select(ReviewModel).where(ReviewModel.id == review_id)
            result = await self.db.execute(query)
            review_model = result.scalars().first()
            
            if not review_model:
                return None
                
            return self._map_to_domain(review_model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting review by ID {review_id}: {str(e)}", exc_info=True)
            return None
    
    async def get_by_user_and_course(self, user_id: str, course_id: str) -> Optional[Review]:
        """
        Get a review by user ID and course ID.
        
        Args:
            user_id: User ID
            course_id: Course ID
            
        Returns:
            Review domain entity if found, None otherwise
        """
        try:
            query = select(ReviewModel).where(
                ReviewModel.user_id == user_id,
                ReviewModel.course_id == course_id
            )
            result = await self.db.execute(query)
            review_model = result.scalars().first()
            
            if not review_model:
                return None
                
            return self._map_to_domain(review_model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting review for user {user_id} and course {course_id}: {str(e)}", exc_info=True)
            return None
    
    async def create(self, review: Review) -> Optional[Review]:
        """
        Create a new review.
        
        Args:
            review: Review domain entity
            
        Returns:
            Created review domain entity with ID, or None if creation failed
        """
        try:
            # Check if review already exists
            existing_review = await self.get_by_user_and_course(
                review.user_id, review.course_id
            )
            
            if existing_review:
                logger.warning(f"Review already exists for user {review.user_id} and course {review.course_id}")
                return existing_review
            
            # Generate ID if not provided
            if not review.id:
                review.id = str(uuid.uuid4())
            
            # Create model from domain entity
            review_model = ReviewModel(
                id=review.id,
                user_id=review.user_id,
                course_id=review.course_id,
                rating=review.rating,
                title=review.title,
                content=review.content,
                instructor_response=review.instructor_response,
                instructor_response_at=review.instructor_response_at,
                is_verified_purchase=review.is_verified_purchase,
                is_featured=review.is_featured,
                is_hidden=review.is_hidden,
                helpfulness_votes=review.helpfulness_votes,
                created_at=review.created_at or datetime.utcnow(),
                updated_at=review.updated_at or datetime.utcnow()
            )
            
            self.db.add(review_model)
            await self.db.commit()
            await self.db.refresh(review_model)
            
            # Return domain entity with updated data
            return self._map_to_domain(review_model)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error creating review for user {review.user_id} and course {review.course_id}: {str(e)}", exc_info=True)
            return None
    
    async def update(self, review: Review) -> Optional[Review]:
        """
        Update an existing review.
        
        Args:
            review: Review domain entity with updated values
            
        Returns:
            Updated review domain entity, or None if update failed
        """
        try:
            # Check if review exists
            existing_review = await self.get_by_id(review.id)
            if not existing_review:
                logger.error(f"Review with ID {review.id} not found for update")
                return None
            
            # Update the review
            query = update(ReviewModel).where(ReviewModel.id == review.id).values(
                rating=review.rating,
                title=review.title,
                content=review.content,
                instructor_response=review.instructor_response,
                instructor_response_at=review.instructor_response_at,
                is_verified_purchase=review.is_verified_purchase,
                is_featured=review.is_featured,
                is_hidden=review.is_hidden,
                helpfulness_votes=review.helpfulness_votes,
                updated_at=datetime.utcnow()
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            # Get the updated review
            return await self.get_by_id(review.id)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error updating review {review.id}: {str(e)}", exc_info=True)
            return None
    
    async def delete(self, review_id: str) -> bool:
        """
        Delete a review.
        
        Args:
            review_id: ID of the review to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = delete(ReviewModel).where(ReviewModel.id == review_id)
            result = await self.db.execute(query)
            await self.db.commit()
            
            return result.rowcount > 0
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error deleting review {review_id}: {str(e)}", exc_info=True)
            return False
    
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
            # Build query
            query = select(ReviewModel).where(ReviewModel.course_id == course_id)
            count_query = select(func.count(ReviewModel.id)).where(ReviewModel.course_id == course_id)
            
            # Apply filters
            if not include_hidden:
                query = query.where(ReviewModel.is_hidden == False)
                count_query = count_query.where(ReviewModel.is_hidden == False)
            
            if verified_only:
                query = query.where(ReviewModel.is_verified_purchase == True)
                count_query = count_query.where(ReviewModel.is_verified_purchase == True)
            
            if featured_only:
                query = query.where(ReviewModel.is_featured == True)
                count_query = count_query.where(ReviewModel.is_featured == True)
            
            # Get total count
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()
            
            # Apply sorting
            sort_column = getattr(ReviewModel, sort_by, ReviewModel.created_at)
            if sort_order.lower() == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))
            
            # Apply pagination
            query = query.offset((page - 1) * page_size).limit(page_size)
            
            # Execute query
            result = await self.db.execute(query)
            review_models = result.scalars().all()
            
            # Map to domain entities
            reviews = [self._map_to_domain(model) for model in review_models]
            
            return reviews, total_count
            
        except SQLAlchemyError as e:
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
            # Build query
            query = select(ReviewModel).where(ReviewModel.user_id == user_id)
            count_query = select(func.count(ReviewModel.id)).where(ReviewModel.user_id == user_id)
            
            # Get total count
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()
            
            # Apply sorting
            sort_column = getattr(ReviewModel, sort_by, ReviewModel.created_at)
            if sort_order.lower() == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))
            
            # Apply pagination
            query = query.offset((page - 1) * page_size).limit(page_size)
            
            # Execute query
            result = await self.db.execute(query)
            review_models = result.scalars().all()
            
            # Map to domain entities
            reviews = [self._map_to_domain(model) for model in review_models]
            
            return reviews, total_count
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting reviews for user {user_id}: {str(e)}", exc_info=True)
            return [], 0
    
    async def add_instructor_response(
        self, 
        review_id: str, 
        response: str
    ) -> Optional[Review]:
        """
        Add an instructor response to a review.
        
        Args:
            review_id: Review ID
            response: Instructor's response text
            
        Returns:
            Updated review domain entity, or None if update failed
        """
        try:
            now = datetime.utcnow()
            query = update(ReviewModel).where(ReviewModel.id == review_id).values(
                instructor_response=response,
                instructor_response_at=now,
                updated_at=now
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            return await self.get_by_id(review_id)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
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
            now = datetime.utcnow()
            query = update(ReviewModel).where(ReviewModel.id == review_id).values(
                is_featured=is_featured,
                updated_at=now
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            return await self.get_by_id(review_id)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
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
            now = datetime.utcnow()
            query = update(ReviewModel).where(ReviewModel.id == review_id).values(
                is_hidden=is_hidden,
                updated_at=now
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            return await self.get_by_id(review_id)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
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
            # Get current votes count
            review = await self.get_by_id(review_id)
            if not review:
                return None
                
            # Update the votes
            now = datetime.utcnow()
            query = update(ReviewModel).where(ReviewModel.id == review_id).values(
                helpfulness_votes=review.helpfulness_votes + 1,
                updated_at=now
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            return await self.get_by_id(review_id)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error voting review {review_id} as helpful: {str(e)}", exc_info=True)
            return None
    
    async def get_course_rating_stats(self, course_id: str) -> Dict[str, Any]:
        """
        Get rating statistics for a course.
        
        Args:
            course_id: Course ID
            
        Returns:
            Dictionary with rating statistics
        """
        try:
            # Get average rating
            avg_query = select(func.avg(ReviewModel.rating)).where(
                ReviewModel.course_id == course_id,
                ReviewModel.is_hidden == False
            )
            avg_result = await self.db.execute(avg_query)
            avg_rating = avg_result.scalar() or 0.0
            
            # Get total count
            count_query = select(func.count(ReviewModel.id)).where(
                ReviewModel.course_id == course_id,
                ReviewModel.is_hidden == False
            )
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar() or 0
            
            # Get rating distribution
            rating_distribution = {}
            for rating in range(1, 6):
                rating_query = select(func.count(ReviewModel.id)).where(
                    ReviewModel.course_id == course_id,
                    ReviewModel.rating == rating,
                    ReviewModel.is_hidden == False
                )
                rating_result = await self.db.execute(rating_query)
                rating_count = rating_result.scalar() or 0
                
                rating_distribution[rating] = rating_count
            
            return {
                "average_rating": round(float(avg_rating), 1),
                "total_reviews": total_count,
                "rating_distribution": rating_distribution
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting rating stats for course {course_id}: {str(e)}", exc_info=True)
            return {
                "average_rating": 0.0,
                "total_reviews": 0,
                "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
    
    def _map_to_domain(self, review_model: ReviewModel) -> Review:
        """
        Map database model to domain entity.
        
        Args:
            review_model: Database model
            
        Returns:
            Domain entity
        """
        return Review(
            id=review_model.id,
            user_id=review_model.user_id,
            course_id=review_model.course_id,
            rating=review_model.rating,
            title=review_model.title,
            content=review_model.content,
            instructor_response=review_model.instructor_response,
            instructor_response_at=review_model.instructor_response_at,
            is_verified_purchase=review_model.is_verified_purchase,
            is_featured=review_model.is_featured,
            is_hidden=review_model.is_hidden,
            helpfulness_votes=review_model.helpfulness_votes,
            created_at=review_model.created_at,
            updated_at=review_model.updated_at
        ) 