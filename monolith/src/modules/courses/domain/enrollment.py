from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

class EnrollmentStatus(str, Enum):
    """Status of a course enrollment."""
    ACTIVE = "active"
    COMPLETED = "completed"
    REFUNDED = "refunded"
    EXPIRED = "expired"
    PAUSED = "paused"

@dataclass
class Enrollment:
    """
    Enrollment domain entity representing a student's enrollment in a course.
    """
    user_id: str
    course_id: str
    id: Optional[str] = None
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE
    enrolled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    progress_percentage: float = 0.0
    last_activity_at: Optional[datetime] = None
    payment_id: Optional[str] = None
    certificate_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        now = datetime.utcnow()
        if self.enrolled_at is None:
            self.enrolled_at = now
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert enrollment entity to dictionary representation.
        
        Returns:
            Dictionary representation of the enrollment
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "course_id": self.course_id,
            "status": self.status.value if isinstance(self.status, EnrollmentStatus) else self.status,
            "enrolled_at": self.enrolled_at.isoformat() if self.enrolled_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "progress_percentage": self.progress_percentage,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "payment_id": self.payment_id,
            "certificate_id": self.certificate_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def update_progress(self, progress_percentage: float) -> None:
        """
        Update the enrollment progress.
        
        Args:
            progress_percentage: New progress percentage (0.0 to 100.0)
        """
        self.progress_percentage = max(0.0, min(100.0, progress_percentage))
        self.last_activity_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        # Auto-mark as completed if 100% progress
        if self.progress_percentage >= 100.0 and self.status != EnrollmentStatus.COMPLETED:
            self.complete()
    
    def complete(self) -> None:
        """Mark the enrollment as completed."""
        self.status = EnrollmentStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.progress_percentage = 100.0
        self.updated_at = datetime.utcnow()
    
    def refund(self) -> None:
        """Mark the enrollment as refunded."""
        self.status = EnrollmentStatus.REFUNDED
        self.updated_at = datetime.utcnow()
    
    def expire(self) -> None:
        """Mark the enrollment as expired."""
        self.status = EnrollmentStatus.EXPIRED
        self.updated_at = datetime.utcnow()
    
    def pause(self) -> None:
        """Pause the enrollment."""
        self.status = EnrollmentStatus.PAUSED
        self.updated_at = datetime.utcnow()
    
    def reactivate(self) -> None:
        """Reactivate the enrollment."""
        self.status = EnrollmentStatus.ACTIVE
        self.updated_at = datetime.utcnow()
    
    def is_active(self) -> bool:
        """Check if the enrollment is active."""
        if self.status != EnrollmentStatus.ACTIVE:
            return False
            
        # Check if enrollment has expired
        if self.expiry_date and datetime.utcnow() > self.expiry_date:
            return False
            
        return True
    
    def record_activity(self) -> None:
        """Record user activity in the course."""
        self.last_activity_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def set_certificate(self, certificate_id: str) -> None:
        """
        Set the certificate ID for a completed enrollment.
        
        Args:
            certificate_id: ID of the generated certificate
        """
        if self.status != EnrollmentStatus.COMPLETED:
            self.complete()
            
        self.certificate_id = certificate_id
        self.updated_at = datetime.utcnow() 