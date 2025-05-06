from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from sqlalchemy import select, update, insert, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from src.common.logger import get_logger
from src.modules.identity.domain.profile import UserProfile
from src.modules.identity.domain.role import Role, Permission
from src.modules.identity.models.user_profile import UserProfileModel
from src.modules.identity.models.role import RoleModel, PermissionModel, UserRoleModel, RolePermissionModel

logger = get_logger(__name__)

class ProfileRepository:
    """
    Repository for user profile and role management.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_profile_by_user_id(self, user_id: str) -> Optional[UserProfile]:
        """
        Get a user profile by user ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User profile domain entity if found, None otherwise
        """
        try:
            query = select(UserProfileModel).where(UserProfileModel.user_id == user_id)
            result = await self.db.execute(query)
            profile_model = result.scalars().first()
            
            if not profile_model:
                return None
                
            return self._map_profile_to_domain(profile_model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting profile for user {user_id}: {str(e)}", exc_info=True)
            return None
    
    async def create_profile(self, profile: UserProfile) -> bool:
        """
        Create a new user profile.
        
        Args:
            profile: User profile domain entity
            
        Returns:
            True if created successfully, False otherwise
        """
        try:
            profile_model = UserProfileModel(
                id=profile.id or str(uuid.uuid4()),
                user_id=profile.user_id,
                bio=profile.bio,
                avatar_url=profile.avatar_url,
                title=profile.title,
                company=profile.company,
                website=profile.website,
                location=profile.location,
                social_links=profile.social_links,
                preferences=profile.preferences,
                created_at=profile.created_at or datetime.utcnow(),
                updated_at=profile.updated_at or datetime.utcnow()
            )
            
            self.db.add(profile_model)
            await self.db.commit()
            return True
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error creating profile for user {profile.user_id}: {str(e)}", exc_info=True)
            return False
    
    async def update_profile(self, profile: UserProfile) -> bool:
        """
        Update an existing user profile.
        
        Args:
            profile: User profile domain entity
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            query = update(UserProfileModel).where(UserProfileModel.user_id == profile.user_id).values(
                bio=profile.bio,
                avatar_url=profile.avatar_url,
                title=profile.title,
                company=profile.company,
                website=profile.website,
                location=profile.location,
                social_links=profile.social_links,
                preferences=profile.preferences,
                updated_at=datetime.utcnow()
            )
            
            await self.db.execute(query)
            await self.db.commit()
            return True
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error updating profile for user {profile.user_id}: {str(e)}", exc_info=True)
            return False
    
    async def get_user_roles(self, user_id: str) -> List[str]:
        """
        Get a user's roles.
        
        Args:
            user_id: User ID
            
        Returns:
            List of role codes (e.g. ["admin", "instructor"])
        """
        try:
            query = select(RoleModel.code).join(
                UserRoleModel, UserRoleModel.role_id == RoleModel.id
            ).where(
                UserRoleModel.user_id == user_id
            )
            
            result = await self.db.execute(query)
            roles = result.scalars().all()
            
            return list(roles)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting roles for user {user_id}: {str(e)}", exc_info=True)
            return []
    
    async def get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """
        Get a user's permissions including those from their roles.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with roles and permissions
        """
        try:
            # Get user roles
            roles_query = select(RoleModel.code).join(
                UserRoleModel, UserRoleModel.role_id == RoleModel.id
            ).where(
                UserRoleModel.user_id == user_id
            )
            
            roles_result = await self.db.execute(roles_query)
            roles = roles_result.scalars().all()
            
            # Get permissions from roles
            permissions_query = select(PermissionModel.code).join(
                RolePermissionModel, RolePermissionModel.permission_id == PermissionModel.id
            ).join(
                RoleModel, RoleModel.id == RolePermissionModel.role_id
            ).join(
                UserRoleModel, and_(
                    UserRoleModel.role_id == RoleModel.id,
                    UserRoleModel.user_id == user_id
                )
            ).distinct()
            
            permissions_result = await self.db.execute(permissions_query)
            permissions = permissions_result.scalars().all()
            
            return {
                "roles": list(roles),
                "permissions": list(permissions)
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting permissions for user {user_id}: {str(e)}", exc_info=True)
            return {"roles": [], "permissions": []}
    
    async def assign_role_to_user(self, user_id: str, role_code: str) -> bool:
        """
        Assign a role to a user.
        
        Args:
            user_id: User ID
            role_code: Role code
            
        Returns:
            True if assigned successfully, False otherwise
        """
        try:
            # Check if role exists
            role_query = select(RoleModel).where(RoleModel.code == role_code)
            role_result = await self.db.execute(role_query)
            role = role_result.scalars().first()
            
            if not role:
                logger.error(f"Role {role_code} not found")
                return False
            
            # Check if user already has this role
            existing_query = select(UserRoleModel).where(
                UserRoleModel.user_id == user_id,
                UserRoleModel.role_id == role.id
            )
            
            existing_result = await self.db.execute(existing_query)
            if existing_result.scalars().first():
                # User already has this role
                return True
            
            # Assign role to user
            user_role = UserRoleModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                role_id=role.id,
                created_at=datetime.utcnow()
            )
            
            self.db.add(user_role)
            await self.db.commit()
            
            logger.info(f"Role {role_code} assigned to user {user_id}")
            return True
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error assigning role {role_code} to user {user_id}: {str(e)}", exc_info=True)
            return False
    
    async def remove_role_from_user(self, user_id: str, role_code: str) -> bool:
        """
        Remove a role from a user.
        
        Args:
            user_id: User ID
            role_code: Role code
            
        Returns:
            True if removed successfully, False otherwise
        """
        try:
            # Get role ID from code
            role_query = select(RoleModel.id).where(RoleModel.code == role_code)
            role_result = await self.db.execute(role_query)
            role_id = role_result.scalar_one_or_none()
            
            if not role_id:
                logger.error(f"Role {role_code} not found")
                return False
            
            # Remove role from user
            query = delete(UserRoleModel).where(
                UserRoleModel.user_id == user_id,
                UserRoleModel.role_id == role_id
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
            logger.info(f"Role {role_code} removed from user {user_id}")
            return True
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error removing role {role_code} from user {user_id}: {str(e)}", exc_info=True)
            return False
    
    async def get_all_roles(self) -> List[Role]:
        """
        Get all roles with their permissions.
        
        Returns:
            List of role domain entities
        """
        try:
            query = select(RoleModel)
            result = await self.db.execute(query)
            role_models = result.scalars().all()
            
            roles = []
            for role_model in role_models:
                # Get permissions for this role
                perm_query = select(PermissionModel).join(
                    RolePermissionModel, RolePermissionModel.permission_id == PermissionModel.id
                ).where(
                    RolePermissionModel.role_id == role_model.id
                )
                
                perm_result = await self.db.execute(perm_query)
                perm_models = perm_result.scalars().all()
                
                permissions = [
                    Permission(
                        id=perm.id,
                        code=perm.code,
                        name=perm.name,
                        description=perm.description
                    )
                    for perm in perm_models
                ]
                
                roles.append(Role(
                    id=role_model.id,
                    code=role_model.code,
                    name=role_model.name,
                    description=role_model.description,
                    permissions=permissions
                ))
            
            return roles
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting all roles: {str(e)}", exc_info=True)
            return []
    
    def _map_profile_to_domain(self, profile_model: UserProfileModel) -> UserProfile:
        """
        Map a database model to a domain entity.
        
        Args:
            profile_model: Database model
            
        Returns:
            Domain entity
        """
        return UserProfile(
            id=profile_model.id,
            user_id=profile_model.user_id,
            bio=profile_model.bio,
            avatar_url=profile_model.avatar_url,
            title=profile_model.title,
            company=profile_model.company,
            website=profile_model.website,
            location=profile_model.location,
            social_links=profile_model.social_links,
            preferences=profile_model.preferences,
            created_at=profile_model.created_at,
            updated_at=profile_model.updated_at
        )
