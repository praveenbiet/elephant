from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import get_logger
from src.modules.courses.domain.progress import LessonProgress, ProgressStatus
from src.modules.courses.persistence.progress_repository import ProgressRepository
from src.modules.courses.persistence.enrollment_repository import EnrollmentRepository
from src.modules.courses.persistence.lesson_repository import LessonRepository
from src.modules.courses.persistence.section_repository import SectionRepository

logger = get_logger(__name__)

class ProgressService:
    """
    Service for progress-related operations.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.progress_repository = ProgressRepository(db)
        self.enrollment_repository = EnrollmentRepository(db)
        self.lesson_repository = LessonRepository(db)
        self.section_repository = SectionRepository(db)
    
    async def get_lesson_progress(self, user_id: str, lesson_id: str) -> Optional[LessonProgress]:
        """
        Get progress for a specific lesson.
        
        Args:
            user_id: User ID
            lesson_id: Lesson ID
            
        Returns:
            LessonProgress entity if found, None otherwise
        """
        try:
            return await self.progress_repository.get_by_user_and_lesson(user_id, lesson_id)
        
        except Exception as e:
            logger.error(f"Error getting lesson progress: {str(e)}", exc_info=True)
            return None
    
    async def update_lesson_progress(
        self, 
        user_id: str, 
        lesson_id: str, 
        progress_percentage: float,
        position_seconds: Optional[int] = None
    ) -> Optional[LessonProgress]:
        """
        Update progress for a specific lesson.
        
        Args:
            user_id: User ID
            lesson_id: Lesson ID
            progress_percentage: Progress percentage (0.0 to 100.0)
            position_seconds: Current position in seconds for video content
            
        Returns:
            Updated LessonProgress entity if successful, None otherwise
        """
        try:
            # Update lesson progress
            progress = await self.progress_repository.update_lesson_progress(
                user_id, lesson_id, progress_percentage, position_seconds
            )
            
            if not progress:
                return None
            
            # Get lesson to find course
            lesson = await self.lesson_repository.get_by_id(lesson_id)
            if not lesson:
                return progress
                
            # Get section to find course
            section = await self.section_repository.get_by_id(lesson.section_id)
            if not section:
                return progress
                
            # Update course progress in enrollment
            course_id = section.course_id
            
            # Calculate course progress
            course_progress, _ = await self.progress_repository.calculate_course_progress(
                user_id, course_id
            )
            
            # Update enrollment progress
            await self.enrollment_repository.update_progress(
                user_id, course_id, course_progress
            )
                
            return progress
            
        except Exception as e:
            logger.error(f"Error updating lesson progress: {str(e)}", exc_info=True)
            return None
    
    async def mark_lesson_completed(self, user_id: str, lesson_id: str) -> Optional[LessonProgress]:
        """
        Mark a lesson as completed.
        
        Args:
            user_id: User ID
            lesson_id: Lesson ID
            
        Returns:
            Updated LessonProgress entity if successful, None otherwise
        """
        try:
            # Get existing progress
            progress = await self.progress_repository.get_by_user_and_lesson(user_id, lesson_id)
            
            if not progress:
                # Create new progress record
                progress = LessonProgress(
                    user_id=user_id,
                    lesson_id=lesson_id
                )
            
            # Mark as completed
            progress.complete()
            
            # Save to database
            if progress.id:
                updated_progress = await self.progress_repository.update(progress)
            else:
                updated_progress = await self.progress_repository.create(progress)
            
            if not updated_progress:
                return None
                
            # Update course progress
            await self._update_course_progress(user_id, lesson_id)
                
            return updated_progress
            
        except Exception as e:
            logger.error(f"Error marking lesson as completed: {str(e)}", exc_info=True)
            return None
    
    async def reset_lesson_progress(self, user_id: str, lesson_id: str) -> Optional[LessonProgress]:
        """
        Reset progress for a specific lesson.
        
        Args:
            user_id: User ID
            lesson_id: Lesson ID
            
        Returns:
            Updated LessonProgress entity if successful, None otherwise
        """
        try:
            # Get existing progress
            progress = await self.progress_repository.get_by_user_and_lesson(user_id, lesson_id)
            
            if not progress:
                return None
            
            # Reset progress
            progress.restart()
            
            # Save to database
            updated_progress = await self.progress_repository.update(progress)
            
            if not updated_progress:
                return None
                
            # Update course progress
            await self._update_course_progress(user_id, lesson_id)
                
            return updated_progress
            
        except Exception as e:
            logger.error(f"Error resetting lesson progress: {str(e)}", exc_info=True)
            return None
    
    async def get_course_progress(self, user_id: str, course_id: str) -> Dict[str, Any]:
        """
        Get detailed progress for a course.
        
        Args:
            user_id: User ID
            course_id: Course ID
            
        Returns:
            Dictionary with course progress details
        """
        try:
            # Calculate overall course progress
            progress_percentage, status_counts = await self.progress_repository.calculate_course_progress(
                user_id, course_id
            )
            
            # Get sections in the course
            sections = await self.section_repository.get_sections_by_course_id(course_id)
            
            section_progress = []
            for section in sections:
                # Get lessons in this section
                lessons = await self.lesson_repository.get_lessons_by_section_id(section.id)
                
                lesson_progress = []
                for lesson in lessons:
                    # Get progress for this lesson
                    progress = await self.progress_repository.get_by_user_and_lesson(user_id, lesson.id)
                    
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
                
                section_progress.append({
                    "section": section,
                    "progress_percentage": section_percentage,
                    "lessons": lesson_progress
                })
            
            # Get enrollment record to check certificate
            enrollment = await self.enrollment_repository.get_by_user_and_course(user_id, course_id)
            
            return {
                "overall_percentage": progress_percentage,
                "status_counts": status_counts,
                "section_progress": section_progress,
                "enrollment": enrollment
            }
            
        except Exception as e:
            logger.error(f"Error getting course progress: {str(e)}", exc_info=True)
            return {
                "overall_percentage": 0.0,
                "status_counts": {"not_started": 0, "in_progress": 0, "completed": 0},
                "section_progress": [],
                "enrollment": None
            }
    
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
            section = await self.section_repository.get_by_id(section_id)
            if not section:
                return {
                    "section": None,
                    "progress_percentage": 0.0,
                    "lessons": []
                }
                
            # Get lessons in this section
            lessons = await self.lesson_repository.get_lessons_by_section_id(section_id)
            
            lesson_progress = []
            for lesson in lessons:
                # Get progress for this lesson
                progress = await self.progress_repository.get_by_user_and_lesson(user_id, lesson.id)
                
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
    
    async def get_recent_activity(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get user's recent learning activity across all courses.
        
        Args:
            user_id: User ID
            limit: Maximum number of activities to return
            
        Returns:
            List of recent activity items
        """
        try:
            # Query to get recent activity from lesson progress
            recent_activity_query = """
            SELECT 
                lp.id,
                lp.user_id,
                lp.lesson_id,
                lp.status,
                lp.progress_percentage,
                lp.last_position_seconds,
                lp.last_activity_at,
                l.title as lesson_title,
                l.type as lesson_type,
                s.id as section_id,
                s.title as section_title,
                c.id as course_id,
                c.title as course_title,
                c.image_url as course_image
            FROM lesson_progress lp
            JOIN course_lessons l ON lp.lesson_id = l.id
            JOIN course_sections s ON l.section_id = s.id
            JOIN courses c ON s.course_id = c.id
            WHERE lp.user_id = :user_id
            ORDER BY lp.last_activity_at DESC
            LIMIT :limit
            """
            
            # Execute query
            result = await self.db.execute(
                recent_activity_query,
                {"user_id": user_id, "limit": limit}
            )
            
            # Process results
            activities = []
            for row in result.mappings():
                activities.append({
                    "progress_id": row["id"],
                    "lesson_id": row["lesson_id"],
                    "lesson_title": row["lesson_title"],
                    "lesson_type": row["lesson_type"],
                    "section_id": row["section_id"],
                    "section_title": row["section_title"],
                    "course_id": row["course_id"],
                    "course_title": row["course_title"],
                    "course_image": row["course_image"],
                    "status": row["status"],
                    "progress_percentage": row["progress_percentage"],
                    "last_position_seconds": row["last_position_seconds"],
                    "last_activity_at": row["last_activity_at"]
                })
                
            return activities
            
        except Exception as e:
            logger.error(f"Error getting recent activity: {str(e)}", exc_info=True)
            return []
    
    async def get_learning_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get overall learning statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with learning statistics
        """
        try:
            # Query to get overall statistics
            stats_query = """
            SELECT 
                COUNT(DISTINCT e.course_id) as enrolled_courses,
                COUNT(DISTINCT CASE WHEN e.status = 'completed' THEN e.course_id END) as completed_courses,
                COUNT(DISTINCT CASE WHEN e.status = 'active' THEN e.course_id END) as active_courses,
                COUNT(DISTINCT lp.lesson_id) as lessons_accessed,
                COUNT(DISTINCT CASE WHEN lp.status = 'completed' THEN lp.lesson_id END) as lessons_completed,
                SUM(CASE WHEN lp.status = 'completed' THEN l.duration_minutes ELSE 0 END) as minutes_watched
            FROM enrollments e
            LEFT JOIN course_sections s ON e.course_id = s.course_id
            LEFT JOIN course_lessons l ON s.id = l.section_id
            LEFT JOIN lesson_progress lp ON l.id = lp.lesson_id AND lp.user_id = e.user_id
            WHERE e.user_id = :user_id
            """
            
            # Execute query
            result = await self.db.execute(stats_query, {"user_id": user_id})
            stats = result.mappings().first()
            
            # Get most recent activity
            recent_activities = await self.get_recent_activity(user_id, 1)
            last_activity_at = recent_activities[0]["last_activity_at"] if recent_activities else None
            
            return {
                "enrolled_courses": stats["enrolled_courses"] or 0,
                "completed_courses": stats["completed_courses"] or 0,
                "active_courses": stats["active_courses"] or 0,
                "lessons_accessed": stats["lessons_accessed"] or 0,
                "lessons_completed": stats["lessons_completed"] or 0,
                "minutes_watched": stats["minutes_watched"] or 0,
                "last_activity_at": last_activity_at
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
            lesson = await self.lesson_repository.get_by_id(lesson_id)
            if not lesson:
                return
                
            # Get section to find course
            section = await self.section_repository.get_by_id(lesson.section_id)
            if not section:
                return
                
            # Calculate course progress
            course_id = section.course_id
            course_progress, _ = await self.progress_repository.calculate_course_progress(
                user_id, course_id
            )
            
            # Update enrollment progress
            await self.enrollment_repository.update_progress(
                user_id, course_id, course_progress
            )
                
        except Exception as e:
            logger.error(f"Error updating course progress: {str(e)}", exc_info=True) 