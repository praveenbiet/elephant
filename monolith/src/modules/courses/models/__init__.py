# Import all models for easier access
from src.modules.courses.models.course import CourseModel
from src.modules.courses.models.section import SectionModel
from src.modules.courses.models.lesson import LessonModel
from src.modules.courses.models.enrollment import EnrollmentModel
from src.modules.courses.models.progress import LessonProgressModel

# These imports enable SQLAlchemy to discover all models
__all__ = [
    'CourseModel',
    'SectionModel',
    'LessonModel',
    'EnrollmentModel',
    'LessonProgressModel'
] 