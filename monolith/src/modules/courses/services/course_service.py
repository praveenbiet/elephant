from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import get_logger
from src.modules.courses.domain.course import Course, CourseStatus, CourseLevel
from src.modules.courses.domain.section import Section
from src.modules.courses.domain.lesson import Lesson
from src.modules.courses.domain.enrollment import Enrollment, EnrollmentStatus
from src.modules.courses.domain.review import Review
from src.modules.courses.persistence.course_repository import CourseRepository
from src.modules.courses.persistence.section_repository import SectionRepository
from src.modules.courses.persistence.lesson_repository import LessonRepository
from src.modules.courses.persistence.enrollment_repository import EnrollmentRepository
from src.modules.courses.persistence.review_repository import ReviewRepository
from src.modules.courses.persistence.category_repository import CategoryRepository

logger = get_logger(__name__)

class CourseService:
    """
    Service for course-related operations.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.course_repository = CourseRepository(db)
        self.section_repository = SectionRepository(db)
        self.lesson_repository = LessonRepository(db)
        self.enrollment_repository = EnrollmentRepository(db)
        self.review_repository = ReviewRepository(db)
        self.category_repository = CategoryRepository(db)
    
    async def get_course_by_id(self, course_id: str) -> Optional[Course]:
        """Get a course by ID."""
        return await self.course_repository.get_by_id(course_id)
    
    async def get_course_by_slug(self, slug: str) -> Optional[Course]:
        """Get a course by slug."""
        return await self.course_repository.get_by_slug(slug)
    
    async def create_course(self, course_data: Dict[str, Any]) -> Optional[Course]:
        """
        Create a new course.
        
        Args:
            course_data: Dictionary with course data
            
        Returns:
            Created course domain entity or None if creation failed
        """
        try:
            # Generate ID if not provided
            course_id = course_data.get('id') or str(uuid.uuid4())
            
            # Create course domain entity
            course = Course(
                id=course_id,
                title=course_data['title'],
                instructor_id=course_data['instructor_id'],
                description=course_data['description'],
                level=course_data.get('level', CourseLevel.ALL_LEVELS),
                status=course_data.get('status', CourseStatus.DRAFT),
                slug=course_data.get('slug'),
                short_description=course_data.get('short_description'),
                image_url=course_data.get('image_url'),
                category_id=course_data.get('category_id'),
                subcategory_ids=course_data.get('subcategory_ids', []),
                tags=course_data.get('tags', []),
                price=course_data.get('price'),
                sale_price=course_data.get('sale_price'),
                duration_minutes=course_data.get('duration_minutes'),
                skills_gained=course_data.get('skills_gained', []),
                requirements=course_data.get('requirements', []),
                language=course_data.get('language', 'en'),
                caption_languages=course_data.get('caption_languages', []),
                meta_keywords=course_data.get('meta_keywords'),
                meta_description=course_data.get('meta_description'),
                featured=course_data.get('featured', False)
            )
            
            # Create course in repository
            return await self.course_repository.create(course)
            
        except Exception as e:
            logger.error(f"Error creating course: {str(e)}", exc_info=True)
            return None
    
    async def update_course(self, course_id: str, course_data: Dict[str, Any]) -> Optional[Course]:
        """
        Update an existing course.
        
        Args:
            course_id: ID of the course to update
            course_data: Dictionary with updated course data
            
        Returns:
            Updated course domain entity or None if update failed
        """
        try:
            # Get existing course
            course = await self.course_repository.get_by_id(course_id)
            if not course:
                logger.error(f"Course with ID {course_id} not found for update")
                return None
            
            # Update course attributes
            if 'title' in course_data:
                course.title = course_data['title']
            if 'description' in course_data:
                course.description = course_data['description']
            if 'short_description' in course_data:
                course.short_description = course_data['short_description']
            if 'image_url' in course_data:
                course.image_url = course_data['image_url']
            if 'level' in course_data:
                course.level = course_data['level']
            if 'category_id' in course_data:
                course.category_id = course_data['category_id']
            if 'subcategory_ids' in course_data:
                course.subcategory_ids = course_data['subcategory_ids']
            if 'tags' in course_data:
                course.tags = course_data['tags']
            if 'price' in course_data:
                course.price = course_data['price']
            if 'sale_price' in course_data:
                course.sale_price = course_data['sale_price']
            if 'duration_minutes' in course_data:
                course.duration_minutes = course_data['duration_minutes']
            if 'skills_gained' in course_data:
                course.skills_gained = course_data['skills_gained']
            if 'requirements' in course_data:
                course.requirements = course_data['requirements']
            if 'language' in course_data:
                course.language = course_data['language']
            if 'caption_languages' in course_data:
                course.caption_languages = course_data['caption_languages']
            if 'meta_keywords' in course_data:
                course.meta_keywords = course_data['meta_keywords']
            if 'meta_description' in course_data:
                course.meta_description = course_data['meta_description']
            if 'featured' in course_data:
                course.featured = course_data['featured']
            if 'status' in course_data:
                course.status = course_data['status']
                if course_data['status'] == CourseStatus.PUBLISHED and not course.published_at:
                    course.published_at = datetime.utcnow()
            
            # Update course in repository
            return await self.course_repository.update(course)
            
        except Exception as e:
            logger.error(f"Error updating course {course_id}: {str(e)}", exc_info=True)
            return None
    
    async def delete_course(self, course_id: str) -> bool:
        """
        Delete a course.
        
        Args:
            course_id: ID of the course to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return await self.course_repository.delete(course_id)
            
        except Exception as e:
            logger.error(f"Error deleting course {course_id}: {str(e)}", exc_info=True)
            return False
    
    async def list_courses(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[CourseStatus] = None,
        instructor_id: Optional[str] = None,
        category_id: Optional[str] = None,
        level: Optional[CourseLevel] = None,
        featured: Optional[bool] = None,
        search_term: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Course], int]:
        """
        List courses with filtering, pagination, and sorting.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of results per page
            status: Filter by course status
            instructor_id: Filter by instructor ID
            category_id: Filter by category ID
            level: Filter by course level
            featured: Filter by featured status
            search_term: Search in title and description
            sort_by: Field to sort by
            sort_order: Sort order ("asc" or "desc")
            
        Returns:
            Tuple of (list of courses, total count)
        """
        try:
            return await self.course_repository.list_courses(
                page=page,
                page_size=page_size,
                status=status,
                instructor_id=instructor_id,
                category_id=category_id,
                level=level,
                featured=featured,
                search_term=search_term,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
        except Exception as e:
            logger.error(f"Error listing courses: {str(e)}", exc_info=True)
            return [], 0
    
    async def publish_course(self, course_id: str) -> Optional[Course]:
        """
        Publish a course.
        
        Args:
            course_id: ID of the course to publish
            
        Returns:
            Updated course domain entity, or None if update failed
        """
        try:
            # Check if course has at least one section with content
            sections = await self.section_repository.get_sections_by_course_id(course_id)
            if not sections:
                logger.error(f"Cannot publish course {course_id} without any sections")
                return None
            
            # Check if at least one section has lessons
            has_content = False
            for section in sections:
                lessons_count = await self.lesson_repository.count_lessons(section.id)
                if lessons_count > 0:
                    has_content = True
                    break
            
            if not has_content:
                logger.error(f"Cannot publish course {course_id} without any lessons")
                return None
            
            # Publish the course
            return await self.course_repository.publish_course(course_id)
            
        except Exception as e:
            logger.error(f"Error publishing course {course_id}: {str(e)}", exc_info=True)
            return None
    
    async def unpublish_course(self, course_id: str) -> Optional[Course]:
        """
        Unpublish a course (set to draft).
        
        Args:
            course_id: ID of the course to unpublish
            
        Returns:
            Updated course domain entity, or None if update failed
        """
        try:
            return await self.course_repository.unpublish_course(course_id)
            
        except Exception as e:
            logger.error(f"Error unpublishing course {course_id}: {str(e)}", exc_info=True)
            return None
    
    async def get_course_with_sections_and_lessons(self, course_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a course with all its sections and lessons.
        
        Args:
            course_id: Course ID
            
        Returns:
            Dictionary with course, sections, and lessons
        """
        try:
            # Get course
            course = await self.course_repository.get_by_id(course_id)
            if not course:
                return None
            
            # Get sections
            sections = await self.section_repository.get_sections_by_course_id(course_id)
            
            # Get lessons for each section
            result = {
                "course": course,
                "sections": []
            }
            
            for section in sections:
                lessons = await self.lesson_repository.get_lessons_by_section_id(section.id)
                result["sections"].append({
                    "section": section,
                    "lessons": lessons
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting course with sections and lessons for {course_id}: {str(e)}", exc_info=True)
            return None
    
    async def get_course_statistics(self, course_id: str) -> Dict[str, Any]:
        """
        Get statistics for a course including enrollment and review data.
        
        Args:
            course_id: Course ID
            
        Returns:
            Dictionary with course statistics
        """
        try:
            # Get enrollment statistics
            enrollment_stats = await self.enrollment_repository.count_enrollments_by_status(course_id)
            
            # Get total enrolled students (active + completed)
            total_enrolled = enrollment_stats.get(EnrollmentStatus.ACTIVE.value, 0) + enrollment_stats.get(EnrollmentStatus.COMPLETED.value, 0)
            
            # Get rating statistics
            rating_stats = await self.review_repository.get_course_rating_stats(course_id)
            
            # Get section and lesson counts
            sections = await self.section_repository.get_sections_by_course_id(course_id)
            section_count = len(sections)
            
            lesson_count = 0
            for section in sections:
                lesson_count += await self.lesson_repository.count_lessons(section.id)
            
            # Calculate total duration
            course = await self.course_repository.get_by_id(course_id)
            duration_minutes = course.duration_minutes or 0
            
            return {
                "enrollment_stats": {
                    "total_enrolled": total_enrolled,
                    "active": enrollment_stats.get(EnrollmentStatus.ACTIVE.value, 0),
                    "completed": enrollment_stats.get(EnrollmentStatus.COMPLETED.value, 0),
                    "refunded": enrollment_stats.get(EnrollmentStatus.REFUNDED.value, 0),
                    "expired": enrollment_stats.get(EnrollmentStatus.EXPIRED.value, 0),
                    "paused": enrollment_stats.get(EnrollmentStatus.PAUSED.value, 0)
                },
                "content_stats": {
                    "section_count": section_count,
                    "lesson_count": lesson_count,
                    "duration_minutes": duration_minutes
                },
                "rating_stats": rating_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting course statistics for {course_id}: {str(e)}", exc_info=True)
            return {
                "enrollment_stats": {
                    "total_enrolled": 0,
                    "active": 0,
                    "completed": 0,
                    "refunded": 0,
                    "expired": 0,
                    "paused": 0
                },
                "content_stats": {
                    "section_count": 0,
                    "lesson_count": 0,
                    "duration_minutes": 0
                },
                "rating_stats": {
                    "average_rating": 0.0,
                    "total_reviews": 0,
                    "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
                }
            }
    
    async def get_instructor_courses(
        self, 
        instructor_id: str,
        include_drafts: bool = False
    ) -> List[Course]:
        """
        Get all courses by an instructor.
        
        Args:
            instructor_id: Instructor user ID
            include_drafts: Whether to include draft courses
            
        Returns:
            List of course domain entities
        """
        try:
            return await self.course_repository.get_courses_by_instructor(
                instructor_id=instructor_id,
                include_drafts=include_drafts
            )
            
        except Exception as e:
            logger.error(f"Error getting courses for instructor {instructor_id}: {str(e)}", exc_info=True)
            return []
    
    async def get_featured_courses(self, limit: int = 10) -> List[Course]:
        """
        Get featured courses.
        
        Args:
            limit: Maximum number of courses to return
            
        Returns:
            List of course domain entities
        """
        try:
            return await self.course_repository.get_featured_courses(limit=limit)
            
        except Exception as e:
            logger.error(f"Error getting featured courses: {str(e)}", exc_info=True)
            return []
    
    async def get_top_rated_courses(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top-rated courses with average rating.
        
        Args:
            limit: Maximum number of courses to return
            
        Returns:
            List of dictionaries with course and rating info
        """
        try:
            return await self.course_repository.get_top_rated_courses(limit=limit)
            
        except Exception as e:
            logger.error(f"Error getting top rated courses: {str(e)}", exc_info=True)
            return [] 