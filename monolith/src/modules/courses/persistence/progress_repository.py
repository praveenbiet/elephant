import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy import select, update, delete, func, desc, asc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from src.common.logger import get_logger
from src.modules.courses.domain.progress import LessonProgress, ProgressStatus
from src.modules.courses.models.course import LessonProgressModel

logger = get_logger(__name__)

class ProgressRepository:
    """
    Repository for progress-related database operations.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, progress_id: str) -> Optional[LessonProgress]:
        """
        Get a lesson progress record by ID.
        
        Args:
            progress_id: Progress record ID
            
        Returns:
            LessonProgress domain entity if found, None otherwise
        """
        try:
            query = select(LessonProgressModel).where(LessonProgressModel.id == progress_id)
            result = await self.db.execute(query)
            progress_model = result.scalars().first()
            
            if not progress_model:
                return None
                
            return self._map_to_domain(progress_model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting progress by ID {progress_id}: {str(e)}", exc_info=True)
            return None
    
    async def get_by_user_and_lesson(self, user_id: str, lesson_id: str) -> Optional[LessonProgress]:
        """
        Get a lesson progress record by user ID and lesson ID.
        
        Args:
            user_id: User ID
            lesson_id: Lesson ID
            
        Returns:
            LessonProgress domain entity if found, None otherwise
        """
        try:
            query = select(LessonProgressModel).where(
                LessonProgressModel.user_id == user_id,
                LessonProgressModel.lesson_id == lesson_id
            )
            result = await self.db.execute(query)
            progress_model = result.scalars().first()
            
            if not progress_model:
                return None
                
            return self._map_to_domain(progress_model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting progress for user {user_id} and lesson {lesson_id}: {str(e)}", exc_info=True)
            return None
    
    async def create(self, progress: LessonProgress) -> Optional[LessonProgress]:
        """
        Create a new lesson progress record.
        
        Args:
            progress: LessonProgress domain entity
            
        Returns:
            Created LessonProgress domain entity with ID, or None if creation failed
        """
        try:
            # Check if progress already exists
            existing_progress = await self.get_by_user_and_lesson(
                progress.user_id, progress.lesson_id
            )
            
            if existing_progress:
                logger.info(f"Progress already exists for user {progress.user_id} and lesson {progress.lesson_id}")
                return existing_progress
            
            # Generate ID if not provided
            if not progress.id:
                progress.id = str(uuid.uuid4())
            
            # Create model from domain entity
            progress_model = LessonProgressModel(
                id=progress.id,
                user_id=progress.user_id,
                lesson_id=progress.lesson_id,
                status=progress.status.value if isinstance(progress.status, ProgressStatus) else progress.status,
                progress_percentage=progress.progress_percentage,
                last_position_seconds=progress.last_position_seconds,
                completed_at=progress.completed_at,
                last_activity_at=progress.last_activity_at,
                created_at=progress.created_at or datetime.utcnow(),
                updated_at=progress.updated_at or datetime.utcnow()
            )
            
            self.db.add(progress_model)
            await self.db.commit()
            await self.db.refresh(progress_model)
            
            # Return domain entity with updated data
            return self._map_to_domain(progress_model)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error creating progress for user {progress.user_id} and lesson {progress.lesson_id}: {str(e)}", exc_info=True)
            return None
    
    async def update(self, progress: LessonProgress) -> Optional[LessonProgress]:
        """
        Update an existing lesson progress record.
        
        Args:
            progress: LessonProgress domain entity with updated values
            
        Returns:
            Updated LessonProgress domain entity, or None if update failed
        """
        try:
            # Check if progress exists
            existing_progress = await self.get_by_id(progress.id)
            if not existing_progress:
                logger.error(f"Progress with ID {progress.id} not found for update")
                return None
            
            # Update the progress
            query = update(LessonProgressModel).where(LessonProgressModel.id == progress.id).values(
                status=progress.status.value if isinstance(progress.status, ProgressStatus) else progress.status,
                progress_percentage=progress.progress_percentage,
                last_position_seconds=progress.last_position_seconds,
                completed_at=progress.completed_at,
                last_activity_at=progress.last_activity_at,
                updated_at=datetime.utcnow()
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            # Get the updated progress
            return await self.get_by_id(progress.id)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error updating progress {progress.id}: {str(e)}", exc_info=True)
            return None
    
    async def delete(self, progress_id: str) -> bool:
        """
        Delete a lesson progress record.
        
        Args:
            progress_id: ID of the progress record to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = delete(LessonProgressModel).where(LessonProgressModel.id == progress_id)
            result = await self.db.execute(query)
            await self.db.commit()
            
            return result.rowcount > 0
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error deleting progress {progress_id}: {str(e)}", exc_info=True)
            return False
    
    async def get_user_lesson_progress(
        self, 
        user_id: str,
        course_id: Optional[str] = None,
        section_id: Optional[str] = None,
        status: Optional[ProgressStatus] = None
    ) -> List[LessonProgress]:
        """
        Get lesson progress records for a user with filtering.
        
        Args:
            user_id: User ID
            course_id: Optional course ID to filter by
            section_id: Optional section ID to filter by
            status: Optional progress status to filter by
            
        Returns:
            List of LessonProgress domain entities
        """
        try:
            # Start with base query
            query = select(LessonProgressModel).where(LessonProgressModel.user_id == user_id)
            
            # Apply filters
            if section_id:
                # Filter by lessons in a specific section
                query = query.join(
                    LessonProgressModel.lesson
                ).where(
                    LessonProgressModel.lesson.has(section_id=section_id)
                )
            elif course_id:
                # Filter by lessons in a specific course
                query = query.join(
                    LessonProgressModel.lesson
                ).join(
                    LessonProgressModel.lesson.section
                ).where(
                    LessonProgressModel.lesson.section.has(course_id=course_id)
                )
            
            if status:
                status_value = status.value if isinstance(status, ProgressStatus) else status
                query = query.where(LessonProgressModel.status == status_value)
            
            # Execute query
            result = await self.db.execute(query)
            progress_models = result.scalars().all()
            
            # Map to domain entities
            return [self._map_to_domain(model) for model in progress_models]
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting progress for user {user_id}: {str(e)}", exc_info=True)
            return []
    
    async def calculate_course_progress(self, user_id: str, course_id: str) -> Tuple[float, Dict[str, int]]:
        """
        Calculate the overall progress for a user in a course.
        
        Args:
            user_id: User ID
            course_id: Course ID
            
        Returns:
            Tuple of (progress percentage, status counts)
        """
        try:
            # Get all lessons in the course
            lesson_count_query = """
            SELECT COUNT(l.id)
            FROM course_lessons l
            JOIN course_sections s ON l.section_id = s.id
            WHERE s.course_id = :course_id
            """
            
            # Get progress status counts
            progress_stats_query = """
            SELECT 
                lp.status,
                COUNT(lp.id) as count
            FROM lesson_progress lp
            JOIN course_lessons l ON lp.lesson_id = l.id
            JOIN course_sections s ON l.section_id = s.id
            WHERE lp.user_id = :user_id AND s.course_id = :course_id
            GROUP BY lp.status
            """
            
            # Execute queries
            lesson_count_result = await self.db.execute(
                lesson_count_query, 
                {"course_id": course_id}
            )
            total_lessons = lesson_count_result.scalar() or 0
            
            progress_stats_result = await self.db.execute(
                progress_stats_query, 
                {"user_id": user_id, "course_id": course_id}
            )
            
            # Process results
            status_counts = {
                "not_started": 0,
                "in_progress": 0,
                "completed": 0
            }
            
            for status, count in progress_stats_result:
                status_counts[status] = count
            
            # Calculate overall progress percentage
            if total_lessons == 0:
                progress_percentage = 0.0
            else:
                # Weight completed lessons as 100% and in-progress lessons by their progress percentage
                completed_count = status_counts.get("completed", 0)
                
                # Get average progress for in-progress lessons
                in_progress_avg_query = """
                SELECT AVG(lp.progress_percentage)
                FROM lesson_progress lp
                JOIN course_lessons l ON lp.lesson_id = l.id
                JOIN course_sections s ON l.section_id = s.id
                WHERE lp.user_id = :user_id 
                AND s.course_id = :course_id
                AND lp.status = 'in_progress'
                """
                
                in_progress_avg_result = await self.db.execute(
                    in_progress_avg_query,
                    {"user_id": user_id, "course_id": course_id}
                )
                in_progress_avg = in_progress_avg_result.scalar() or 0.0
                in_progress_count = status_counts.get("in_progress", 0)
                
                # Calculate total progress
                progress_percentage = (
                    (completed_count * 100.0) +
                    (in_progress_count * in_progress_avg)
                ) / (total_lessons * 100.0) * 100.0
            
            return progress_percentage, status_counts
            
        except SQLAlchemyError as e:
            logger.error(f"Error calculating course progress for user {user_id} and course {course_id}: {str(e)}", exc_info=True)
            return 0.0, {"not_started": 0, "in_progress": 0, "completed": 0}
    
    async def update_lesson_progress(
        self, 
        user_id: str, 
        lesson_id: str, 
        progress_percentage: float,
        position_seconds: Optional[int] = None
    ) -> Optional[LessonProgress]:
        """
        Update the progress of a specific lesson.
        
        Args:
            user_id: User ID
            lesson_id: Lesson ID
            progress_percentage: New progress percentage (0.0 to 100.0)
            position_seconds: Current position in seconds for video content
            
        Returns:
            Updated LessonProgress domain entity, or None if update failed
        """
        try:
            # Get existing progress or create new
            progress = await self.get_by_user_and_lesson(user_id, lesson_id)
            
            if not progress:
                # Create new progress record
                progress = LessonProgress(
                    user_id=user_id,
                    lesson_id=lesson_id,
                    status=ProgressStatus.NOT_STARTED,
                    progress_percentage=0.0,
                    last_position_seconds=0
                )
            
            # Update progress
            progress.update_progress(progress_percentage, position_seconds)
            
            # Save to database
            if progress.id:
                return await self.update(progress)
            else:
                return await self.create(progress)
            
        except SQLAlchemyError as e:
            logger.error(f"Error updating lesson progress for user {user_id} and lesson {lesson_id}: {str(e)}", exc_info=True)
            return None
    
    def _map_to_domain(self, progress_model: LessonProgressModel) -> LessonProgress:
        """
        Map database model to domain entity.
        
        Args:
            progress_model: Database model
            
        Returns:
            Domain entity
        """
        return LessonProgress(
            id=progress_model.id,
            user_id=progress_model.user_id,
            lesson_id=progress_model.lesson_id,
            status=progress_model.status,
            progress_percentage=progress_model.progress_percentage,
            last_position_seconds=progress_model.last_position_seconds,
            completed_at=progress_model.completed_at,
            last_activity_at=progress_model.last_activity_at,
            created_at=progress_model.created_at,
            updated_at=progress_model.updated_at
        ) 