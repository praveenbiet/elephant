from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, DateTime, ForeignKey, Index, Text, Boolean
from sqlalchemy.orm import relationship

from src.common.database import Base

class RoleModel(Base):
    """Role database model."""
    __tablename__ = "roles"
    
    id = Column(String(36), primary_key=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    permissions = relationship("PermissionModel", secondary="role_permissions", back_populates="roles")
    
    def __repr__(self):
        return f"<Role {self.code}>"

class PermissionModel(Base):
    """Permission database model."""
    __tablename__ = "permissions"
    
    id = Column(String(36), primary_key=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    roles = relationship("RoleModel", secondary="role_permissions", back_populates="permissions")
    
    def __repr__(self):
        return f"<Permission {self.code}>"

class RolePermissionModel(Base):
    """Role-permission relationship database model."""
    __tablename__ = "role_permissions"
    
    id = Column(String(36), primary_key=True)
    role_id = Column(String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(String(36), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indices
    __table_args__ = (
        Index("ix_role_permissions_role_id", "role_id"),
        Index("ix_role_permissions_permission_id", "permission_id"),
        Index("uq_role_permissions_role_permission", "role_id", "permission_id", unique=True),
    )
    
    def __repr__(self):
        return f"<RolePermission {self.role_id} - {self.permission_id}>"

class UserRoleModel(Base):
    """User-role relationship database model."""
    __tablename__ = "user_roles"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indices
    __table_args__ = (
        Index("ix_user_roles_user_id", "user_id"),
        Index("ix_user_roles_role_id", "role_id"),
        Index("uq_user_roles_user_role", "user_id", "role_id", unique=True),
    )
    
    def __repr__(self):
        return f"<UserRole {self.user_id} - {self.role_id}>"
