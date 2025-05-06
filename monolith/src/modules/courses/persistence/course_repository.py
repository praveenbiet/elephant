import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy import select, update, delete, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

from src.common.logger import get_logger
from src.modules.courses.domain.course import Course, CourseStatus, CourseLevel
from src.modules.courses.models.course import CourseModel
from src.modules.courses.models.enrollment import EnrollmentModel
from src.modules.courses.models.review import ReviewModel

logger = get_logger(__name__)

class CourseRepository:
    """
    Repository for course-related database operations.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, course_id: str) -> Optional[Course]:
        """
        Get a course by ID.
        
        Args:
            course_id: Course ID
            
        Returns:
            Course domain entity if found, None otherwise
        """
        try:
            query = select(CourseModel).where(CourseModel.id == course_id)
            result = await self.db.execute(query)
            course_model = result.scalars().first()
            
            if not course_model:
                return None
                
            return self._map_to_domain(course_model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting course by ID {course_id}: {str(e)}", exc_info=True)
            return None
    
    async def get_by_slug(self, slug: str) -> Optional[Course]:
        """
        Get a course by slug.
        
        Args:
            slug: Course slug
            
        Returns:
            Course domain entity if found, None otherwise
        """
        try:
            query = select(CourseModel).where(CourseModel.slug == slug)
            result = await self.db.execute(query)
            course_model = result.scalars().first()
            
            if not course_model:
                return None
                
            return self._map_to_domain(course_model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting course by slug {slug}: {str(e)}", exc_info=True)
            return None
    
    async def create(self, course: Course) -> Optional[Course]:
        """
        Create a new course.
        
        Args:
            course: Course domain entity
            
        Returns:
            Created course domain entity with ID, or None if creation failed
        """
        try:
            # Generate ID if not provided
            if not course.id:
                course.id = str(uuid.uuid4())
            
            # Generate slug if not provided
            if not course.slug:
                base_slug = self._generate_slug_from_title(course.title)
                course.slug = await self._ensure_unique_slug(base_slug)
            
            # Create model from domain entity
            course_model = CourseModel(
                id=course.id,
                slug=course.slug,
                title=course.title,
                instructor_id=course.instructor_id,
                description=course.description,
                short_description=course.short_description,
                image_url=course.image_url,
                level=course.level,
                status=course.status,
                category_id=course.category_id,
                subcategory_ids=course.subcategory_ids,
                tags=course.tags,
                price=course.price,
                sale_price=course.sale_price,
                duration_minutes=course.duration_minutes,
                skills_gained=course.skills_gained,
                requirements=course.requirements,
                language=course.language,
                caption_languages=course.caption_languages,
                meta_keywords=course.meta_keywords,
                meta_description=course.meta_description,
                featured=course.featured,
                published_at=course.published_at,
                created_at=course.created_at or datetime.utcnow(),
                updated_at=course.updated_at or datetime.utcnow()
            )
            
            self.db.add(course_model)
            await self.db.commit()
            await self.db.refresh(course_model)
            
            # Return domain entity with updated data
            return self._map_to_domain(course_model)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error creating course {course.title}: {str(e)}", exc_info=True)
            return None
    
    async def update(self, course: Course) -> Optional[Course]:
        """
        Update an existing course.
        
        Args:
            course: Course domain entity with updated values
            
        Returns:
            Updated course domain entity, or None if update failed
        """
        try:
            # Check if course exists
            existing_course = await self.get_by_id(course.id)
            if not existing_course:
                logger.error(f"Course with ID {course.id} not found for update")
                return None
            
            # Update the course
            query = update(CourseModel).where(CourseModel.id == course.id).values(
                title=course.title,
                description=course.description,
                short_description=course.short_description,
                image_url=course.image_url,
                level=course.level,
                status=course.status,
                category_id=course.category_id,
                subcategory_ids=course.subcategory_ids,
                tags=course.tags,
                price=course.price,
                sale_price=course.sale_price,
                duration_minutes=course.duration_minutes,
                skills_gained=course.skills_gained,
                requirements=course.requirements,
                language=course.language,
                caption_languages=course.caption_languages,
                meta_keywords=course.meta_keywords,
                meta_description=course.meta_description,
                featured=course.featured,
                published_at=course.published_at,
                updated_at=datetime.utcnow()
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            # Get the updated course
            return await self.get_by_id(course.id)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error updating course {course.id}: {str(e)}", exc_info=True)
            return None
    
    async def delete(self, course_id: str) -> bool:
        """
        Delete a course.
        
        Args:
            course_id: ID of the course to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = delete(CourseModel).where(CourseModel.id == course_id)
            result = await self.db.execute(query)
            await self.db.commit()
            
            return result.rowcount > 0
            
        except SQLAlchemyError as e:
            await self.db.rollback()
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
            # Build query
            query = select(CourseModel)
            count_query = select(func.count(CourseModel.id))
            
            # Apply filters
            if status:
                query = query.where(CourseModel.status == status)
                count_query = count_query.where(CourseModel.status == status)
            
            if instructor_id:
                query = query.where(CourseModel.instructor_id == instructor_id)
                count_query = count_query.where(CourseModel.instructor_id == instructor_id)
            
            if category_id:
                query = query.where(CourseModel.category_id == category_id)
                count_query = count_query.where(CourseModel.category_id == category_id)
            
            if level:
                query = query.where(CourseModel.level == level)
                count_query = count_query.where(CourseModel.level == level)
            
            if featured is not None:
                query = query.where(CourseModel.featured == featured)
                count_query = count_query.where(CourseModel.featured == featured)
            
            if search_term:
                search_pattern = f"%{search_term}%"
                query = query.where(
                    (CourseModel.title.ilike(search_pattern)) | 
                    (CourseModel.description.ilike(search_pattern))
                )
                count_query = count_query.where(
                    (CourseModel.title.ilike(search_pattern)) | 
                    (CourseModel.description.ilike(search_pattern))
                )
            
            # Get total count
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()
            
            # Apply sorting
            sort_column = getattr(CourseModel, sort_by, CourseModel.created_at)
            if sort_order.lower() == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))
            
            # Apply pagination
            query = query.offset((page - 1) * page_size).limit(page_size)
            
            # Execute query
            result = await self.db.execute(query)
            course_models = result.scalars().all()
            
            # Map to domain entities
            courses = [self._map_to_domain(course_model) for course_model in course_models]
            
            return courses, total_count
            
        except SQLAlchemyError as e:
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
            now = datetime.utcnow()
            query = update(CourseModel).where(CourseModel.id == course_id).values(
                status=CourseStatus.PUBLISHED,
                published_at=now,
                updated_at=now
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            return await self.get_by_id(course_id)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
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
            query = update(CourseModel).where(CourseModel.id == course_id).values(
                status=CourseStatus.DRAFT,
                updated_at=datetime.utcnow()
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            return await self.get_by_id(course_id)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error unpublishing course {course_id}: {str(e)}", exc_info=True)
            return None
    
    async def get_courses_by_instructor(
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
            query = select(CourseModel).where(CourseModel.instructor_id == instructor_id)
            
            if not include_drafts:
                query = query.where(CourseModel.status != CourseStatus.DRAFT)
                
            result = await self.db.execute(query)
            course_models = result.scalars().all()
            
            return [self._map_to_domain(course_model) for course_model in course_models]
            
        except SQLAlchemyError as e:
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
            query = select(CourseModel).where(
                CourseModel.featured == True,
                CourseModel.status == CourseStatus.PUBLISHED
            ).order_by(
                desc(CourseModel.published_at)
            ).limit(limit)
            
            result = await self.db.execute(query)
            course_models = result.scalars().all()
            
            return [self._map_to_domain(course_model) for course_model in course_models]
            
        except SQLAlchemyError as e:
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
            # This requires a custom query to calculate average ratings
            sql = """
            SELECT 
                c.*, 
                AVG(r.rating) as avg_rating,
                COUNT(r.id) as review_count
            FROM courses c
            JOIN reviews r ON c.id = r.course_id
            WHERE c.status = 'published'
            GROUP BY c.id
            HAVING COUNT(r.id) >= 5  -- Minimum number of reviews
            ORDER BY avg_rating DESC, review_count DESC
            LIMIT :limit
            """
            
            result = await self.db.execute(text(sql), {"limit": limit})
            courses_data = result.mappings().all()
            
            # Process results
            top_courses = []
            for data in courses_data:
                course_model = CourseModel(**{k: data[k] for k in data.keys() if k not in ['avg_rating', 'review_count']})
                course = self._map_to_domain(course_model)
                
                top_courses.append({
                    "course": course,
                    "avg_rating": float(data["avg_rating"]),
                    "review_count": int(data["review_count"])
                })
                
            return top_courses
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting top rated courses: {str(e)}", exc_info=True)
            return []
    
    async def _ensure_unique_slug(self, base_slug: str) -> str:
        """
        Ensure a slug is unique by appending a number if necessary.
        
        Args:
            base_slug: Base slug to check
            
        Returns:
            Unique slug
        """
        slug = base_slug
        counter = 1
        
        while True:
            # Check if slug exists
            query = select(CourseModel.id).where(CourseModel.slug == slug)
            result = await self.db.execute(query)
            if not result.scalar_one_or_none():
                return slug
            
            # If it exists, append counter and increment
            slug = f"{base_slug}-{counter}"
            counter += 1
    
    def _generate_slug_from_title(self, title: str) -> str:
        """
        Generate a slug from a course title.
        
        Args:
            title: Course title
            
        Returns:
            Generated slug
        """
        # This is a simple implementation; a real one would handle special characters better
        slug = title.lower().replace(" ", "-")
        # Remove special characters
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        return slug
    
    def _map_to_domain(self, course_model: CourseModel) -> Course:
        """
        Map database model to domain entity.
        
        Args:
            course_model: Database model
            
        Returns:
            Domain entity
        """
        return Course(
            id=course_model.id,
            slug=course_model.slug,
            title=course_model.title,
            instructor_id=course_model.instructor_id,
            description=course_model.description,
            short_description=course_model.short_description,
            image_url=course_model.image_url,
            level=course_model.level,
            status=course_model.status,
            category_id=course_model.category_id,
            subcategory_ids=course_model.subcategory_ids or [],
            tags=course_model.tags or [],
            price=course_model.price,
            sale_price=course_model.sale_price,
            duration_minutes=course_model.duration_minutes,
            skills_gained=course_model.skills_gained or [],
            requirements=course_model.requirements or [],
            language=course_model.language,
            caption_languages=course_model.caption_languages or [],
            meta_keywords=course_model.meta_keywords,
            meta_description=course_model.meta_description,
            featured=course_model.featured,
            published_at=course_model.published_at,
            created_at=course_model.created_at,
            updated_at=course_model.updated_at
        ) 