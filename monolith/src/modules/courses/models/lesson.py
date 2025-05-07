from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship

from src.common.database import Base
from src.modules.courses.domain.lesson import LessonType

class LessonModel(Base):
    """
    Database model for course lessons.
    """
    __tablename__ = "course_lessons"
    
    id = Column(String(36), primary_key=True)
    section_id = Column(String(36), ForeignKey("course_sections.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(Enum(LessonType), nullable=False)
    content_url = Column(String(512), nullable=True)  # For video lessons
    duration_minutes = Column(Integer, nullable=True)  # For video lessons
    order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    section = relationship("SectionModel", back_populates="lessons")
    progress = relationship("LessonProgressModel", back_populates="lesson", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Lesson(id={self.id}, title={self.title}, type={self.type})>" 