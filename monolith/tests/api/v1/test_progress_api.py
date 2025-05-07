import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.routers.progress import router, get_progress_service, get_enrollment_service, get_course_service
from src.modules.courses.domain.progress import LessonProgress, ProgressStatus
from src.modules.courses.services.progress_service import ProgressService
from src.modules.courses.services.enrollment_service import EnrollmentService
from src.modules.courses.services.course_service import CourseService
from src.api.dependencies import get_current_active_user

app = FastAPI()
app.include_router(router)

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_current_user():
    return {"id": "test-user-id", "email": "test@example.com"}

@pytest.fixture
def override_dependencies(mock_current_user):
    """Override dependencies for testing."""
    # Mock progress service
    mock_progress_service = AsyncMock(spec=ProgressService)
    app.dependency_overrides[get_progress_service] = lambda: mock_progress_service
    
    # Mock enrollment service
    mock_enrollment_service = AsyncMock(spec=EnrollmentService)
    app.dependency_overrides[get_enrollment_service] = lambda: mock_enrollment_service
    
    # Mock course service
    mock_course_service = AsyncMock(spec=CourseService)
    app.dependency_overrides[get_course_service] = lambda: mock_course_service
    
    # Mock authentication
    app.dependency_overrides[get_current_active_user] = lambda: mock_current_user
    
    yield {
        "progress_service": mock_progress_service,
        "enrollment_service": mock_enrollment_service,
        "course_service": mock_course_service
    }
    
    # Clean up
    app.dependency_overrides.clear()

@pytest.fixture
def sample_lesson_progress():
    return {
        "id": "test-progress-id",
        "lesson_id": "test-lesson-id",
        "progress_percentage": 45.5,
        "status": "in_progress",
        "last_position_seconds": 325,
        "completed_at": None,
        "last_activity_at": datetime.utcnow().isoformat()
    }

@pytest.fixture
def sample_course_progress():
    return {
        "course": {
            "id": "test-course-id",
            "title": "Test Course",
            "image_url": "https://example.com/test-course.jpg"
        },
        "overall_percentage": 35.0,
        "status_counts": {
            "not_started": 5,
            "in_progress": 3,
            "completed": 2
        },
        "section_progress": [
            {
                "section_id": "test-section-id",
                "title": "Test Section",
                "progress_percentage": 75.0,
                "lessons": [
                    {
                        "lesson_id": "test-lesson-id",
                        "title": "Test Lesson",
                        "type": "video",
                        "status": "completed",
                        "progress_percentage": 100.0,
                        "last_position_seconds": 450
                    }
                ]
            }
        ],
        "enrollment": {
            "status": "active",
            "progress_percentage": 35.0,
            "completed_at": None,
            "certificate_id": None
        }
    }

@pytest.fixture
def sample_learning_stats():
    return {
        "enrolled_courses": 5,
        "completed_courses": 2,
        "active_courses": 3,
        "lessons_accessed": 45,
        "lessons_completed": 32,
        "minutes_watched": 540,
        "last_activity_at": datetime.utcnow().isoformat()
    }

