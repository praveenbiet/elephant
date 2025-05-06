from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, ForeignKey, JSON, Enum, Index
from sqlalchemy.orm import relationship

from src.common.database import Base
from src.modules.courses.domain.course import CourseStatus, CourseLevel

class CourseModel(Base):
    """Course database model."""
    __tablename__ = "courses"
    
    id = Column(String(36), primary_key=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    instructor_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=False)
    short_description = Column(String(500), nullable=True)
    image_url = Column(String(255), nullable=True)
    level = Column(Enum(CourseLevel), default=CourseLevel.ALL_LEVELS, nullable=False)
    status = Column(Enum(CourseStatus), default=CourseStatus.DRAFT, nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    subcategory_ids = Column(JSON, nullable=True)  # Array of subcategory IDs
    tags = Column(JSON, nullable=True)  # Array of tags
    price = Column(Float, nullable=True)
    sale_price = Column(Float, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    skills_gained = Column(JSON, nullable=True)  # Array of skills
    requirements = Column(JSON, nullable=True)  # Array of requirements
    language = Column(String(10), default="en", nullable=False)
    caption_languages = Column(JSON, nullable=True)  # Array of language codes
    meta_keywords = Column(String(500), nullable=True)
    meta_description = Column(String(500), nullable=True)
    featured = Column(Boolean, default=False, nullable=False)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    sections = relationship("SectionModel", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("EnrollmentModel", back_populates="course", cascade="all, delete-orphan")
    reviews = relationship("ReviewModel", back_populates="course", cascade="all, delete-orphan")
    
    # Indices
    __table_args__ = (
        Index("ix_courses_instructor_id", "instructor_id"),
        Index("ix_courses_category_id", "category_id"),
        Index("ix_courses_status", "status"),
        Index("ix_courses_level", "level"),
        Index("ix_courses_featured", "featured"),
    )
    
    def __repr__(self):
        return f"<Course {self.title}>"

class SectionModel(Base):
    """Course section database model."""
    __tablename__ = "course_sections"
    
    id = Column(String(36), primary_key=True)
    course_id = Column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    position = Column(Integer, nullable=False)
    is_free_preview = Column(Boolean, default=False, nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    course = relationship("CourseModel", back_populates="sections")
    lessons = relationship("LessonModel", back_populates="section", cascade="all, delete-orphan")
    
    # Indices
    __table_args__ = (
        Index("ix_course_sections_course_id", "course_id"),
        Index("ix_course_sections_position", "position"),
        Index("ix_course_sections_is_free_preview", "is_free_preview"),
    )
    
    def __repr__(self):
        return f"<Section {self.title} for course {self.course_id}>"

class LessonModel(Base):
    """Course lesson database model."""
    __tablename__ = "course_lessons"
    
    id = Column(String(36), primary_key=True)
    section_id = Column(String(36), ForeignKey("course_sections.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    type = Column(String(20), nullable=False)  # video, text, quiz, assignment, etc.
    content_id = Column(String(36), nullable=True)  # ID of associated content
    description = Column(Text, nullable=True)
    position = Column(Integer, nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    is_free_preview = Column(Boolean, default=False, nullable=False)
    is_downloadable = Column(Boolean, default=False, nullable=False)
    preview_image_url = Column(String(255), nullable=True)
    attachments = Column(JSON, nullable=True)  # Array of attachment objects
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    section = relationship("SectionModel", back_populates="lessons")
    progress_records = relationship("LessonProgressModel", back_populates="lesson", cascade="all, delete-orphan")
    
    # Indices
    __table_args__ = (
        Index("ix_course_lessons_section_id", "section_id"),
        Index("ix_course_lessons_position", "position"),
        Index("ix_course_lessons_type", "type"),
        Index("ix_course_lessons_is_free_preview", "is_free_preview"),
    )
    
    def __repr__(self):
        return f"<Lesson {self.title} for section {self.section_id}>"

class LessonProgressModel(Base):
    """Lesson progress tracking database model."""
    __tablename__ = "lesson_progress"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(String(36), ForeignKey("course_lessons.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="not_started", nullable=False)  # not_started, in_progress, completed
    progress_percentage = Column(Float, default=0.0, nullable=False)
    last_position_seconds = Column(Integer, default=0, nullable=False)  # For video lessons
    completed_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    lesson = relationship("LessonModel", back_populates="progress_records")
    
    # Indices
    __table_args__ = (
        Index("ix_lesson_progress_user_id", "user_id"),
        Index("ix_lesson_progress_lesson_id", "lesson_id"),
        Index("ix_lesson_progress_status", "status"),
        Index("uq_lesson_progress_user_lesson", "user_id", "lesson_id", unique=True),
    )
    
    def __repr__(self):
        return f"<LessonProgress for user {self.user_id} on lesson {self.lesson_id}>" 