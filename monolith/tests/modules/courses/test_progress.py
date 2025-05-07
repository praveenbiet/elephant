import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.modules.courses.domain.progress import LessonProgress, ProgressStatus
from src.modules.courses.services.progress_service import ProgressService
from src.modules.courses.persistence.progress_repository import ProgressRepository

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def progress_repository(mock_db):
    return ProgressRepository(mock_db)

@pytest.fixture
def progress_service(mock_db):
    return ProgressService(mock_db)

@pytest.fixture
def sample_lesson_progress():
    return LessonProgress(
        id="test-progress-id",
        user_id="test-user-id",
        lesson_id="test-lesson-id",
        status=ProgressStatus.IN_PROGRESS,
        progress_percentage=45.5,
        last_position_seconds=325,
        completed_at=None,
        last_activity_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

class TestProgressRepository:
    @pytest.mark.asyncio
    async def test_get_by_id(self, progress_repository, sample_lesson_progress):
        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = sample_lesson_progress
        progress_repository.db.execute.return_value = mock_result

        # Test the method
        result = await progress_repository.get_by_id("test-progress-id")
        
        assert result is not None
        assert result.id == sample_lesson_progress.id
        assert result.user_id == sample_lesson_progress.user_id
        assert result.lesson_id == sample_lesson_progress.lesson_id

    @pytest.mark.asyncio
    async def test_create_progress(self, progress_repository, sample_lesson_progress):
        # Mock the database operations
        progress_repository.db.commit = AsyncMock()
        progress_repository.db.refresh = AsyncMock()

        # Test the method
        result = await progress_repository.create(sample_lesson_progress)
        
        assert result is not None
        assert result.id == sample_lesson_progress.id
        progress_repository.db.add.assert_called_once()
        progress_repository.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_progress(self, progress_repository, sample_lesson_progress):
        # Mock the database operations
        progress_repository.db.commit = AsyncMock()
        progress_repository.get_by_id = AsyncMock(return_value=sample_lesson_progress)

        # Test the method
        result = await progress_repository.update(sample_lesson_progress)
        
        assert result is not None
        progress_repository.db.commit.assert_called_once()

class TestProgressService:
    @pytest.mark.asyncio
    async def test_get_lesson_progress(self, progress_service, sample_lesson_progress):
        # Mock the repository method
        progress_service.progress_repository.get_by_user_and_lesson = AsyncMock(
            return_value=sample_lesson_progress
        )

        # Test the method
        result = await progress_service.get_lesson_progress("test-user-id", "test-lesson-id")
        
        assert result is not None
        assert result.id == sample_lesson_progress.id
        assert result.progress_percentage == sample_lesson_progress.progress_percentage

    @pytest.mark.asyncio
    async def test_update_lesson_progress(self, progress_service, sample_lesson_progress):
        # Mock the repository method
        progress_service.progress_repository.update_lesson_progress = AsyncMock(
            return_value=sample_lesson_progress
        )

        # Test the method
        result = await progress_service.update_lesson_progress(
            "test-user-id",
            "test-lesson-id",
            45.5,
            325
        )
        
        assert result is not None
        assert result.progress_percentage == 45.5
        assert result.last_position_seconds == 325

    @pytest.mark.asyncio
    async def test_mark_lesson_completed(self, progress_service, sample_lesson_progress):
        # Mock the repository methods
        progress_service.progress_repository.get_by_user_and_lesson = AsyncMock(
            return_value=sample_lesson_progress
        )
        progress_service.progress_repository.update = AsyncMock(
            return_value=sample_lesson_progress
        )

        # Test the method
        result = await progress_service.mark_lesson_completed("test-user-id", "test-lesson-id")
        
        assert result is not None
        assert result.status == ProgressStatus.COMPLETED
        assert result.progress_percentage == 100.0

    @pytest.mark.asyncio
    async def test_get_course_progress(self, progress_service):
        # Mock the repository methods
        progress_service.progress_repository.calculate_course_progress = AsyncMock(
            return_value=(35.0, {"not_started": 5, "in_progress": 3, "completed": 2})
        )
        progress_service.section_repository.get_sections_by_course_id = AsyncMock(
            return_value=[MagicMock(id="test-section-id")]
        )
        progress_service.lesson_repository.get_lessons_by_section_id = AsyncMock(
            return_value=[MagicMock(id="test-lesson-id")]
        )

        # Test the method
        result = await progress_service.get_course_progress("test-user-id", "test-course-id")
        
        assert result is not None
        assert "overall_percentage" in result
        assert "status_counts" in result
        assert "section_progress" in result

    @pytest.mark.asyncio
    async def test_get_learning_stats(self, progress_service):
        # Mock the database query
        mock_result = MagicMock()
        mock_result.mappings().first.return_value = {
            "enrolled_courses": 5,
            "completed_courses": 2,
            "active_courses": 3,
            "lessons_accessed": 45,
            "lessons_completed": 32,
            "minutes_watched": 540
        }
        progress_service.db.execute.return_value = mock_result

        # Test the method
        result = await progress_service.get_learning_stats("test-user-id")
        
        assert result is not None
        assert result["enrolled_courses"] == 5
        assert result["completed_courses"] == 2
        assert result["active_courses"] == 3
        assert result["lessons_accessed"] == 45
        assert result["lessons_completed"] == 32
        assert result["minutes_watched"] == 540 