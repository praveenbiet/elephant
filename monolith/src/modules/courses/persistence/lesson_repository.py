import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, update, delete, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from src.common.logger import get_logger
from src.modules.courses.domain.lesson import Lesson, LessonType
from src.modules.courses.models.course import LessonModel

logger = get_logger(__name__)

class LessonRepository:
    """
    Repository for lesson-related database operations.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, lesson_id: str) -> Optional[Lesson]:
        """
        Get a lesson by ID.
        
        Args:
            lesson_id: Lesson ID
            
        Returns:
            Lesson domain entity if found, None otherwise
        """
        try:
            query = select(LessonModel).where(LessonModel.id == lesson_id)
            result = await self.db.execute(query)
            lesson_model = result.scalars().first()
            
            if not lesson_model:
                return None
                
            return self._map_to_domain(lesson_model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting lesson by ID {lesson_id}: {str(e)}", exc_info=True)
            return None
    
    async def get_lessons_by_section_id(self, section_id: str) -> List[Lesson]:
        """
        Get all lessons for a section.
        
        Args:
            section_id: Section ID
            
        Returns:
            List of lesson domain entities sorted by position
        """
        try:
            query = select(LessonModel).where(
                LessonModel.section_id == section_id
            ).order_by(
                LessonModel.position
            )
            
            result = await self.db.execute(query)
            lesson_models = result.scalars().all()
            
            return [self._map_to_domain(model) for model in lesson_models]
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting lessons for section {section_id}: {str(e)}", exc_info=True)
            return []
    
    async def create(self, lesson: Lesson) -> Optional[Lesson]:
        """
        Create a new lesson.
        
        Args:
            lesson: Lesson domain entity
            
        Returns:
            Created lesson domain entity with ID, or None if creation failed
        """
        try:
            # Generate ID if not provided
            if not lesson.id:
                lesson.id = str(uuid.uuid4())
            
            # Create model from domain entity
            lesson_model = LessonModel(
                id=lesson.id,
                section_id=lesson.section_id,
                title=lesson.title,
                type=lesson.type.value if isinstance(lesson.type, LessonType) else lesson.type,
                content_id=lesson.content_id,
                description=lesson.description,
                position=lesson.position,
                duration_minutes=lesson.duration_minutes,
                is_free_preview=lesson.is_free_preview,
                is_downloadable=lesson.is_downloadable,
                preview_image_url=lesson.preview_image_url,
                attachments=lesson.attachments,
                created_at=lesson.created_at or datetime.utcnow(),
                updated_at=lesson.updated_at or datetime.utcnow()
            )
            
            self.db.add(lesson_model)
            await self.db.commit()
            await self.db.refresh(lesson_model)
            
            # Return domain entity with updated data
            return self._map_to_domain(lesson_model)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error creating lesson {lesson.title}: {str(e)}", exc_info=True)
            return None
    
    async def update(self, lesson: Lesson) -> Optional[Lesson]:
        """
        Update an existing lesson.
        
        Args:
            lesson: Lesson domain entity with updated values
            
        Returns:
            Updated lesson domain entity, or None if update failed
        """
        try:
            # Check if lesson exists
            existing_lesson = await self.get_by_id(lesson.id)
            if not existing_lesson:
                logger.error(f"Lesson with ID {lesson.id} not found for update")
                return None
            
            # Update the lesson
            query = update(LessonModel).where(LessonModel.id == lesson.id).values(
                title=lesson.title,
                type=lesson.type.value if isinstance(lesson.type, LessonType) else lesson.type,
                content_id=lesson.content_id,
                description=lesson.description,
                position=lesson.position,
                duration_minutes=lesson.duration_minutes,
                is_free_preview=lesson.is_free_preview,
                is_downloadable=lesson.is_downloadable,
                preview_image_url=lesson.preview_image_url,
                attachments=lesson.attachments,
                updated_at=datetime.utcnow()
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            # Get the updated lesson
            return await self.get_by_id(lesson.id)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error updating lesson {lesson.id}: {str(e)}", exc_info=True)
            return None
    
    async def delete(self, lesson_id: str) -> bool:
        """
        Delete a lesson.
        
        Args:
            lesson_id: ID of the lesson to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = delete(LessonModel).where(LessonModel.id == lesson_id)
            result = await self.db.execute(query)
            await self.db.commit()
            
            return result.rowcount > 0
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error deleting lesson {lesson_id}: {str(e)}", exc_info=True)
            return False
    
    async def reorder_lessons(self, section_id: str, lesson_ids: List[str]) -> bool:
        """
        Reorder lessons within a section.
        
        Args:
            section_id: Section ID
            lesson_ids: List of lesson IDs in the desired order
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Verify all lessons belong to the section
            query = select(func.count(LessonModel.id)).where(
                LessonModel.section_id == section_id,
                LessonModel.id.in_(lesson_ids)
            )
            result = await self.db.execute(query)
            count = result.scalar()
            
            if count != len(lesson_ids):
                logger.error(f"Not all lessons belong to section {section_id}")
                return False
            
            # Update positions
            for position, lesson_id in enumerate(lesson_ids, 1):
                await self.db.execute(
                    update(LessonModel).where(
                        LessonModel.id == lesson_id
                    ).values(
                        position=position,
                        updated_at=datetime.utcnow()
                    )
                )
            
            await self.db.commit()
            return True
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error reordering lessons for section {section_id}: {str(e)}", exc_info=True)
            return False
    
    async def get_free_preview_lessons(self, section_id: str) -> List[Lesson]:
        """
        Get all free preview lessons for a section.
        
        Args:
            section_id: Section ID
            
        Returns:
            List of lesson domain entities that are marked as free preview
        """
        try:
            query = select(LessonModel).where(
                LessonModel.section_id == section_id,
                LessonModel.is_free_preview == True
            ).order_by(
                LessonModel.position
            )
            
            result = await self.db.execute(query)
            lesson_models = result.scalars().all()
            
            return [self._map_to_domain(model) for model in lesson_models]
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting free preview lessons for section {section_id}: {str(e)}", exc_info=True)
            return []
    
    async def get_next_position(self, section_id: str) -> int:
        """
        Get the next available position for a new lesson in a section.
        
        Args:
            section_id: Section ID
            
        Returns:
            Next position (1 if no lessons exist)
        """
        try:
            query = select(func.max(LessonModel.position)).where(
                LessonModel.section_id == section_id
            )
            
            result = await self.db.execute(query)
            max_position = result.scalar() or 0
            
            return max_position + 1
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting next position for section {section_id}: {str(e)}", exc_info=True)
            return 1
    
    async def get_lessons_by_type(
        self, 
        section_id: str, 
        lesson_type: LessonType
    ) -> List[Lesson]:
        """
        Get all lessons of a specific type in a section.
        
        Args:
            section_id: Section ID
            lesson_type: Type of lessons to retrieve
            
        Returns:
            List of lesson domain entities of the specified type
        """
        try:
            type_value = lesson_type.value if isinstance(lesson_type, LessonType) else lesson_type
            
            query = select(LessonModel).where(
                LessonModel.section_id == section_id,
                LessonModel.type == type_value
            ).order_by(
                LessonModel.position
            )
            
            result = await self.db.execute(query)
            lesson_models = result.scalars().all()
            
            return [self._map_to_domain(model) for model in lesson_models]
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting lessons of type {lesson_type} for section {section_id}: {str(e)}", exc_info=True)
            return []
    
    async def count_lessons(self, section_id: str) -> int:
        """
        Count the number of lessons in a section.
        
        Args:
            section_id: Section ID
            
        Returns:
            Number of lessons in the section
        """
        try:
            query = select(func.count(LessonModel.id)).where(
                LessonModel.section_id == section_id
            )
            
            result = await self.db.execute(query)
            count = result.scalar() or 0
            
            return count
            
        except SQLAlchemyError as e:
            logger.error(f"Error counting lessons for section {section_id}: {str(e)}", exc_info=True)
            return 0
    
    def _map_to_domain(self, lesson_model: LessonModel) -> Lesson:
        """
        Map database model to domain entity.
        
        Args:
            lesson_model: Database model
            
        Returns:
            Domain entity
        """
        return Lesson(
            id=lesson_model.id,
            section_id=lesson_model.section_id,
            title=lesson_model.title,
            type=lesson_model.type,
            content_id=lesson_model.content_id,
            description=lesson_model.description,
            position=lesson_model.position,
            duration_minutes=lesson_model.duration_minutes,
            is_free_preview=lesson_model.is_free_preview,
            is_downloadable=lesson_model.is_downloadable,
            preview_image_url=lesson_model.preview_image_url,
            attachments=lesson_model.attachments or [],
            created_at=lesson_model.created_at,
            updated_at=lesson_model.updated_at
        ) 