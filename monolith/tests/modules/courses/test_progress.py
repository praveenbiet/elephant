import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

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
    service = ProgressService(mock_db)
    service.progress_repo = AsyncMock(spec=ProgressRepository)
    service.lesson_repo = AsyncMock()
    service.section_repo = AsyncMock()
    service.course_repo = AsyncMock()
    service.enrollment_repo = AsyncMock()
    return service

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

@pytest.fixture
def sample_lesson():
    return MagicMock(
        id="test-lesson-id",
        title="Test Lesson",
        type="video",
        section_id="test-section-id"
    )

@pytest.fixture
def sample_section():
    return MagicMock(
        id="test-section-id",
        title="Test Section",
        course_id="test-course-id"
    )

@pytest.fixture
def sample_course():
    return MagicMock(
        id="test-course-id",
        title="Test Course",
        image_url="https://example.com/test-course.jpg"
    )

class TestProgressRepository:
    @pytest.mark.asyncio
    async def test_get_by_id(self, progress_repository, sample_lesson_progress):
        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = MagicMock(
            id=sample_lesson_progress.id,
            user_id=sample_lesson_progress.user_id,
            lesson_id=sample_lesson_progress.lesson_id,
            status=sample_lesson_progress.status,
            progress_percentage=sample_lesson_progress.progress_percentage,
            last_position_seconds=sample_lesson_progress.last_position_seconds,
            completed_at=sample_lesson_progress.completed_at,
            last_activity_at=sample_lesson_progress.last_activity_at,
            created_at=sample_lesson_progress.created_at,
            updated_at=sample_lesson_progress.updated_at
        )
        progress_repository.db.execute.return_value = mock_result

        # Test the method
        result = await progress_repository.get_by_id("test-progress-id")
        
        assert result is not None
        assert result.id == sample_lesson_progress.id
        assert result.user_id == sample_lesson_progress.user_id
        assert result.lesson_id == sample_lesson_progress.lesson_id

    @pytest.mark.asyncio
    async def test_get_by_user_and_lesson(self, progress_repository, sample_lesson_progress):
        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = MagicMock(
            id=sample_lesson_progress.id,
            user_id=sample_lesson_progress.user_id,
            lesson_id=sample_lesson_progress.lesson_id,
            status=sample_lesson_progress.status,
            progress_percentage=sample_lesson_progress.progress_percentage,
            last_position_seconds=sample_lesson_progress.last_position_seconds,
            completed_at=sample_lesson_progress.completed_at,
            last_activity_at=sample_lesson_progress.last_activity_at,
            created_at=sample_lesson_progress.created_at,
            updated_at=sample_lesson_progress.updated_at
        )
        progress_repository.db.execute.return_value = mock_result

        # Test the method
        result = await progress_repository.get_by_user_and_lesson("test-user-id", "test-lesson-id")
        
        assert result is not None
        assert result.id == sample_lesson_progress.id
        assert result.user_id == sample_lesson_progress.user_id
        assert result.lesson_id == sample_lesson_progress.lesson_id

    @pytest.mark.asyncio
    async def test_create_progress(self, progress_repository, sample_lesson_progress):
        # Mock the database operations
        progress_repository.db.commit = AsyncMock()
        progress_repository.db.refresh = AsyncMock()
        progress_repository.get_by_user_and_lesson = AsyncMock(return_value=None)

        # Create model mock
        mock_model = MagicMock(
            id=sample_lesson_progress.id,
            user_id=sample_lesson_progress.user_id,
            lesson_id=sample_lesson_progress.lesson_id,
            status=sample_lesson_progress.status,
            progress_percentage=sample_lesson_progress.progress_percentage,
            last_position_seconds=sample_lesson_progress.last_position_seconds,
            completed_at=sample_lesson_progress.completed_at,
            last_activity_at=sample_lesson_progress.last_activity_at,
            created_at=sample_lesson_progress.created_at,
            updated_at=sample_lesson_progress.updated_at
        )
        
        # Test the method
        with patch.object(progress_repository, '_map_to_domain', return_value=sample_lesson_progress):
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
        with patch.object(progress_repository, '_map_to_domain', return_value=sample_lesson_progress):
            result = await progress_repository.update(sample_lesson_progress)
        
        assert result is not None
        progress_repository.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_lesson_progress(self, progress_repository, sample_lesson_progress):
        # Mock the repository methods
        progress_repository.get_by_user_and_lesson = AsyncMock(return_value=sample_lesson_progress)
        progress_repository.update = AsyncMock(return_value=sample_lesson_progress)
        
        # Test the method with existing progress
        result = await progress_repository.update_lesson_progress(
            "test-user-id", "test-lesson-id", 60.0, 400
        )
        
        assert result is not None
        assert isinstance(result, LessonProgress)
        progress_repository.update.assert_called_once()
        
        # Test with new progress
        progress_repository.get_by_user_and_lesson = AsyncMock(return_value=None)
        progress_repository.create = AsyncMock(return_value=sample_lesson_progress)
        
        result = await progress_repository.update_lesson_progress(
            "test-user-id", "test-lesson-id", 30.0, 200
        )
        
        assert result is not None
        progress_repository.create.assert_called_once()

