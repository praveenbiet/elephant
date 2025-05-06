from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.config import get_settings
from src.common.database import get_db
from src.common.logger import get_logger
from src.modules.auth.persistence.user_repository import UserRepository
from src.modules.identity.persistence.profile_repository import ProfileRepository

logger = get_logger(__name__)
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token extraction from requests
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"/api/v1/auth/token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that a plain password matches the hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)

def create_access_token(
    data: Dict[str, Any], 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get the current user from the token.
    
    Validates the JWT token and returns the user data.
    Raises HTTPException if validation fails.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the token
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        # Get the user from the database
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        
        if user is None:
            raise credentials_exception
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user account"
            )
        
        return user.to_dict()
        
    except JWTError:
        logger.warning("Invalid JWT token", extra={"props": {"token": token}})
        raise credentials_exception

async def get_current_user_with_permissions(
    user: Dict[str, Any] = Depends(get_current_user),
    required_permissions: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get the current user and check they have the required permissions.
    
    If no permissions are required, just returns the user.
    """
    if not required_permissions:
        return user
    
    # Get user's profile with roles and permissions
    profile_repo = ProfileRepository(db)
    user_permissions = await profile_repo.get_user_permissions(user["id"])
    
    # Check if user has admin role (which grants all permissions)
    if "admin" in user_permissions.get("roles", []):
        return user
    
    # Check specific permissions
    for required_perm in required_permissions:
        if required_perm not in user_permissions.get("permissions", []):
            logger.warning(
                f"User {user['id']} attempted to access a resource requiring {required_perm} permission",
                extra={"props": {"user_id": user["id"], "required_permission": required_perm}}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
    
    return user

def is_admin(
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Check if the current user is an admin."""
    return get_current_user_with_permissions(
        user=user,
        required_permissions=["admin.access"],
        db=db
    )
