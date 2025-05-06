import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, update, delete, func, desc, asc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from src.common.logger import get_logger
from src.modules.courses.domain.enrollment import Enrollment, EnrollmentStatus
from src.modules.courses.models.enrollment import EnrollmentModel

logger = get_logger(__name__)

class EnrollmentRepository:
    """
    Repository for enrollment-related database operations.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, enrollment_id: str) -> Optional[Enrollment]:
        """
        Get an enrollment by ID.
        
        Args:
            enrollment_id: Enrollment ID
            
        Returns:
            Enrollment domain entity if found, None otherwise
        """
        try:
            query = select(EnrollmentModel).where(EnrollmentModel.id == enrollment_id)
            result = await self.db.execute(query)
            enrollment_model = result.scalars().first()
            
            if not enrollment_model:
                return None
                
            return self._map_to_domain(enrollment_model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting enrollment by ID {enrollment_id}: {str(e)}", exc_info=True)
            return None
    
    async def get_by_user_and_course(self, user_id: str, course_id: str) -> Optional[Enrollment]:
        """
        Get an enrollment by user ID and course ID.
        
        Args:
            user_id: User ID
            course_id: Course ID
            
        Returns:
            Enrollment domain entity if found, None otherwise
        """
        try:
            query = select(EnrollmentModel).where(
                EnrollmentModel.user_id == user_id,
                EnrollmentModel.course_id == course_id
            )
            result = await self.db.execute(query)
            enrollment_model = result.scalars().first()
            
            if not enrollment_model:
                return None
                
            return self._map_to_domain(enrollment_model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting enrollment for user {user_id} and course {course_id}: {str(e)}", exc_info=True)
            return None
    
    async def create(self, enrollment: Enrollment) -> Optional[Enrollment]:
        """
        Create a new enrollment.
        
        Args:
            enrollment: Enrollment domain entity
            
        Returns:
            Created enrollment domain entity with ID, or None if creation failed
        """
        try:
            # Check if enrollment already exists
            existing_enrollment = await self.get_by_user_and_course(
                enrollment.user_id, enrollment.course_id
            )
            
            if existing_enrollment:
                logger.warning(f"Enrollment already exists for user {enrollment.user_id} and course {enrollment.course_id}")
                return existing_enrollment
            
            # Generate ID if not provided
            if not enrollment.id:
                enrollment.id = str(uuid.uuid4())
            
            # Create model from domain entity
            enrollment_model = EnrollmentModel(
                id=enrollment.id,
                user_id=enrollment.user_id,
                course_id=enrollment.course_id,
                status=enrollment.status,
                enrolled_at=enrollment.enrolled_at or datetime.utcnow(),
                completed_at=enrollment.completed_at,
                expiry_date=enrollment.expiry_date,
                progress_percentage=enrollment.progress_percentage,
                last_activity_at=enrollment.last_activity_at,
                payment_id=enrollment.payment_id,
                certificate_id=enrollment.certificate_id,
                created_at=enrollment.created_at or datetime.utcnow(),
                updated_at=enrollment.updated_at or datetime.utcnow()
            )
            
            self.db.add(enrollment_model)
            await self.db.commit()
            await self.db.refresh(enrollment_model)
            
            # Return domain entity with updated data
            return self._map_to_domain(enrollment_model)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error creating enrollment for user {enrollment.user_id} and course {enrollment.course_id}: {str(e)}", exc_info=True)
            return None
    
    async def update(self, enrollment: Enrollment) -> Optional[Enrollment]:
        """
        Update an existing enrollment.
        
        Args:
            enrollment: Enrollment domain entity with updated values
            
        Returns:
            Updated enrollment domain entity, or None if update failed
        """
        try:
            # Check if enrollment exists
            existing_enrollment = await self.get_by_id(enrollment.id)
            if not existing_enrollment:
                logger.error(f"Enrollment with ID {enrollment.id} not found for update")
                return None
            
            # Update the enrollment
            query = update(EnrollmentModel).where(EnrollmentModel.id == enrollment.id).values(
                status=enrollment.status.value if isinstance(enrollment.status, EnrollmentStatus) else enrollment.status,
                completed_at=enrollment.completed_at,
                expiry_date=enrollment.expiry_date,
                progress_percentage=enrollment.progress_percentage,
                last_activity_at=enrollment.last_activity_at,
                payment_id=enrollment.payment_id,
                certificate_id=enrollment.certificate_id,
                updated_at=datetime.utcnow()
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            # Get the updated enrollment
            return await self.get_by_id(enrollment.id)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error updating enrollment {enrollment.id}: {str(e)}", exc_info=True)
            return None
    
    async def delete(self, enrollment_id: str) -> bool:
        """
        Delete an enrollment.
        
        Args:
            enrollment_id: ID of the enrollment to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = delete(EnrollmentModel).where(EnrollmentModel.id == enrollment_id)
            result = await self.db.execute(query)
            await self.db.commit()
            
            return result.rowcount > 0
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error deleting enrollment {enrollment_id}: {str(e)}", exc_info=True)
            return False
    
    async def get_user_enrollments(
        self, 
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[EnrollmentStatus] = None,
        sort_by: str = "enrolled_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Enrollment], int]:
        """
        Get enrollments for a user with pagination and filtering.
        
        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of results per page
            status: Filter by enrollment status
            sort_by: Field to sort by
            sort_order: Sort order ("asc" or "desc")
            
        Returns:
            Tuple of (list of enrollments, total count)
        """
        try:
            # Build query
            query = select(EnrollmentModel).where(EnrollmentModel.user_id == user_id)
            count_query = select(func.count(EnrollmentModel.id)).where(EnrollmentModel.user_id == user_id)
            
            # Apply status filter
            if status:
                status_value = status.value if isinstance(status, EnrollmentStatus) else status
                query = query.where(EnrollmentModel.status == status_value)
                count_query = count_query.where(EnrollmentModel.status == status_value)
            
            # Get total count
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()
            
            # Apply sorting
            sort_column = getattr(EnrollmentModel, sort_by, EnrollmentModel.enrolled_at)
            if sort_order.lower() == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))
            
            # Apply pagination
            query = query.offset((page - 1) * page_size).limit(page_size)
            
            # Execute query
            result = await self.db.execute(query)
            enrollment_models = result.scalars().all()
            
            # Map to domain entities
            enrollments = [self._map_to_domain(model) for model in enrollment_models]
            
            return enrollments, total_count
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting enrollments for user {user_id}: {str(e)}", exc_info=True)
            return [], 0
    
    async def get_course_enrollments(
        self, 
        course_id: str,
        page: int = 1,
        page_size: int = 20,
        status: Optional[EnrollmentStatus] = None,
        sort_by: str = "enrolled_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Enrollment], int]:
        """
        Get enrollments for a course with pagination and filtering.
        
        Args:
            course_id: Course ID
            page: Page number (1-indexed)
            page_size: Number of results per page
            status: Filter by enrollment status
            sort_by: Field to sort by
            sort_order: Sort order ("asc" or "desc")
            
        Returns:
            Tuple of (list of enrollments, total count)
        """
        try:
            # Build query
            query = select(EnrollmentModel).where(EnrollmentModel.course_id == course_id)
            count_query = select(func.count(EnrollmentModel.id)).where(EnrollmentModel.course_id == course_id)
            
            # Apply status filter
            if status:
                status_value = status.value if isinstance(status, EnrollmentStatus) else status
                query = query.where(EnrollmentModel.status == status_value)
                count_query = count_query.where(EnrollmentModel.status == status_value)
            
            # Get total count
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()
            
            # Apply sorting
            sort_column = getattr(EnrollmentModel, sort_by, EnrollmentModel.enrolled_at)
            if sort_order.lower() == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))
            
            # Apply pagination
            query = query.offset((page - 1) * page_size).limit(page_size)
            
            # Execute query
            result = await self.db.execute(query)
            enrollment_models = result.scalars().all()
            
            # Map to domain entities
            enrollments = [self._map_to_domain(model) for model in enrollment_models]
            
            return enrollments, total_count
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting enrollments for course {course_id}: {str(e)}", exc_info=True)
            return [], 0
    
    async def update_progress(
        self, 
        user_id: str, 
        course_id: str, 
        progress_percentage: float
    ) -> Optional[Enrollment]:
        """
        Update the progress of an enrollment.
        
        Args:
            user_id: User ID
            course_id: Course ID
            progress_percentage: New progress percentage (0.0 to 100.0)
            
        Returns:
            Updated enrollment domain entity, or None if update failed
        """
        try:
            # Get enrollment
            enrollment = await self.get_by_user_and_course(user_id, course_id)
            if not enrollment:
                logger.error(f"Enrollment not found for user {user_id} and course {course_id}")
                return None
            
            # Ensure progress is within range
            progress_percentage = max(0.0, min(100.0, progress_percentage))
            
            # Update enrollment
            now = datetime.utcnow()
            status = enrollment.status
            completed_at = enrollment.completed_at
            
            # Auto-mark as completed if 100% progress
            if progress_percentage >= 100.0 and enrollment.status != EnrollmentStatus.COMPLETED:
                status = EnrollmentStatus.COMPLETED
                completed_at = now
            
            query = update(EnrollmentModel).where(
                EnrollmentModel.user_id == user_id,
                EnrollmentModel.course_id == course_id
            ).values(
                progress_percentage=progress_percentage,
                last_activity_at=now,
                status=status,
                completed_at=completed_at,
                updated_at=now
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            # Get the updated enrollment
            return await self.get_by_user_and_course(user_id, course_id)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error updating progress for user {user_id} and course {course_id}: {str(e)}", exc_info=True)
            return None
    
    async def mark_as_completed(self, user_id: str, course_id: str) -> Optional[Enrollment]:
        """
        Mark an enrollment as completed.
        
        Args:
            user_id: User ID
            course_id: Course ID
            
        Returns:
            Updated enrollment domain entity, or None if update failed
        """
        try:
            # Get enrollment
            enrollment = await self.get_by_user_and_course(user_id, course_id)
            if not enrollment:
                logger.error(f"Enrollment not found for user {user_id} and course {course_id}")
                return None
            
            # Update enrollment
            now = datetime.utcnow()
            query = update(EnrollmentModel).where(
                EnrollmentModel.user_id == user_id,
                EnrollmentModel.course_id == course_id
            ).values(
                status=EnrollmentStatus.COMPLETED,
                completed_at=now,
                progress_percentage=100.0,
                last_activity_at=now,
                updated_at=now
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            # Get the updated enrollment
            return await self.get_by_user_and_course(user_id, course_id)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error marking enrollment as completed for user {user_id} and course {course_id}: {str(e)}", exc_info=True)
            return None
    
    async def count_enrollments_by_status(self, course_id: str) -> Dict[str, int]:
        """
        Count enrollments for a course grouped by status.
        
        Args:
            course_id: Course ID
            
        Returns:
            Dictionary with count of enrollments by status
        """
        try:
            query = select(
                EnrollmentModel.status,
                func.count(EnrollmentModel.id).label("count")
            ).where(
                EnrollmentModel.course_id == course_id
            ).group_by(
                EnrollmentModel.status
            )
            
            result = await self.db.execute(query)
            status_counts = {status: count for status, count in result.all()}
            
            # Ensure all statuses are represented
            counts = {}
            for status in EnrollmentStatus:
                counts[status.value] = status_counts.get(status.value, 0)
                
            return counts
            
        except SQLAlchemyError as e:
            logger.error(f"Error counting enrollments by status for course {course_id}: {str(e)}", exc_info=True)
            return {status.value: 0 for status in EnrollmentStatus}
    
    def _map_to_domain(self, enrollment_model: EnrollmentModel) -> Enrollment:
        """
        Map database model to domain entity.
        
        Args:
            enrollment_model: Database model
            
        Returns:
            Domain entity
        """
        return Enrollment(
            id=enrollment_model.id,
            user_id=enrollment_model.user_id,
            course_id=enrollment_model.course_id,
            status=enrollment_model.status,
            enrolled_at=enrollment_model.enrolled_at,
            completed_at=enrollment_model.completed_at,
            expiry_date=enrollment_model.expiry_date,
            progress_percentage=enrollment_model.progress_percentage,
            last_activity_at=enrollment_model.last_activity_at,
            payment_id=enrollment_model.payment_id,
            certificate_id=enrollment_model.certificate_id,
            created_at=enrollment_model.created_at,
            updated_at=enrollment_model.updated_at
        ) 