class TestProgressService:
    @pytest.mark.asyncio
    async def test_get_lesson_progress(self, progress_service, sample_lesson_progress):
        # Mock the repository method
        progress_service.progress_repo.get_by_user_and_lesson = AsyncMock(
            return_value=sample_lesson_progress
        )

        # Test the method
        result = await progress_service.get_lesson_progress("test-user-id", "test-lesson-id")
        
        assert result is not None
        assert result["lesson_id"] == sample_lesson_progress.lesson_id
        assert result["progress_percentage"] == sample_lesson_progress.progress_percentage
        assert result["status"] == sample_lesson_progress.status.value

        # Test with no existing progress
        progress_service.progress_repo.get_by_user_and_lesson = AsyncMock(return_value=None)
        progress_service.progress_repo.create = AsyncMock(return_value=sample_lesson_progress)
        
        result = await progress_service.get_lesson_progress("test-user-id", "test-lesson-id")
        
        assert result is not None
        assert result["lesson_id"] == sample_lesson_progress.lesson_id
        progress_service.progress_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_lesson_progress(self, progress_service, sample_lesson_progress):
        # Mock the repository method
        progress_service.progress_repo.update_lesson_progress = AsyncMock(
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
        assert result["progress_percentage"] == 45.5
        assert result["last_position_seconds"] == 325

    @pytest.mark.asyncio
    async def test_mark_lesson_completed(self, progress_service, sample_lesson_progress):
        # Mock the repository methods
        progress_service.progress_repo.get_by_user_and_lesson = AsyncMock(
            return_value=sample_lesson_progress
        )
        
        completed_progress = LessonProgress(
            id=sample_lesson_progress.id,
            user_id=sample_lesson_progress.user_id,
            lesson_id=sample_lesson_progress.lesson_id,
            status=ProgressStatus.COMPLETED,
            progress_percentage=100.0,
            last_position_seconds=sample_lesson_progress.last_position_seconds,
            completed_at=datetime.utcnow(),
            last_activity_at=datetime.utcnow(),
            created_at=sample_lesson_progress.created_at,
            updated_at=datetime.utcnow()
        )
        
        progress_service.progress_repo.update = AsyncMock(
            return_value=completed_progress
        )

        # Test the method
        result = await progress_service.mark_lesson_completed("test-user-id", "test-lesson-id")
        
        assert result is not None
        assert result["status"] == ProgressStatus.COMPLETED.value
        assert result["progress_percentage"] == 100.0
        assert result["completed_at"] is not None
    
    @pytest.mark.asyncio
    async def test_get_course_progress(self, progress_service, sample_course, sample_section, sample_lesson, sample_lesson_progress):
        # Mock the repository methods
        progress_service.course_repo.get_by_id = AsyncMock(return_value=sample_course)
        progress_service.progress_repo.calculate_course_progress = AsyncMock(
            return_value=(35.0, {"not_started": 5, "in_progress": 3, "completed": 2})
        )
        progress_service.section_repo.get_by_course = AsyncMock(
            return_value=[sample_section]
        )
        progress_service.lesson_repo.get_by_section = AsyncMock(
            return_value=[sample_lesson]
        )
        progress_service.progress_repo.get_by_user_and_lesson = AsyncMock(
            return_value=sample_lesson_progress
        )
        progress_service.course_repo.get_enrollment = AsyncMock(
            return_value=MagicMock(
                status="active",
                progress_percentage=35.0,
                completed_at=None,
                certificate_id=None
            )
        )

        # Test the method
        result = await progress_service.get_course_progress("test-user-id", "test-course-id")
        
        assert result is not None
        assert "overall_percentage" in result
        assert "status_counts" in result
        assert "section_progress" in result
        assert len(result["section_progress"]) == 1
        assert result["overall_percentage"] == 35.0
        assert result["status_counts"] == {"not_started": 5, "in_progress": 3, "completed": 2}
        
    @pytest.mark.asyncio
    async def test_get_learning_stats(self, progress_service, mock_db):
        # Mock the database query results
        mock_db.execute = AsyncMock()
        mock_db.execute.side_effect = [
            MagicMock(scalar=lambda: 5),  # enrolled_courses
            MagicMock(scalar=lambda: 2),  # completed_courses
            MagicMock(scalar=lambda: 45),  # lessons_accessed
            MagicMock(scalar=lambda: 32),  # lessons_completed
            MagicMock(scalar=lambda: 540 * 60),  # minutes_watched in seconds
            MagicMock(scalar=lambda: datetime.utcnow())  # last_activity
        ]
        
        # Test the method
        result = await progress_service.get_learning_stats("test-user-id")
        
        assert result is not None
        assert result["enrolled_courses"] == 5
        assert result["completed_courses"] == 2
        assert result["active_courses"] == 3
        assert result["lessons_accessed"] == 45
        assert result["lessons_completed"] == 32
        assert result["minutes_watched"] == 540
        assert result["last_activity_at"] is not None 