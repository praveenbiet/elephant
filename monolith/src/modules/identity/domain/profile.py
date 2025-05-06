from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List

@dataclass
class UserProfile:
    """
    User profile domain entity representing a user's profile information.
    """
    user_id: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    social_links: Optional[Dict[str, str]] = None
    preferences: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert profile entity to dictionary representation.
        
        Returns:
            Dictionary representation of the profile
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "title": self.title,
            "company": self.company,
            "website": self.website,
            "location": self.location,
            "social_links": self.social_links,
            "preferences": self.preferences,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def update(
        self,
        bio: Optional[str] = None,
        avatar_url: Optional[str] = None,
        title: Optional[str] = None,
        company: Optional[str] = None,
        website: Optional[str] = None,
        location: Optional[str] = None,
        social_links: Optional[Dict[str, str]] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update profile information.
        
        Args:
            bio: User bio
            avatar_url: Avatar URL
            title: Job title
            company: Company name
            website: Personal website
            location: User location
            social_links: Social media links
            preferences: User preferences
        """
        self.bio = bio if bio is not None else self.bio
        self.avatar_url = avatar_url if avatar_url is not None else self.avatar_url
        self.title = title if title is not None else self.title
        self.company = company if company is not None else self.company
        self.website = website if website is not None else self.website
        self.location = location if location is not None else self.location
        
        if social_links is not None:
            self.social_links = social_links
        
        if preferences is not None:
            # Merge preferences rather than replacing
            if self.preferences is None:
                self.preferences = {}
            self.preferences.update(preferences)
        
        self.updated_at = datetime.utcnow()
    
    def update_preference(self, key: str, value: Any) -> None:
        """
        Update a single preference.
        
        Args:
            key: Preference key
            value: Preference value
        """
        if self.preferences is None:
            self.preferences = {}
        
        self.preferences[key] = value
        self.updated_at = datetime.utcnow()
    
    def has_completed_profile(self) -> bool:
        """
        Check if the user has completed their profile.
        
        Returns:
            True if profile is complete, False otherwise
        """
        # Define what constitutes a complete profile
        required_fields = [self.bio, self.avatar_url, self.title]
        return all(field is not None and field != "" for field in required_fields)
    
    def add_social_link(self, platform: str, url: str) -> None:
        """
        Add a social media link.
        
        Args:
            platform: Social media platform (e.g., "twitter", "linkedin")
            url: Profile URL
        """
        if self.social_links is None:
            self.social_links = {}
        
        self.social_links[platform] = url
        self.updated_at = datetime.utcnow()
    
    def remove_social_link(self, platform: str) -> None:
        """
        Remove a social media link.
        
        Args:
            platform: Social media platform to remove
        """
        if self.social_links and platform in self.social_links:
            del self.social_links[platform]
            self.updated_at = datetime.utcnow()
