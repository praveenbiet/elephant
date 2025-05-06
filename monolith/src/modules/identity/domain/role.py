from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional

@dataclass
class Permission:
    """
    Permission domain entity representing a system permission.
    """
    code: str
    name: str
    description: Optional[str] = None
    id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert permission entity to dictionary representation.
        
        Returns:
            Dictionary representation of the permission
        """
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description
        }

@dataclass
class Role:
    """
    Role domain entity representing a user role with associated permissions.
    """
    code: str
    name: str
    description: Optional[str] = None
    permissions: List[Permission] = field(default_factory=list)
    id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert role entity to dictionary representation.
        
        Returns:
            Dictionary representation of the role
        """
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "permissions": [p.to_dict() for p in self.permissions]
        }
    
    def has_permission(self, permission_code: str) -> bool:
        """
        Check if the role has a specific permission.
        
        Args:
            permission_code: Permission code to check
            
        Returns:
            True if role has the permission, False otherwise
        """
        return any(p.code == permission_code for p in self.permissions)
    
    def add_permission(self, permission: Permission) -> None:
        """
        Add a permission to the role.
        
        Args:
            permission: Permission to add
        """
        if not self.has_permission(permission.code):
            self.permissions.append(permission)
    
    def remove_permission(self, permission_code: str) -> None:
        """
        Remove a permission from the role.
        
        Args:
            permission_code: Code of the permission to remove
        """
        self.permissions = [p for p in self.permissions if p.code != permission_code]

@dataclass
class UserRole:
    """
    User role assignment domain entity.
    """
    user_id: str
    role_id: str
    created_at: Optional[datetime] = None
    id: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert user role entity to dictionary representation.
        
        Returns:
            Dictionary representation of the user role
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
