from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Index, Text
from sqlalchemy.orm import relationship

from src.common.database import Base

class UserProfileModel(Base):
    """User profile database model."""
    __tablename__ = "user_profiles"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(255), nullable=True)
    title = Column(String(100), nullable=True)
    company = Column(String(100), nullable=True)
    website = Column(String(255), nullable=True)
    location = Column(String(100), nullable=True)
    social_links = Column(JSON, nullable=True)  # JSON field for social media links
    preferences = Column(JSON, nullable=True)   # JSON field for user preferences
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indices
    __table_args__ = (
        Index("ix_user_profiles_user_id", "user_id"),
    )
    
    def __repr__(self):
        return f"<UserProfile {self.id} for user {self.user_id}>"