class TestProgressAPI:
    def test_get_lesson_progress(self, client, override_dependencies, sample_lesson_progress):
        # Setup mock
        mock_services = override_dependencies
        mock_services["progress_service"].get_lesson_progress.return_value = sample_lesson_progress
        
        # Make request
        response = client.get("/progress/lesson/test-lesson-id")
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["lesson_id"] == sample_lesson_progress["lesson_id"]
        assert data["progress_percentage"] == sample_lesson_progress["progress_percentage"]
        assert data["status"] == sample_lesson_progress["status"]
        
        # Verify mock called
        mock_services["progress_service"].get_lesson_progress.assert_called_once_with("test-user-id", "test-lesson-id")
    
    def test_update_lesson_progress(self, client, override_dependencies, sample_lesson_progress):
        # Setup mock
        mock_services = override_dependencies
        mock_services["progress_service"].update_lesson_progress.return_value = sample_lesson_progress
        
        # Make request
        progress_data = {
            "progress_percentage": 60.0,
            "position_seconds": 400
        }
        response = client.post("/progress/lesson/test-lesson-id/update", json=progress_data)
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["lesson_id"] == sample_lesson_progress["lesson_id"]
        
        # Verify mock called
        mock_services["progress_service"].update_lesson_progress.assert_called_once_with(
            "test-user-id", "test-lesson-id", 60.0, 400
        )
    
    def test_complete_lesson(self, client, override_dependencies, sample_lesson_progress):
        # Setup mock
        mock_services = override_dependencies
        completed_progress = sample_lesson_progress.copy()
        completed_progress["status"] = "completed"
        completed_progress["progress_percentage"] = 100.0
        completed_progress["completed_at"] = datetime.utcnow().isoformat()
        mock_services["progress_service"].mark_lesson_completed.return_value = completed_progress
        
        # Make request
        response = client.post("/progress/lesson/test-lesson-id/complete")
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["progress_percentage"] == 100.0
        assert data["completed_at"] is not None
        
        # Verify mock called
        mock_services["progress_service"].mark_lesson_completed.assert_called_once_with("test-user-id", "test-lesson-id")
    
    def test_reset_lesson_progress(self, client, override_dependencies, sample_lesson_progress):
        # Setup mock
        mock_services = override_dependencies
        reset_progress = sample_lesson_progress.copy()
        reset_progress["status"] = "in_progress"
        reset_progress["progress_percentage"] = 0.0
        reset_progress["last_position_seconds"] = 0
        reset_progress["completed_at"] = None
        mock_services["progress_service"].reset_lesson_progress.return_value = reset_progress
        
        # Make request
        response = client.post("/progress/lesson/test-lesson-id/reset")
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
        assert data["progress_percentage"] == 0.0
        assert data["last_position_seconds"] == 0
        
        # Verify mock called
        mock_services["progress_service"].reset_lesson_progress.assert_called_once_with("test-user-id", "test-lesson-id")
    
    def test_get_course_progress(self, client, override_dependencies, sample_course_progress):
        # Setup mocks
        mock_services = override_dependencies
        mock_services["enrollment_service"].check_user_enrollment.return_value = {"is_enrolled": True}
        mock_services["course_service"].get_course_by_id.return_value = {
            "id": "test-course-id",
            "title": "Test Course",
            "image_url": "https://example.com/test-course.jpg"
        }
        mock_services["progress_service"].get_course_progress.return_value = sample_course_progress
        
        # Make request
        response = client.get("/progress/course/test-course-id")
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["overall_percentage"] == 35.0
        assert len(data["section_progress"]) == 1
        assert data["section_progress"][0]["title"] == "Test Section"
        
        # Verify mocks called
        mock_services["enrollment_service"].check_user_enrollment.assert_called_once_with("test-user-id", "test-course-id")
        mock_services["course_service"].get_course_by_id.assert_called_once_with("test-course-id")
        mock_services["progress_service"].get_course_progress.assert_called_once_with("test-user-id", "test-course-id")
    
    def test_get_recent_activity(self, client, override_dependencies):
        # Setup mock
        mock_services = override_dependencies
        mock_activities = [
            {
                "progress_id": "test-progress-id",
                "lesson_id": "test-lesson-id",
                "lesson_title": "Test Lesson",
                "lesson_type": "video",
                "section_id": "test-section-id",
                "section_title": "Test Section",
                "course_id": "test-course-id",
                "course_title": "Test Course",
                "status": "in_progress",
                "progress_percentage": 45.5,
                "last_position_seconds": 325,
                "last_activity_at": datetime.utcnow().isoformat()
            }
        ]
        mock_services["progress_service"].get_recent_activity.return_value = mock_activities
        
        # Make request
        response = client.get("/progress/recent-activity?limit=10&days=7")
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert "activities" in data
        assert len(data["activities"]) == 1
        
        # Verify mock called
        mock_services["progress_service"].get_recent_activity.assert_called_once_with("test-user-id", 10, 7)
    
    def test_get_learning_stats(self, client, override_dependencies, sample_learning_stats):
        # Setup mock
        mock_services = override_dependencies
        mock_services["progress_service"].get_learning_stats.return_value = sample_learning_stats
        
        # Make request
        response = client.get("/progress/learning-stats")
        
        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["enrolled_courses"] == 5
        assert data["completed_courses"] == 2
        assert data["active_courses"] == 3
        assert data["lessons_accessed"] == 45
        assert data["lessons_completed"] == 32
        assert data["minutes_watched"] == 540
        
        # Verify mock called
        mock_services["progress_service"].get_learning_stats.assert_called_once_with("test-user-id") 