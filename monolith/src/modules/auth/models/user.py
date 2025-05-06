from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship

from src.common.database import Base

class UserModel(Base):
    """User database model."""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    password_reset_tokens = relationship("PasswordResetTokenModel", back_populates="user", cascade="all, delete-orphan")
    email_verification_tokens = relationship("EmailVerificationTokenModel", back_populates="user", cascade="all, delete-orphan")
    
    # Indices
    __table_args__ = (
        Index("ix_users_email_is_active", "email", "is_active"),
    )
    
    def __repr__(self):
        return f"<User {self.email}>"

class PasswordResetTokenModel(Base):
    """Password reset token database model."""
    __tablename__ = "password_reset_tokens"
    
    id = Column(String(36), primary_key=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("UserModel", back_populates="password_reset_tokens")
    
    # Indices
    __table_args__ = (
        Index("ix_password_reset_tokens_user_id", "user_id"),
        Index("ix_password_reset_tokens_used", "used"),
    )
    
    def __repr__(self):
        return f"<PasswordResetToken {self.id} for user {self.user_id}>"

class EmailVerificationTokenModel(Base):
    """Email verification token database model."""
    __tablename__ = "email_verification_tokens"
    
    id = Column(String(36), primary_key=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("UserModel", back_populates="email_verification_tokens")
    
    # Indices
    __table_args__ = (
        Index("ix_email_verification_tokens_user_id", "user_id"),
        Index("ix_email_verification_tokens_used", "used"),
    )
    
    def __repr__(self):
        return f"<EmailVerificationToken {self.id} for user {self.user_id}>"

class RefreshTokenModel(Base):
    """Refresh token database model."""
    __tablename__ = "refresh_tokens"
    
    id = Column(String(36), primary_key=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    revoked_reason = Column(String(255), nullable=True)
    device_info = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 can be up to 45 chars
    
    # Indices
    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_revoked", "revoked"),
    )
    
    def __repr__(self):
        status = "revoked" if self.revoked else "active"
        return f"<RefreshToken {self.id} for user {self.user_id} ({status})>"

class PasswordHistoryModel(Base):
    """Password history database model."""
    __tablename__ = "password_history"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indices
    __table_args__ = (
        Index("ix_password_history_user_id", "user_id"),
    )
    
    def __repr__(self):
        return f"<PasswordHistory {self.id} for user {self.user_id}>"
