from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index, Enum
from sqlalchemy.orm import relationship

from src.common.database import Base
from src.modules.courses.domain.enrollment import EnrollmentStatus

class EnrollmentModel(Base):
    """Course enrollment database model."""
    __tablename__ = "enrollments"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(EnrollmentStatus), default=EnrollmentStatus.ACTIVE, nullable=False)
    enrolled_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    progress_percentage = Column(Float, default=0.0, nullable=False)
    last_activity_at = Column(DateTime, nullable=True)
    payment_id = Column(String(36), nullable=True)  # Optional link to payment record
    certificate_id = Column(String(36), nullable=True)  # Optional link to certificate
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    course = relationship("CourseModel", back_populates="enrollments")
    
    # Indices
    __table_args__ = (
        Index("ix_enrollments_user_id", "user_id"),
        Index("ix_enrollments_course_id", "course_id"),
        Index("ix_enrollments_status", "status"),
        Index("ix_enrollments_enrolled_at", "enrolled_at"),
        Index("ix_enrollments_completed_at", "completed_at"),
        Index("ix_enrollments_expiry_date", "expiry_date"),
        Index("uq_enrollments_user_course", "user_id", "course_id", unique=True),
    )
    
    def __repr__(self):
        return f"<Enrollment for user {self.user_id} in course {self.course_id}>" 