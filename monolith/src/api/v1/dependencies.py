from typing import Annotated, Dict, Any, List, Optional
import redis.asyncio as redis

from fastapi import Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.config import get_settings
from src.common.database import get_db
from src.common.auth import get_current_user, get_current_user_with_permissions
from src.modules.auth.persistence.user_repository import UserRepository
from src.modules.identity.persistence.profile_repository import ProfileRepository

settings = get_settings()

# Redis connection pool
_redis_client = None

async def get_redis_client():
    """Get Redis client for caching and session management."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return _redis_client

# Authentication and authorization dependencies
async def get_optional_current_user(
    token: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> Optional[Dict[str, Any]]:
    """
    Get the current user if authenticated, or None if not.
    This is useful for endpoints that work with both authenticated
    and unauthenticated users.
    """
    if not token:
        return None
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None

# Role-based dependencies
async def get_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get current user if they are an admin."""
    profile_repo = ProfileRepository(db)
    user_roles = await profile_repo.get_user_roles(current_user["id"])
    
    if "admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user

async def get_instructor_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get current user if they are an instructor."""
    profile_repo = ProfileRepository(db)
    user_roles = await profile_repo.get_user_roles(current_user["id"])
    
    if "instructor" not in user_roles and "admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Instructor privileges required"
        )
    
    return current_user

# Pagination and filtering dependencies
class PaginationParams:
    """Pagination parameters for list endpoints."""
    def __init__(
        self, 
        page: int = Query(1, ge=1, description="Page number, starting from 1"),
        page_size: int = Query(20, ge=1, le=100, description="Number of items per page")
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size
        
    def get_pagination_info(self, total_count: int) -> Dict[str, Any]:
        """Get pagination information for response metadata."""
        total_pages = (total_count + self.page_size - 1) // self.page_size
        
        return {
            "page": self.page,
            "page_size": self.page_size,
            "total_items": total_count,
            "total_pages": total_pages
        }

class SortParams:
    """Sorting parameters for list endpoints."""
    def __init__(
        self,
        sort_by: str = Query(None, description="Field to sort by"),
        sort_order: str = Query("asc", description="Sort order (asc or desc)")
    ):
        self.sort_by = sort_by
        self.sort_order = sort_order.lower()
        
        # Validate sort order
        if self.sort_order not in ["asc", "desc"]:
            self.sort_order = "asc"
