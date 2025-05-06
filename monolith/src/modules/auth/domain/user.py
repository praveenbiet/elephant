from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass
class User:
    """
    User domain entity representing a user in the system.
    """
    id: str
    email: str
    password_hash: str
    first_name: str
    last_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert user entity to dictionary representation.
        
        Returns:
            Dictionary representation of the user
        """
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None
        }
    
    @property
    def full_name(self) -> str:
        """
        Get the user's full name.
        
        Returns:
            Full name as a string
        """
        return f"{self.first_name} {self.last_name}"
    
    def is_password_expired(self, password_expiry_days: int = 90) -> bool:
        """
        Check if the user's password is expired.
        
        Args:
            password_expiry_days: Number of days after which a password expires
            
        Returns:
            True if password is expired, False otherwise
        """
        if not self.updated_at:
            return False
            
        password_age = (datetime.utcnow() - self.updated_at).days
        return password_age > password_expiry_days
    
    def update_last_login(self) -> None:
        """Update the user's last login timestamp."""
        self.last_login_at = datetime.utcnow()
    
    def deactivate(self) -> None:
        """Deactivate the user."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def activate(self) -> None:
        """Activate the user."""
        self.is_active = True
        self.updated_at = datetime.utcnow()
    
    def mark_verified(self) -> None:
        """Mark the user as verified."""
        self.is_verified = True
        self.updated_at = datetime.utcnow()
    
    def update_profile(self, first_name: Optional[str] = None, last_name: Optional[str] = None) -> None:
        """
        Update the user's profile information.
        
        Args:
            first_name: New first name
            last_name: New last name
        """
        if first_name is not None:
            self.first_name = first_name
        
        if last_name is not None:
            self.last_name = last_name
        
        self.updated_at = datetime.utcnow()
