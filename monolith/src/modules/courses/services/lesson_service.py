from typing import List, Optional, Dict, Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import get_logger
from src.modules.courses.domain.lesson import Lesson, LessonType
from src.modules.courses.persistence.lesson_repository import LessonRepository
from src.modules.courses.persistence.section_repository import SectionRepository

logger = get_logger(__name__)

class LessonService:
    """
    Service for lesson-related operations.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.lesson_repository = LessonRepository(db)
        self.section_repository = SectionRepository(db)
    
    async def get_lesson_by_id(self, lesson_id: str) -> Optional[Lesson]:
        """Get a lesson by ID."""
        return await self.lesson_repository.get_by_id(lesson_id)
    
    async def get_lessons_by_section_id(self, section_id: str) -> List[Lesson]:
        """Get all lessons for a section."""
        return await self.lesson_repository.get_lessons_by_section_id(section_id)
    
    async def create_lesson(self, lesson_data: Dict[str, Any]) -> Optional[Lesson]:
        """
        Create a new lesson.
        
        Args:
            lesson_data: Dictionary with lesson data
            
        Returns:
            Created lesson domain entity or None if creation failed
        """
        try:
            # Verify section exists
            section = await self.section_repository.get_by_id(lesson_data['section_id'])
            if not section:
                logger.error(f"Section {lesson_data['section_id']} not found for lesson creation")
                return None
            
            # Generate ID if not provided
            lesson_id = lesson_data.get('id') or str(uuid.uuid4())
            
            # Get position if not provided
            position = lesson_data.get('position')
            if position is None:
                position = await self.lesson_repository.get_next_position(lesson_data['section_id'])
            
            # Ensure lesson type is valid
            lesson_type = lesson_data.get('type')
            if isinstance(lesson_type, str):
                try:
                    lesson_type = LessonType(lesson_type)
                except ValueError:
                    lesson_type = LessonType.OTHER
            elif lesson_type is None:
                lesson_type = LessonType.VIDEO
            
            # Create lesson domain entity
            lesson = Lesson(
                id=lesson_id,
                section_id=lesson_data['section_id'],
                title=lesson_data['title'],
                type=lesson_type,
                position=position,
                content_id=lesson_data.get('content_id'),
                description=lesson_data.get('description'),
                duration_minutes=lesson_data.get('duration_minutes'),
                is_free_preview=lesson_data.get('is_free_preview', False),
                is_downloadable=lesson_data.get('is_downloadable', False),
                preview_image_url=lesson_data.get('preview_image_url'),
                attachments=lesson_data.get('attachments', [])
            )
            
            # Create lesson in repository
            created_lesson = await self.lesson_repository.create(lesson)
            
            # Update section and course duration if needed
            if created_lesson and created_lesson.duration_minutes:
                # Update section duration
                await self._update_section_duration(section.id)
            
            return created_lesson
            
        except Exception as e:
            logger.error(f"Error creating lesson: {str(e)}", exc_info=True)
            return None
    
    async def update_lesson(self, lesson_id: str, lesson_data: Dict[str, Any]) -> Optional[Lesson]:
        """
        Update an existing lesson.
        
        Args:
            lesson_id: ID of the lesson to update
            lesson_data: Dictionary with updated lesson data
            
        Returns:
            Updated lesson domain entity or None if update failed
        """
        try:
            # Get existing lesson
            lesson = await self.lesson_repository.get_by_id(lesson_id)
            if not lesson:
                logger.error(f"Lesson with ID {lesson_id} not found for update")
                return None
            
            # Store original section ID and duration for later updates
            original_section_id = lesson.section_id
            original_duration = lesson.duration_minutes
            
            # Update lesson attributes
            if 'title' in lesson_data:
                lesson.title = lesson_data['title']
            if 'description' in lesson_data:
                lesson.description = lesson_data['description']
            if 'position' in lesson_data:
                lesson.position = lesson_data['position']
            if 'type' in lesson_data:
                lesson_type = lesson_data['type']
                if isinstance(lesson_type, str):
                    try:
                        lesson.type = LessonType(lesson_type)
                    except ValueError:
                        lesson.type = LessonType.OTHER
                else:
                    lesson.type = lesson_type
            if 'content_id' in lesson_data:
                lesson.content_id = lesson_data['content_id']
            if 'duration_minutes' in lesson_data:
                lesson.duration_minutes = lesson_data['duration_minutes']
            if 'is_free_preview' in lesson_data:
                lesson.is_free_preview = lesson_data['is_free_preview']
            if 'is_downloadable' in lesson_data:
                lesson.is_downloadable = lesson_data['is_downloadable']
            if 'preview_image_url' in lesson_data:
                lesson.preview_image_url = lesson_data['preview_image_url']
            if 'attachments' in lesson_data:
                lesson.attachments = lesson_data['attachments']
            if 'section_id' in lesson_data:
                # Verify new section exists
                new_section = await self.section_repository.get_by_id(lesson_data['section_id'])
                if not new_section:
                    logger.error(f"New section {lesson_data['section_id']} not found for lesson update")
                    return None
                lesson.section_id = lesson_data['section_id']
            
            # Update lesson in repository
            updated_lesson = await self.lesson_repository.update(lesson)
            
            # Update section duration if needed
            if updated_lesson:
                if original_section_id != updated_lesson.section_id:
                    # If section changed, update both sections
                    await self._update_section_duration(original_section_id)
                    await self._update_section_duration(updated_lesson.section_id)
                elif original_duration != updated_lesson.duration_minutes:
                    # If only duration changed, update current section
                    await self._update_section_duration(updated_lesson.section_id)
            
            return updated_lesson
            
        except Exception as e:
            logger.error(f"Error updating lesson {lesson_id}: {str(e)}", exc_info=True)
            return None
    
    async def delete_lesson(self, lesson_id: str) -> bool:
        """
        Delete a lesson.
        
        Args:
            lesson_id: ID of the lesson to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get lesson to know the section_id
            lesson = await self.lesson_repository.get_by_id(lesson_id)
            if not lesson:
                logger.error(f"Lesson with ID {lesson_id} not found for deletion")
                return False
            
            section_id = lesson.section_id
            
            # Delete the lesson
            result = await self.lesson_repository.delete(lesson_id)
            
            if result:
                # Update section duration
                await self._update_section_duration(section_id)
                
            return result
            
        except Exception as e:
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
            return await self.lesson_repository.reorder_lessons(section_id, lesson_ids)
            
        except Exception as e:
            logger.error(f"Error reordering lessons for section {section_id}: {str(e)}", exc_info=True)
            return False
    
    async def get_lessons_by_type(self, section_id: str, lesson_type: LessonType) -> List[Lesson]:
        """
        Get all lessons of a specific type in a section.
        
        Args:
            section_id: Section ID
            lesson_type: Type of lessons to retrieve
            
        Returns:
            List of lesson domain entities of the specified type
        """
        try:
            return await self.lesson_repository.get_lessons_by_type(section_id, lesson_type)
            
        except Exception as e:
            logger.error(f"Error getting lessons of type {lesson_type} for section {section_id}: {str(e)}", exc_info=True)
            return []
    
    async def _update_section_duration(self, section_id: str) -> None:
        """
        Update the section duration based on lesson durations.
        
        Args:
            section_id: Section ID
        """
        try:
            # Get all lessons for the section
            lessons = await self.lesson_repository.get_lessons_by_section_id(section_id)
            
            # Calculate total duration
            total_duration = sum(lesson.duration_minutes or 0 for lesson in lessons)
            
            # Update section
            section = await self.section_repository.get_by_id(section_id)
            if section and section.duration_minutes != total_duration:
                section.duration_minutes = total_duration
                await self.section_repository.update(section)
                
                # Update course duration
                from src.modules.courses.services.section_service import SectionService
                section_service = SectionService(self.db)
                await section_service._update_course_duration(section.course_id)
                
        except Exception as e:
            logger.error(f"Error updating section duration for section {section_id}: {str(e)}", exc_info=True) 