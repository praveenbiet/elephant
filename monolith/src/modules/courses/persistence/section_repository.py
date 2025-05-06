import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, update, delete, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

from src.common.logger import get_logger
from src.modules.courses.domain.section import Section
from src.modules.courses.models.course import SectionModel

logger = get_logger(__name__)

class SectionRepository:
    """
    Repository for course section-related database operations.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, section_id: str) -> Optional[Section]:
        """
        Get a section by ID.
        
        Args:
            section_id: Section ID
            
        Returns:
            Section domain entity if found, None otherwise
        """
        try:
            query = select(SectionModel).where(SectionModel.id == section_id)
            result = await self.db.execute(query)
            section_model = result.scalars().first()
            
            if not section_model:
                return None
                
            return self._map_to_domain(section_model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting section by ID {section_id}: {str(e)}", exc_info=True)
            return None
    
    async def get_sections_by_course_id(self, course_id: str) -> List[Section]:
        """
        Get all sections for a course.
        
        Args:
            course_id: Course ID
            
        Returns:
            List of section domain entities sorted by position
        """
        try:
            query = select(SectionModel).where(
                SectionModel.course_id == course_id
            ).order_by(
                SectionModel.position
            )
            
            result = await self.db.execute(query)
            section_models = result.scalars().all()
            
            return [self._map_to_domain(model) for model in section_models]
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting sections for course {course_id}: {str(e)}", exc_info=True)
            return []
    
    async def create(self, section: Section) -> Optional[Section]:
        """
        Create a new section.
        
        Args:
            section: Section domain entity
            
        Returns:
            Created section domain entity with ID, or None if creation failed
        """
        try:
            # Generate ID if not provided
            if not section.id:
                section.id = str(uuid.uuid4())
            
            # Create model from domain entity
            section_model = SectionModel(
                id=section.id,
                course_id=section.course_id,
                title=section.title,
                description=section.description,
                position=section.position,
                is_free_preview=section.is_free_preview,
                duration_minutes=section.duration_minutes,
                created_at=section.created_at or datetime.utcnow(),
                updated_at=section.updated_at or datetime.utcnow()
            )
            
            self.db.add(section_model)
            await self.db.commit()
            await self.db.refresh(section_model)
            
            # Return domain entity with updated data
            return self._map_to_domain(section_model)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error creating section {section.title}: {str(e)}", exc_info=True)
            return None
    
    async def update(self, section: Section) -> Optional[Section]:
        """
        Update an existing section.
        
        Args:
            section: Section domain entity with updated values
            
        Returns:
            Updated section domain entity, or None if update failed
        """
        try:
            # Check if section exists
            existing_section = await self.get_by_id(section.id)
            if not existing_section:
                logger.error(f"Section with ID {section.id} not found for update")
                return None
            
            # Update the section
            query = update(SectionModel).where(SectionModel.id == section.id).values(
                title=section.title,
                description=section.description,
                position=section.position,
                is_free_preview=section.is_free_preview,
                duration_minutes=section.duration_minutes,
                updated_at=datetime.utcnow()
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            # Get the updated section
            return await self.get_by_id(section.id)
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error updating section {section.id}: {str(e)}", exc_info=True)
            return None
    
    async def delete(self, section_id: str) -> bool:
        """
        Delete a section.
        
        Args:
            section_id: ID of the section to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = delete(SectionModel).where(SectionModel.id == section_id)
            result = await self.db.execute(query)
            await self.db.commit()
            
            return result.rowcount > 0
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error deleting section {section_id}: {str(e)}", exc_info=True)
            return False
    
    async def reorder_sections(self, course_id: str, section_ids: List[str]) -> bool:
        """
        Reorder sections within a course.
        
        Args:
            course_id: Course ID
            section_ids: List of section IDs in the desired order
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Verify all sections belong to the course
            query = select(func.count(SectionModel.id)).where(
                SectionModel.course_id == course_id,
                SectionModel.id.in_(section_ids)
            )
            result = await self.db.execute(query)
            count = result.scalar()
            
            if count != len(section_ids):
                logger.error(f"Not all sections belong to course {course_id}")
                return False
            
            # Update positions
            for position, section_id in enumerate(section_ids, 1):
                await self.db.execute(
                    update(SectionModel).where(
                        SectionModel.id == section_id
                    ).values(
                        position=position,
                        updated_at=datetime.utcnow()
                    )
                )
            
            await self.db.commit()
            return True
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error reordering sections for course {course_id}: {str(e)}", exc_info=True)
            return False
    
    async def get_free_preview_sections(self, course_id: str) -> List[Section]:
        """
        Get all free preview sections for a course.
        
        Args:
            course_id: Course ID
            
        Returns:
            List of section domain entities that are marked as free preview
        """
        try:
            query = select(SectionModel).where(
                SectionModel.course_id == course_id,
                SectionModel.is_free_preview == True
            ).order_by(
                SectionModel.position
            )
            
            result = await self.db.execute(query)
            section_models = result.scalars().all()
            
            return [self._map_to_domain(model) for model in section_models]
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting free preview sections for course {course_id}: {str(e)}", exc_info=True)
            return []
    
    async def get_next_position(self, course_id: str) -> int:
        """
        Get the next available position for a new section in a course.
        
        Args:
            course_id: Course ID
            
        Returns:
            Next position (1 if no sections exist)
        """
        try:
            query = select(func.max(SectionModel.position)).where(
                SectionModel.course_id == course_id
            )
            
            result = await self.db.execute(query)
            max_position = result.scalar() or 0
            
            return max_position + 1
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting next position for course {course_id}: {str(e)}", exc_info=True)
            return 1
    
    def _map_to_domain(self, section_model: SectionModel) -> Section:
        """
        Map database model to domain entity.
        
        Args:
            section_model: Database model
            
        Returns:
            Domain entity
        """
        return Section(
            id=section_model.id,
            course_id=section_model.course_id,
            title=section_model.title,
            description=section_model.description,
            position=section_model.position,
            is_free_preview=section_model.is_free_preview,
            duration_minutes=section_model.duration_minutes,
            created_at=section_model.created_at,
            updated_at=section_model.updated_at
        ) 