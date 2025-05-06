from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import get_logger
from src.modules.courses.domain.enrollment import Enrollment, EnrollmentStatus
from src.modules.courses.persistence.enrollment_repository import EnrollmentRepository
from src.modules.courses.persistence.course_repository import CourseRepository

logger = get_logger(__name__)

class EnrollmentService:
    """
    Service for course enrollment-related operations.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.enrollment_repository = EnrollmentRepository(db)
        self.course_repository = CourseRepository(db)
    
    async def get_enrollment_by_id(self, enrollment_id: str) -> Optional[Enrollment]:
        """Get an enrollment by ID."""
        return await self.enrollment_repository.get_by_id(enrollment_id)
    
    async def get_enrollment_by_user_and_course(self, user_id: str, course_id: str) -> Optional[Enrollment]:
        """Get an enrollment by user ID and course ID."""
        return await self.enrollment_repository.get_by_user_and_course(user_id, course_id)
    
    async def enroll_user(
        self, 
        user_id: str, 
        course_id: str,
        payment_id: Optional[str] = None,
        expiry_date: Optional[datetime] = None
    ) -> Optional[Enrollment]:
        """
        Enroll a user in a course.
        
        Args:
            user_id: User ID
            course_id: Course ID
            payment_id: Optional payment ID
            expiry_date: Optional expiry date for the enrollment
            
        Returns:
            Created enrollment domain entity or None if creation failed
        """
        try:
            # Verify course exists
            course = await self.course_repository.get_by_id(course_id)
            if not course:
                logger.error(f"Course {course_id} not found for enrollment")
                return None
            
            # Check if user is already enrolled
            existing_enrollment = await self.enrollment_repository.get_by_user_and_course(user_id, course_id)
            if existing_enrollment:
                # If enrollment exists but is refunded or expired, reactivate it
                if existing_enrollment.status in [EnrollmentStatus.REFUNDED, EnrollmentStatus.EXPIRED]:
                    existing_enrollment.status = EnrollmentStatus.ACTIVE
                    existing_enrollment.enrolled_at = datetime.utcnow()
                    existing_enrollment.payment_id = payment_id or existing_enrollment.payment_id
                    existing_enrollment.expiry_date = expiry_date
                    existing_enrollment.last_activity_at = datetime.utcnow()
                    
                    return await self.enrollment_repository.update(existing_enrollment)
                
                logger.info(f"User {user_id} is already enrolled in course {course_id}")
                return existing_enrollment
            
            # Create new enrollment
            enrollment = Enrollment(
                id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=course_id,
                status=EnrollmentStatus.ACTIVE,
                enrolled_at=datetime.utcnow(),
                expiry_date=expiry_date,
                progress_percentage=0.0,
                last_activity_at=datetime.utcnow(),
                payment_id=payment_id
            )
            
            return await self.enrollment_repository.create(enrollment)
            
        except Exception as e:
            logger.error(f"Error enrolling user {user_id} in course {course_id}: {str(e)}", exc_info=True)
            return None
    
    async def complete_enrollment(self, user_id: str, course_id: str) -> Optional[Enrollment]:
        """
        Mark an enrollment as completed.
        
        Args:
            user_id: User ID
            course_id: Course ID
            
        Returns:
            Updated enrollment domain entity or None if update failed
        """
        try:
            return await self.enrollment_repository.mark_as_completed(user_id, course_id)
            
        except Exception as e:
            logger.error(f"Error completing enrollment for user {user_id} in course {course_id}: {str(e)}", exc_info=True)
            return None
    
    async def refund_enrollment(self, enrollment_id: str) -> Optional[Enrollment]:
        """
        Mark an enrollment as refunded.
        
        Args:
            enrollment_id: Enrollment ID
            
        Returns:
            Updated enrollment domain entity or None if update failed
        """
        try:
            enrollment = await self.enrollment_repository.get_by_id(enrollment_id)
            if not enrollment:
                logger.error(f"Enrollment {enrollment_id} not found for refund")
                return None
            
            enrollment.status = EnrollmentStatus.REFUNDED
            enrollment.updated_at = datetime.utcnow()
            
            return await self.enrollment_repository.update(enrollment)
            
        except Exception as e:
            logger.error(f"Error refunding enrollment {enrollment_id}: {str(e)}", exc_info=True)
            return None
    
    async def pause_enrollment(self, enrollment_id: str) -> Optional[Enrollment]:
        """
        Mark an enrollment as paused.
        
        Args:
            enrollment_id: Enrollment ID
            
        Returns:
            Updated enrollment domain entity or None if update failed
        """
        try:
            enrollment = await self.enrollment_repository.get_by_id(enrollment_id)
            if not enrollment:
                logger.error(f"Enrollment {enrollment_id} not found for pause")
                return None
            
            enrollment.status = EnrollmentStatus.PAUSED
            enrollment.updated_at = datetime.utcnow()
            
            return await self.enrollment_repository.update(enrollment)
            
        except Exception as e:
            logger.error(f"Error pausing enrollment {enrollment_id}: {str(e)}", exc_info=True)
            return None
    
    async def reactivate_enrollment(self, enrollment_id: str) -> Optional[Enrollment]:
        """
        Reactivate a paused or expired enrollment.
        
        Args:
            enrollment_id: Enrollment ID
            
        Returns:
            Updated enrollment domain entity or None if update failed
        """
        try:
            enrollment = await self.enrollment_repository.get_by_id(enrollment_id)
            if not enrollment:
                logger.error(f"Enrollment {enrollment_id} not found for reactivation")
                return None
            
            if enrollment.status not in [EnrollmentStatus.PAUSED, EnrollmentStatus.EXPIRED]:
                logger.warning(f"Enrollment {enrollment_id} is not paused or expired, cannot reactivate")
                return enrollment
            
            enrollment.status = EnrollmentStatus.ACTIVE
            enrollment.updated_at = datetime.utcnow()
            enrollment.last_activity_at = datetime.utcnow()
            
            return await self.enrollment_repository.update(enrollment)
            
        except Exception as e:
            logger.error(f"Error reactivating enrollment {enrollment_id}: {str(e)}", exc_info=True)
            return None
    
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
            return await self.enrollment_repository.update_progress(
                user_id, course_id, progress_percentage
            )
            
        except Exception as e:
            logger.error(f"Error updating progress for user {user_id} in course {course_id}: {str(e)}", exc_info=True)
            return None
    
    async def extend_enrollment(
        self, 
        enrollment_id: str, 
        days: int
    ) -> Optional[Enrollment]:
        """
        Extend the expiry date of an enrollment.
        
        Args:
            enrollment_id: Enrollment ID
            days: Number of days to extend by
            
        Returns:
            Updated enrollment domain entity or None if update failed
        """
        try:
            enrollment = await self.enrollment_repository.get_by_id(enrollment_id)
            if not enrollment:
                logger.error(f"Enrollment {enrollment_id} not found for extension")
                return None
            
            # Calculate new expiry date
            now = datetime.utcnow()
            current_expiry = enrollment.expiry_date or now
            
            # If expired, extend from current date
            if current_expiry < now:
                current_expiry = now
                
            new_expiry = current_expiry + timedelta(days=days)
            
            # Update enrollment
            enrollment.expiry_date = new_expiry
            enrollment.updated_at = now
            
            # If enrollment was expired, reactivate it
            if enrollment.status == EnrollmentStatus.EXPIRED:
                enrollment.status = EnrollmentStatus.ACTIVE
            
            return await self.enrollment_repository.update(enrollment)
            
        except Exception as e:
            logger.error(f"Error extending enrollment {enrollment_id}: {str(e)}", exc_info=True)
            return None
    
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
            return await self.enrollment_repository.get_user_enrollments(
                user_id=user_id,
                page=page,
                page_size=page_size,
                status=status,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
        except Exception as e:
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
            return await self.enrollment_repository.get_course_enrollments(
                course_id=course_id,
                page=page,
                page_size=page_size,
                status=status,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
        except Exception as e:
            logger.error(f"Error getting enrollments for course {course_id}: {str(e)}", exc_info=True)
            return [], 0
    
    async def check_user_enrollment(self, user_id: str, course_id: str) -> Dict[str, Any]:
        """
        Check if a user is enrolled in a course and get enrollment details.
        
        Args:
            user_id: User ID
            course_id: Course ID
            
        Returns:
            Dictionary with enrollment status and details
        """
        try:
            enrollment = await self.enrollment_repository.get_by_user_and_course(user_id, course_id)
            
            if not enrollment:
                return {
                    "is_enrolled": False,
                    "enrollment": None
                }
            
            # Check if enrollment is active
            is_active = enrollment.status == EnrollmentStatus.ACTIVE
            
            # Check if enrollment has expired
            has_expired = False
            if enrollment.expiry_date and enrollment.expiry_date < datetime.utcnow():
                has_expired = True
                
                # If expired but status is still active, update to expired
                if enrollment.status == EnrollmentStatus.ACTIVE:
                    enrollment.status = EnrollmentStatus.EXPIRED
                    enrollment.updated_at = datetime.utcnow()
                    enrollment = await self.enrollment_repository.update(enrollment)
                    is_active = False
            
            return {
                "is_enrolled": is_active,
                "enrollment": enrollment,
                "has_expired": has_expired,
                "is_completed": enrollment.status == EnrollmentStatus.COMPLETED,
                "is_refunded": enrollment.status == EnrollmentStatus.REFUNDED,
                "is_paused": enrollment.status == EnrollmentStatus.PAUSED
            }
            
        except Exception as e:
            logger.error(f"Error checking enrollment for user {user_id} in course {course_id}: {str(e)}", exc_info=True)
            return {
                "is_enrolled": False,
                "enrollment": None,
                "error": str(e)
            }
    
    async def add_certificate(self, enrollment_id: str, certificate_id: str) -> Optional[Enrollment]:
        """
        Add a certificate ID to an enrollment.
        
        Args:
            enrollment_id: Enrollment ID
            certificate_id: Certificate ID
            
        Returns:
            Updated enrollment domain entity or None if update failed
        """
        try:
            enrollment = await self.enrollment_repository.get_by_id(enrollment_id)
            if not enrollment:
                logger.error(f"Enrollment {enrollment_id} not found for adding certificate")
                return None
            
            enrollment.certificate_id = certificate_id
            enrollment.updated_at = datetime.utcnow()
            
            # If not completed, mark as completed
            if enrollment.status != EnrollmentStatus.COMPLETED:
                enrollment.status = EnrollmentStatus.COMPLETED
                enrollment.completed_at = datetime.utcnow()
                enrollment.progress_percentage = 100.0
            
            return await self.enrollment_repository.update(enrollment)
            
        except Exception as e:
            logger.error(f"Error adding certificate to enrollment {enrollment_id}: {str(e)}", exc_info=True)
            return None 