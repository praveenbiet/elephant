import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.modules.courses.domain.progress import ProgressStatus
from src.modules.courses.services.progress_service import ProgressService

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_progress_service():
    return AsyncMock(spec=ProgressService)

@pytest.fixture
def mock_current_user():
    return {
        "id": "test-user-id",
        "email": "test@example.com",
        "is_active": True
    }

@pytest.fixture
def sample_lesson_progress():
    return {
        "id": "test-progress-id",
        "user_id": "test-user-id",
        "lesson_id": "test-lesson-id",
        "status": ProgressStatus.IN_PROGRESS,
        "progress_percentage": 45.5,
        "last_position_seconds": 325,
        "completed_at": None,
        "last_activity_at": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }

class TestProgressAPI:
    def test_get_lesson_progress(self, client, mock_progress_service, mock_current_user, sample_lesson_progress):
        # Mock the service method
        mock_progress_service.get_lesson_progress.return_value = sample_lesson_progress

        # Make the request
        response = client.get(
            "/api/v1/progress/lesson/test-lesson-id",
            headers={"Authorization": f"Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["lesson_id"] == sample_lesson_progress["lesson_id"]
        assert data["progress_percentage"] == sample_lesson_progress["progress_percentage"]
        assert data["status"] == sample_lesson_progress["status"]

    def test_update_lesson_progress(self, client, mock_progress_service, mock_current_user, sample_lesson_progress):
        # Mock the service method
        mock_progress_service.update_lesson_progress.return_value = sample_lesson_progress

        # Make the request
        response = client.post(
            "/api/v1/progress/lesson/test-lesson-id/update",
            headers={"Authorization": f"Bearer test-token"},
            json={
                "progress_percentage": 45.5,
                "position_seconds": 325
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["lesson_id"] == sample_lesson_progress["lesson_id"]
        assert data["progress_percentage"] == sample_lesson_progress["progress_percentage"]

    def test_complete_lesson(self, client, mock_progress_service, mock_current_user, sample_lesson_progress):
        # Mock the service method
        completed_progress = sample_lesson_progress.copy()
        completed_progress["status"] = ProgressStatus.COMPLETED
        completed_progress["progress_percentage"] = 100.0
        mock_progress_service.mark_lesson_completed.return_value = completed_progress

        # Make the request
        response = client.post(
            "/api/v1/progress/lesson/test-lesson-id/complete",
            headers={"Authorization": f"Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ProgressStatus.COMPLETED
        assert data["progress_percentage"] == 100.0

    def test_get_course_progress(self, client, mock_progress_service, mock_current_user):
        # Mock the service method
        mock_progress_service.get_course_progress.return_value = {
            "overall_percentage": 35.0,
            "status_counts": {
                "not_started": 5,
                "in_progress": 3,
                "completed": 2
            },
            "section_progress": [
                {
                    "section": {
                        "id": "test-section-id",
                        "title": "Test Section"
                    },
                    "progress_percentage": 75.0,
                    "lessons": [
                        {
                            "lesson": {
                                "id": "test-lesson-id",
                                "title": "Test Lesson",
                                "type": "video"
                            },
                            "progress": {
                                "status": ProgressStatus.COMPLETED,
                                "progress_percentage": 100.0,
                                "last_position_seconds": 450
                            }
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

        # Make the request
        response = client.get(
            "/api/v1/progress/course/test-course-id",
            headers={"Authorization": f"Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "overall_percentage" in data
        assert "status_counts" in data
        assert "section_progress" in data
        assert len(data["section_progress"]) > 0

    def test_get_recent_activity(self, client, mock_progress_service, mock_current_user):
        # Mock the service method
        mock_progress_service.get_recent_activity.return_value = [
            {
                "progress_id": "test-progress-id",
                "lesson_id": "test-lesson-id",
                "lesson_title": "Test Lesson",
                "lesson_type": "video",
                "section_id": "test-section-id",
                "section_title": "Test Section",
                "course_id": "test-course-id",
                "course_title": "Test Course",
                "status": ProgressStatus.IN_PROGRESS,
                "progress_percentage": 45.5,
                "last_position_seconds": 325,
                "last_activity_at": datetime.utcnow().isoformat()
            }
        ]

        # Make the request
        response = client.get(
            "/api/v1/progress/recent-activity",
            headers={"Authorization": f"Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "activities" in data
        assert len(data["activities"]) > 0

    def test_get_learning_stats(self, client, mock_progress_service, mock_current_user):
        # Mock the service method
        mock_progress_service.get_learning_stats.return_value = {
            "enrolled_courses": 5,
            "completed_courses": 2,
            "active_courses": 3,
            "lessons_accessed": 45,
            "lessons_completed": 32,
            "minutes_watched": 540,
            "last_activity_at": datetime.utcnow().isoformat()
        }

        # Make the request
        response = client.get(
            "/api/v1/progress/learning-stats",
            headers={"Authorization": f"Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enrolled_courses"] == 5
        assert data["completed_courses"] == 2
        assert data["active_courses"] == 3
        assert data["lessons_accessed"] == 45
        assert data["lessons_completed"] == 32
        assert data["minutes_watched"] == 540 