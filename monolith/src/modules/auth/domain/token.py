from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class PasswordResetToken:
    """
    Password reset token for password recovery.
    """
    token: str
    user_id: str
    expires_at: datetime
    created_at: datetime = None
    used: bool = False
    used_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def is_expired(self) -> bool:
        """
        Check if the token is expired.
        
        Returns:
            True if token is expired, False otherwise
        """
        return datetime.utcnow() > self.expires_at
    
    def mark_as_used(self) -> None:
        """Mark the token as used."""
        self.used = True
        self.used_at = datetime.utcnow()

@dataclass
class EmailVerificationToken:
    """
    Email verification token for verifying user emails.
    """
    token: str
    user_id: str
    expires_at: datetime
    created_at: datetime = None
    used: bool = False
    used_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def is_expired(self) -> bool:
        """
        Check if the token is expired.
        
        Returns:
            True if token is expired, False otherwise
        """
        return datetime.utcnow() > self.expires_at
    
    def mark_as_used(self) -> None:
        """Mark the token as used."""
        self.used = True
        self.used_at = datetime.utcnow()

@dataclass
class RefreshToken:
    """
    Refresh token for obtaining new access tokens.
    """
    token: str
    user_id: str
    expires_at: datetime
    created_at: datetime = None
    revoked: bool = False
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def is_expired(self) -> bool:
        """
        Check if the token is expired.
        
        Returns:
            True if token is expired, False otherwise
        """
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """
        Check if the token is valid.
        
        Returns:
            True if token is valid, False otherwise
        """
        return not self.is_expired() and not self.revoked
    
    def revoke(self, reason: str = "User logout") -> None:
        """
        Revoke the token.
        
        Args:
            reason: Reason for revocation
        """
        self.revoked = True
        self.revoked_at = datetime.utcnow()
        self.revoked_reason = reason

@dataclass
class AccessToken:
    """
    Access token for API authorization.
    """
    token: str
    user_id: str
    expires_at: datetime
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def is_expired(self) -> bool:
        """
        Check if the token is expired.
        
        Returns:
            True if token is expired, False otherwise
        """
        return datetime.utcnow() > self.expires_at
