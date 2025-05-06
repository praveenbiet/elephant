from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logger import get_logger
from src.modules.identity.domain.profile import UserProfile
from src.modules.identity.persistence.profile_repository import ProfileRepository
from src.modules.auth.persistence.user_repository import UserRepository

logger = get_logger(__name__)

class UserProfileService:
    """
    Service for user profile management.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.profile_repository = ProfileRepository(db)
        self.user_repository = UserRepository(db)
    
    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Get a user's profile.
        
        Args:
            user_id: User ID
            
        Returns:
            User profile domain entity if found, None otherwise
        """
        return await self.profile_repository.get_profile_by_user_id(user_id)
    
    async def get_or_create_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Get a user's profile, creating one if it doesn't exist.
        
        Args:
            user_id: User ID
            
        Returns:
            User profile domain entity
        """
        # Check if user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.error(f"User {user_id} not found when getting or creating profile")
            return None
        
        # Try to get existing profile
        profile = await self.profile_repository.get_profile_by_user_id(user_id)
        
        if profile:
            return profile
        
        # Create new profile
        now = datetime.utcnow()
        new_profile = UserProfile(
            id=str(uuid.uuid4()),
            user_id=user_id,
            created_at=now,
            updated_at=now
        )
        
        success = await self.profile_repository.create_profile(new_profile)
        
        if not success:
            logger.error(f"Failed to create profile for user {user_id}")
            return None
        
        logger.info(f"Created new profile for user {user_id}")
        return new_profile
    
    async def update_profile(
        self,
        user_id: str,
        bio: Optional[str] = None,
        avatar_url: Optional[str] = None,
        title: Optional[str] = None,
        company: Optional[str] = None,
        website: Optional[str] = None,
        location: Optional[str] = None,
        social_links: Optional[Dict[str, str]] = None
    ) -> Optional[UserProfile]:
        """
        Update a user's profile.
        
        Args:
            user_id: User ID
            bio: User bio
            avatar_url: Avatar URL
            title: Job title
            company: Company name
            website: Personal website
            location: User location
            social_links: Social media links
            
        Returns:
            Updated user profile domain entity if successful, None otherwise
        """
        # Get or create profile
        profile = await self.get_or_create_profile(user_id)
        
        if not profile:
            logger.error(f"Could not get or create profile for user {user_id}")
            return None
        
        # Update profile fields
        profile.update(
            bio=bio,
            avatar_url=avatar_url,
            title=title,
            company=company,
            website=website,
            location=location,
            social_links=social_links
        )
        
        # Save updated profile
        success = await self.profile_repository.update_profile(profile)
        
        if not success:
            logger.error(f"Failed to update profile for user {user_id}")
            return None
        
        logger.info(f"Updated profile for user {user_id}")
        return profile
    
    async def update_preference(
        self,
        user_id: str,
        key: str,
        value: Any
    ) -> Optional[UserProfile]:
        """
        Update a user preference.
        
        Args:
            user_id: User ID
            key: Preference key
            value: Preference value
            
        Returns:
            Updated user profile domain entity if successful, None otherwise
        """
        # Get or create profile
        profile = await self.get_or_create_profile(user_id)
        
        if not profile:
            logger.error(f"Could not get or create profile for user {user_id}")
            return None
        
        # Update preference
        profile.update_preference(key, value)
        
        # Save updated profile
        success = await self.profile_repository.update_profile(profile)
        
        if not success:
            logger.error(f"Failed to update preference for user {user_id}")
            return None
        
        logger.info(f"Updated preference '{key}' for user {user_id}")
        return profile
    
    async def delete_profile(self, user_id: str) -> bool:
        """
        Delete a user's profile.
        
        Note: This is typically not called directly but rather when a user is deleted.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted successfully, False otherwise
        """
        # Currently we don't implement this directly as profiles are deleted via database cascade
        # when a user is deleted. But we keep this method for potential future use.
        logger.warning(f"Attempted to delete profile for user {user_id} - operation not implemented")
        return False
