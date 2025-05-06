from typing import List, Optional, Dict, Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import get_logger
from src.modules.courses.domain.section import Section
from src.modules.courses.persistence.section_repository import SectionRepository
from src.modules.courses.persistence.course_repository import CourseRepository
from src.modules.courses.persistence.lesson_repository import LessonRepository

logger = get_logger(__name__)

class SectionService:
    """
    Service for course section-related operations.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.section_repository = SectionRepository(db)
        self.course_repository = CourseRepository(db)
        self.lesson_repository = LessonRepository(db)
    
    async def get_section_by_id(self, section_id: str) -> Optional[Section]:
        """Get a section by ID."""
        return await self.section_repository.get_by_id(section_id)
    
    async def get_sections_by_course_id(self, course_id: str) -> List[Section]:
        """Get all sections for a course."""
        return await self.section_repository.get_sections_by_course_id(course_id)
    
    async def create_section(self, section_data: Dict[str, Any]) -> Optional[Section]:
        """
        Create a new course section.
        
        Args:
            section_data: Dictionary with section data
            
        Returns:
            Created section domain entity or None if creation failed
        """
        try:
            # Verify course exists
            course = await self.course_repository.get_by_id(section_data['course_id'])
            if not course:
                logger.error(f"Course {section_data['course_id']} not found for section creation")
                return None
            
            # Generate ID if not provided
            section_id = section_data.get('id') or str(uuid.uuid4())
            
            # Get position if not provided
            position = section_data.get('position')
            if position is None:
                position = await self.section_repository.get_next_position(section_data['course_id'])
            
            # Create section domain entity
            section = Section(
                id=section_id,
                course_id=section_data['course_id'],
                title=section_data['title'],
                position=position,
                description=section_data.get('description'),
                is_free_preview=section_data.get('is_free_preview', False),
                duration_minutes=section_data.get('duration_minutes')
            )
            
            # Create section in repository
            created_section = await self.section_repository.create(section)
            
            # Update course duration if needed
            await self._update_course_duration(section.course_id)
            
            return created_section
            
        except Exception as e:
            logger.error(f"Error creating section: {str(e)}", exc_info=True)
            return None
    
    async def update_section(self, section_id: str, section_data: Dict[str, Any]) -> Optional[Section]:
        """
        Update an existing section.
        
        Args:
            section_id: ID of the section to update
            section_data: Dictionary with updated section data
            
        Returns:
            Updated section domain entity or None if update failed
        """
        try:
            # Get existing section
            section = await self.section_repository.get_by_id(section_id)
            if not section:
                logger.error(f"Section with ID {section_id} not found for update")
                return None
            
            # Update section attributes
            if 'title' in section_data:
                section.title = section_data['title']
            if 'description' in section_data:
                section.description = section_data['description']
            if 'position' in section_data:
                section.position = section_data['position']
            if 'is_free_preview' in section_data:
                section.is_free_preview = section_data['is_free_preview']
            if 'duration_minutes' in section_data:
                section.duration_minutes = section_data['duration_minutes']
            
            # Update section in repository
            updated_section = await self.section_repository.update(section)
            
            # Update course duration if needed
            await self._update_course_duration(section.course_id)
            
            return updated_section
            
        except Exception as e:
            logger.error(f"Error updating section {section_id}: {str(e)}", exc_info=True)
            return None
    
    async def delete_section(self, section_id: str) -> bool:
        """
        Delete a section.
        
        Args:
            section_id: ID of the section to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get section to know the course_id
            section = await self.section_repository.get_by_id(section_id)
            if not section:
                logger.error(f"Section with ID {section_id} not found for deletion")
                return False
            
            course_id = section.course_id
            
            # Delete the section
            result = await self.section_repository.delete(section_id)
            
            if result:
                # Update course duration
                await self._update_course_duration(course_id)
                
            return result
            
        except Exception as e:
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
            return await self.section_repository.reorder_sections(course_id, section_ids)
            
        except Exception as e:
            logger.error(f"Error reordering sections for course {course_id}: {str(e)}", exc_info=True)
            return False
    
    async def get_section_with_lessons(self, section_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a section with all its lessons.
        
        Args:
            section_id: Section ID
            
        Returns:
            Dictionary with section and lessons
        """
        try:
            # Get section
            section = await self.section_repository.get_by_id(section_id)
            if not section:
                return None
            
            # Get lessons
            lessons = await self.lesson_repository.get_lessons_by_section_id(section_id)
            
            return {
                "section": section,
                "lessons": lessons
            }
            
        except Exception as e:
            logger.error(f"Error getting section with lessons for {section_id}: {str(e)}", exc_info=True)
            return None
    
    async def get_free_preview_sections(self, course_id: str) -> List[Dict[str, Any]]:
        """
        Get all free preview sections for a course with their lessons.
        
        Args:
            course_id: Course ID
            
        Returns:
            List of dictionaries with sections and their lessons
        """
        try:
            # Get free preview sections
            sections = await self.section_repository.get_free_preview_sections(course_id)
            
            # Get lessons for each section
            result = []
            for section in sections:
                free_lessons = await self.lesson_repository.get_free_preview_lessons(section.id)
                result.append({
                    "section": section,
                    "lessons": free_lessons
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting free preview sections for course {course_id}: {str(e)}", exc_info=True)
            return []
    
    async def _update_course_duration(self, course_id: str) -> None:
        """
        Update the course duration based on section durations.
        
        Args:
            course_id: Course ID
        """
        try:
            # Get all sections for the course
            sections = await self.section_repository.get_sections_by_course_id(course_id)
            
            # Calculate total duration from sections
            total_duration = 0
            for section in sections:
                if section.duration_minutes:
                    total_duration += section.duration_minutes
                else:
                    # If section duration is not set, calculate from lessons
                    lessons = await self.lesson_repository.get_lessons_by_section_id(section.id)
                    section_duration = sum(lesson.duration_minutes or 0 for lesson in lessons)
                    
                    # Update section duration
                    if section_duration > 0:
                        section.duration_minutes = section_duration
                        await self.section_repository.update(section)
                        
                    total_duration += section_duration
            
            # Update course duration
            if total_duration > 0:
                course = await self.course_repository.get_by_id(course_id)
                if course and course.duration_minutes != total_duration:
                    course.duration_minutes = total_duration
                    await self.course_repository.update(course)
            
        except Exception as e:
            logger.error(f"Error updating course duration for course {course_id}: {str(e)}", exc_info=True) 