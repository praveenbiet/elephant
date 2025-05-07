from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import get_logger
from src.modules.courses.domain.progress import LessonProgress, ProgressStatus
from src.modules.courses.persistence.progress_repository import ProgressRepository
from src.modules.courses.persistence.enrollment_repository import EnrollmentRepository
from src.modules.courses.persistence.lesson_repository import LessonRepository
from src.modules.courses.persistence.section_repository import SectionRepository
from src.modules.courses.persistence.course_repository import CourseRepository

logger = get_logger(__name__)

class ProgressService:
    """
    Service for managing course progress.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.progress_repo = ProgressRepository(db)
        self.enrollment_repo = EnrollmentRepository(db)
        self.lesson_repo = LessonRepository(db)
        self.section_repo = SectionRepository(db)
        self.course_repo = CourseRepository(db)
    
    async def get_lesson_progress(self, user_id: str, lesson_id: str) -> Optional[Dict[str, Any]]:
        """
        Get progress for a specific lesson.
        
        Args:
            user_id: User ID
            lesson_id: Lesson ID
            
        Returns:
            Dictionary containing progress information
        """
        try:
            # Get lesson progress
            progress = await self.progress_repo.get_by_user_and_lesson(user_id, lesson_id)
            
            if not progress:
                # Create initial progress record
                progress = LessonProgress(
                    user_id=user_id,
                    lesson_id=lesson_id,
                    status=ProgressStatus.NOT_STARTED,
                    progress_percentage=0.0,
                    last_position_seconds=0
                )
                progress = await self.progress_repo.create(progress)
            
            return progress.to_dict()
            
        except Exception as e:
            logger.error(f"Error getting lesson progress: {str(e)}", exc_info=True)
            return None
    
    async def update_lesson_progress(
        self, 
        user_id: str, 
        lesson_id: str, 
        progress_percentage: float,
        position_seconds: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update progress for a specific lesson.
        
        Args:
            user_id: User ID
            lesson_id: Lesson ID
            progress_percentage: New progress percentage (0.0 to 100.0)
            position_seconds: Current position in seconds for video content
            
        Returns:
            Dictionary containing updated progress information
        """
        try:
            # Update progress
            progress = await self.progress_repo.update_lesson_progress(
                user_id, lesson_id, progress_percentage, position_seconds
            )
            
            if not progress:
                return None
            
            return progress.to_dict()
            
        except Exception as e:
            logger.error(f"Error updating lesson progress: {str(e)}", exc_info=True)
            return None
    
    async def mark_lesson_completed(self, user_id: str, lesson_id: str) -> Optional[Dict[str, Any]]:
        """
        Mark a lesson as completed.
        
        Args:
            user_id: User ID
            lesson_id: Lesson ID
            
        Returns:
            Dictionary containing updated progress information
        """
        try:
            # Get current progress
            progress = await self.progress_repo.get_by_user_and_lesson(user_id, lesson_id)
            
            if not progress:
                # Create new progress record
                progress = LessonProgress(
                    user_id=user_id,
                    lesson_id=lesson_id,
                    status=ProgressStatus.NOT_STARTED,
                    progress_percentage=0.0,
                    last_position_seconds=0
                )
            
            # Mark as completed
            progress.complete()
            
            # Save to database
            if progress.id:
                progress = await self.progress_repo.update(progress)
            else:
                progress = await self.progress_repo.create(progress)
            
            if not progress:
                return None
            
            return progress.to_dict()
            
        except Exception as e:
            logger.error(f"Error marking lesson as completed: {str(e)}", exc_info=True)
            return None
    
    async def reset_lesson_progress(self, user_id: str, lesson_id: str) -> Optional[Dict[str, Any]]:
        """
        Reset progress for a specific lesson.
        
        Args:
            user_id: User ID
            lesson_id: Lesson ID
            
        Returns:
            Dictionary containing updated progress information
        """
        try:
            # Get existing progress
            progress = await self.progress_repo.get_by_user_and_lesson(user_id, lesson_id)
            
            if not progress:
                return None
            
            # Reset progress
            progress.restart()
            
            # Save to database
            updated_progress = await self.progress_repo.update(progress)
            
            if not updated_progress:
                return None
            
            return updated_progress.to_dict()
            
        except Exception as e:
            logger.error(f"Error resetting lesson progress: {str(e)}", exc_info=True)
            return None
    
    async def get_course_progress(self, user_id: str, course_id: str) -> Dict[str, Any]:
        """
        Get overall progress for a course.
        
        Args:
            user_id: User ID
            course_id: Course ID
            
        Returns:
            Dictionary containing course progress information
        """
        try:
            # Get course
            course = await self.course_repo.get_by_id(course_id)
            if not course:
                return None
            
            # Calculate overall progress
            progress_percentage, status_counts = await self.progress_repo.calculate_course_progress(
                user_id, course_id
            )
            
            # Get sections with their progress
            sections = await self.section_repo.get_by_course(course_id)
            section_progress = []
            
            for section in sections:
                # Get lessons in section
                lessons = await self.lesson_repo.get_by_section(section.id)
                lesson_progress = []
                
                for lesson in lessons:
                    # Get progress for each lesson
                    progress = await self.progress_repo.get_by_user_and_lesson(user_id, lesson.id)
                    
                    if not progress:
                        progress = LessonProgress(
                            user_id=user_id,
                            lesson_id=lesson.id,
                            status=ProgressStatus.NOT_STARTED,
                            progress_percentage=0.0,
                            last_position_seconds=0
                        )
                    
                    lesson_progress.append({
                        "lesson": {
                            "id": lesson.id,
                            "title": lesson.title,
                            "type": lesson.type
                        },
                        "progress": progress.to_dict()
                    })
                
                # Calculate section progress
                section_progress_percentage = 0.0
                if lessons:
                    total_progress = sum(
                        p["progress"]["progress_percentage"] 
                        for p in lesson_progress
                    )
                    section_progress_percentage = total_progress / len(lessons)
                
                section_progress.append({
                    "section": {
                        "id": section.id,
                        "title": section.title
                    },
                    "progress_percentage": section_progress_percentage,
                    "lessons": lesson_progress
                })
            
            # Get enrollment status
            enrollment = await self.course_repo.get_enrollment(user_id, course_id)
            
            return {
                "overall_percentage": progress_percentage,
                "status_counts": status_counts,
                "section_progress": section_progress,
                "enrollment": {
                    "status": enrollment.status if enrollment else "not_enrolled",
                    "progress_percentage": progress_percentage,
                    "completed_at": enrollment.completed_at.isoformat() if enrollment and enrollment.completed_at else None,
                    "certificate_id": enrollment.certificate_id if enrollment else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting course progress: {str(e)}", exc_info=True)
            return None
    
    async def get_section_progress(self, user_id: str, section_id: str) -> Dict[str, Any]:
        """
        Get progress for all lessons in a section.
        
        Args:
            user_id: User ID
            section_id: Section ID
            
        Returns:
            Dictionary with section progress details
        """
        try:
            # Get section
            section = await self.section_repo.get_by_id(section_id)
            if not section:
                return {
                    "section": None,
                    "progress_percentage": 0.0,
                    "lessons": []
                }
                
            # Get lessons in this section
            lessons = await self.lesson_repo.get_lessons_by_section_id(section_id)
            
            lesson_progress = []
            for lesson in lessons:
                # Get progress for this lesson
                progress = await self.progress_repo.get_by_user_and_lesson(user_id, lesson.id)
                
                lesson_progress.append({
                    "lesson": lesson,
                    "progress": progress
                })
            
            # Calculate section progress percentage
            if not lessons:
                section_percentage = 0.0
            else:
                completed = sum(1 for lp in lesson_progress if lp["progress"] and lp["progress"].status == ProgressStatus.COMPLETED)
                section_percentage = (completed / len(lessons)) * 100.0
            
            return {
                "section": section,
                "progress_percentage": section_percentage,
                "lessons": lesson_progress
            }
            
        except Exception as e:
            logger.error(f"Error getting section progress: {str(e)}", exc_info=True)
            return {
                "section": None,
                "progress_percentage": 0.0,
                "lessons": []
            }
    
    async def get_recent_activity(
        self, 
        user_id: str, 
        limit: int = 10,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get recent learning activity for a user.
        
        Args:
            user_id: User ID
            limit: Maximum number of activities to return
            days: Number of days to look back
            
        Returns:
            List of recent activities
        """
        try:
            # Get recent progress records
            recent_date = datetime.utcnow() - timedelta(days=days)
            
            # Query recent progress with lesson and course information
            query = """
            SELECT 
                lp.*,
                l.title as lesson_title,
                l.type as lesson_type,
                s.id as section_id,
                s.title as section_title,
                c.id as course_id,
                c.title as course_title
            FROM lesson_progress lp
            JOIN course_lessons l ON lp.lesson_id = l.id
            JOIN course_sections s ON l.section_id = s.id
            JOIN courses c ON s.course_id = c.id
            WHERE lp.user_id = :user_id
            AND lp.last_activity_at >= :recent_date
            ORDER BY lp.last_activity_at DESC
            LIMIT :limit
            """
            
            result = await self.db.execute(
                query,
                {
                    "user_id": user_id,
                    "recent_date": recent_date,
                    "limit": limit
                }
            )
            
            activities = []
            for row in result:
                activities.append({
                    "progress_id": row.id,
                    "lesson_id": row.lesson_id,
                    "lesson_title": row.lesson_title,
                    "lesson_type": row.lesson_type,
                    "section_id": row.section_id,
                    "section_title": row.section_title,
                    "course_id": row.course_id,
                    "course_title": row.course_title,
                    "status": row.status,
                    "progress_percentage": row.progress_percentage,
                    "last_position_seconds": row.last_position_seconds,
                    "last_activity_at": row.last_activity_at.isoformat()
                })
            
            return activities
            
        except Exception as e:
            logger.error(f"Error getting recent activity: {str(e)}", exc_info=True)
            return []
    
    async def get_learning_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get learning statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary containing learning statistics
        """
        try:
            # Get enrolled courses count
            enrolled_courses_query = """
            SELECT COUNT(DISTINCT course_id)
            FROM course_enrollments
            WHERE user_id = :user_id
            """
            
            # Get completed courses count
            completed_courses_query = """
            SELECT COUNT(DISTINCT course_id)
            FROM course_enrollments
            WHERE user_id = :user_id
            AND completed_at IS NOT NULL
            """
            
            # Get lessons accessed count
            lessons_accessed_query = """
            SELECT COUNT(DISTINCT lesson_id)
            FROM lesson_progress
            WHERE user_id = :user_id
            """
            
            # Get lessons completed count
            lessons_completed_query = """
            SELECT COUNT(DISTINCT lesson_id)
            FROM lesson_progress
            WHERE user_id = :user_id
            AND status = 'completed'
            """
            
            # Get total minutes watched
            minutes_watched_query = """
            SELECT COALESCE(SUM(last_position_seconds), 0) / 60
            FROM lesson_progress
            WHERE user_id = :user_id
            AND lesson_id IN (
                SELECT id FROM course_lessons WHERE type = 'video'
            )
            """
            
            # Get last activity timestamp
            last_activity_query = """
            SELECT MAX(last_activity_at)
            FROM lesson_progress
            WHERE user_id = :user_id
            """
            
            # Execute queries
            enrolled_courses = await self.db.execute(enrolled_courses_query, {"user_id": user_id})
            completed_courses = await self.db.execute(completed_courses_query, {"user_id": user_id})
            lessons_accessed = await self.db.execute(lessons_accessed_query, {"user_id": user_id})
            lessons_completed = await self.db.execute(lessons_completed_query, {"user_id": user_id})
            minutes_watched = await self.db.execute(minutes_watched_query, {"user_id": user_id})
            last_activity = await self.db.execute(last_activity_query, {"user_id": user_id})
            
            return {
                "enrolled_courses": enrolled_courses.scalar() or 0,
                "completed_courses": completed_courses.scalar() or 0,
                "active_courses": (enrolled_courses.scalar() or 0) - (completed_courses.scalar() or 0),
                "lessons_accessed": lessons_accessed.scalar() or 0,
                "lessons_completed": lessons_completed.scalar() or 0,
                "minutes_watched": int(minutes_watched.scalar() or 0),
                "last_activity_at": last_activity.scalar().isoformat() if last_activity.scalar() else None
            }
            
        except Exception as e:
            logger.error(f"Error getting learning stats: {str(e)}", exc_info=True)
            return {
                "enrolled_courses": 0,
                "completed_courses": 0,
                "active_courses": 0,
                "lessons_accessed": 0,
                "lessons_completed": 0,
                "minutes_watched": 0,
                "last_activity_at": None
            }
    
    async def _update_course_progress(self, user_id: str, lesson_id: str) -> None:
        """
        Helper method to update course progress after lesson progress change.
        
        Args:
            user_id: User ID
            lesson_id: Lesson ID
        """
        try:
            # Get lesson to find course
            lesson = await self.lesson_repo.get_by_id(lesson_id)
            if not lesson:
                return
                
            # Get section to find course
            section = await self.section_repo.get_by_id(lesson.section_id)
            if not section:
                return
                
            # Calculate course progress
            course_id = section.course_id
            course_progress, _ = await self.progress_repo.calculate_course_progress(
                user_id, course_id
            )
            
            # Update enrollment progress
            await self.enrollment_repo.update_progress(
                user_id, course_id, course_progress
            )
                
        except Exception as e:
            logger.error(f"Error updating course progress: {str(e)}", exc_info=True) 