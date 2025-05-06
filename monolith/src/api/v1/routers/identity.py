from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body, Path, Query
from pydantic import BaseModel, validator, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_db
from src.common.auth import get_current_user, get_current_user_with_permissions
from src.api.v1.dependencies import get_admin_user
from src.modules.identity.services.user_profile_service import UserProfileService
from src.modules.identity.services.authorization_service import AuthorizationService

router = APIRouter(prefix="/identity", tags=["Identity"])

# Request/Response Models
class ProfileResponse(BaseModel):
    """User profile response model."""
    id: str
    user_id: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    social_links: Optional[Dict[str, str]] = None
    preferences: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str

class UpdateProfileRequest(BaseModel):
    """Update profile request model."""
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    social_links: Optional[Dict[str, str]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "bio": "Software engineer with expertise in Python and FastAPI",
                "avatar_url": "https://example.com/avatar.jpg",
                "title": "Senior Software Engineer",
                "company": "Tech Company",
                "website": "https://example.com",
                "location": "New York, NY",
                "social_links": {
                    "twitter": "https://twitter.com/username",
                    "linkedin": "https://linkedin.com/in/username",
                    "github": "https://github.com/username"
                }
            }
        }

class UpdatePreferenceRequest(BaseModel):
    """Update user preference request model."""
    key: str
    value: Any

class RoleResponse(BaseModel):
    """Role response model."""
    id: str
    code: str
    name: str
    description: Optional[str] = None

class PermissionResponse(BaseModel):
    """Permission response model."""
    id: str
    code: str
    name: str
    description: Optional[str] = None

class RoleWithPermissionsResponse(RoleResponse):
    """Role with permissions response model."""
    permissions: List[PermissionResponse]

class AssignRoleRequest(BaseModel):
    """Assign role request model."""
    role_code: str = Field(..., description="Role code to assign")

# Routes
@router.get("/profile", response_model=ProfileResponse)
async def get_own_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current user's profile.
    
    Returns profile information for the authenticated user.
    """
    profile_service = UserProfileService(db)
    
    # Get or create profile
    profile = await profile_service.get_or_create_profile(current_user["id"])
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    profile_dict = profile.to_dict()
    return ProfileResponse(**profile_dict)

@router.put("/profile", response_model=ProfileResponse)
async def update_own_profile(
    data: UpdateProfileRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the current user's profile.
    
    Updates profile information for the authenticated user.
    """
    profile_service = UserProfileService(db)
    
    try:
        profile = await profile_service.update_profile(
            user_id=current_user["id"],
            bio=data.bio,
            avatar_url=data.avatar_url,
            title=data.title,
            company=data.company,
            website=data.website,
            location=data.location,
            social_links=data.social_links
        )
        
        profile_dict = profile.to_dict()
        return ProfileResponse(**profile_dict)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/profile/preferences", response_model=ProfileResponse)
async def update_preference(
    data: UpdatePreferenceRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a single user preference.
    
    Updates a specific preference for the authenticated user.
    """
    profile_service = UserProfileService(db)
    
    try:
        profile = await profile_service.update_preference(
            user_id=current_user["id"],
            key=data.key,
            value=data.value
        )
        
        profile_dict = profile.to_dict()
        return ProfileResponse(**profile_dict)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/profile/{user_id}", response_model=ProfileResponse)
async def get_user_profile(
    user_id: str = Path(..., description="User ID"),
    current_user: Dict[str, Any] = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Get profile for a specific user.
    
    Requires the requesting user to be an admin or the profile owner.
    """
    # Check if user is admin or requesting their own profile
    if current_user["id"] != user_id:
        # Verify permission to view other profiles
        auth_service = AuthorizationService(db)
        has_permission = await auth_service.check_permission(
            user_id=current_user["id"],
            permission_code="identity.view_profile"
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this profile"
            )
    
    profile_service = UserProfileService(db)
    profile = await profile_service.get_profile(user_id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    profile_dict = profile.to_dict()
    return ProfileResponse(**profile_dict)

@router.get("/roles", response_model=List[RoleResponse])
async def get_user_roles(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get roles for the current user.
    
    Returns a list of roles assigned to the authenticated user.
    """
    auth_service = AuthorizationService(db)
    roles = await auth_service.get_user_roles(current_user["id"])
    
    return [
        RoleResponse(
            id=role.id,
            code=role.code,
            name=role.name,
            description=role.description
        )
        for role in roles
    ]

@router.get("/roles/all", response_model=List[RoleWithPermissionsResponse])
async def get_all_roles(
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all roles with their permissions.
    
    Admin-only endpoint to get all roles in the system.
    """
    auth_service = AuthorizationService(db)
    roles = await auth_service.get_all_roles()
    
    return [
        RoleWithPermissionsResponse(
            id=role.id,
            code=role.code,
            name=role.name,
            description=role.description,
            permissions=[
                PermissionResponse(
                    id=perm.id,
                    code=perm.code,
                    name=perm.name,
                    description=perm.description
                )
                for perm in role.permissions
            ]
        )
        for role in roles
    ]

@router.post("/users/{user_id}/roles", status_code=status.HTTP_204_NO_CONTENT)
async def assign_role_to_user(
    data: AssignRoleRequest,
    user_id: str = Path(..., description="User ID"),
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Assign a role to a user.
    
    Admin-only endpoint to assign a role to a user.
    """
    auth_service = AuthorizationService(db)
    
    try:
        success = await auth_service.assign_role_to_user(
            user_id=user_id,
            role_code=data.role_code
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to assign role"
            )
        
        return None
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/users/{user_id}/roles/{role_code}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role_from_user(
    user_id: str = Path(..., description="User ID"),
    role_code: str = Path(..., description="Role code"),
    admin_user: Dict[str, Any] = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a role from a user.
    
    Admin-only endpoint to remove a role from a user.
    """
    auth_service = AuthorizationService(db)
    
    try:
        success = await auth_service.remove_role_from_user(
            user_id=user_id,
            role_code=role_code
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to remove role"
            )
        
        return None
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
