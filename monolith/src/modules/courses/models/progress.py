from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from src.common.database import Base
from src.modules.courses.domain.progress import ProgressStatus

class LessonProgressModel(Base):
    """
    Database model for tracking lesson progress.
    """
    __tablename__ = "lesson_progress"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    lesson_id = Column(String(36), ForeignKey("course_lessons.id"), nullable=False, index=True)
    status = Column(Enum(ProgressStatus), nullable=False, default=ProgressStatus.NOT_STARTED)
    progress_percentage = Column(Float, nullable=False, default=0.0)
    last_position_seconds = Column(Integer, nullable=False, default=0)
    completed_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lesson = relationship("LessonModel", back_populates="progress_records")

    def __repr__(self):
        return f"<LessonProgress(id={self.id}, user_id={self.user_id}, lesson_id={self.lesson_id}, status={self.status})>" 