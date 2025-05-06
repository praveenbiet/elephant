import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from src.common.auth import verify_password, get_password_hash
from src.common.config import get_settings
from src.common.logger import get_logger
from src.modules.auth.persistence.user_repository import UserRepository
from src.modules.auth.domain.user import User
from src.modules.auth.domain.token import PasswordResetToken
from src.modules.auth.adapters.email_adapter import EmailAdapter

logger = get_logger(__name__)
settings = get_settings()

class AuthenticationService:
    """
    Service for user authentication and password management.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repository = UserRepository(db)
        self.email_adapter = EmailAdapter()
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with email and password.
        
        Args:
            email: User's email
            password: User's plain password
            
        Returns:
            User object if authentication is successful, None otherwise
        """
        user = await self.user_repository.get_by_email(email)
        if not user:
            logger.warning(f"Authentication attempt with non-existent email: {email}")
            return None
        
        if not user.is_active:
            logger.warning(f"Authentication attempt with inactive account: {email}")
            return None
        
        if not verify_password(password, user.password_hash):
            logger.warning(f"Failed authentication attempt for user: {email}")
            return None
        
        logger.info(f"User authenticated successfully: {email}")
        return user
    
    async def request_password_reset(self, email: str) -> None:
        """
        Request a password reset for a user.
        
        Creates a password reset token and sends an email to the user.
        
        Args:
            email: User's email
        """
        user = await self.user_repository.get_by_email(email)
        if not user:
            # Don't reveal if email exists or not
            logger.info(f"Password reset requested for non-existent email: {email}")
            return
        
        # Generate reset token
        token_data = {
            "sub": user.id,
            "type": "password_reset",
            "jti": str(uuid.uuid4()),
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        # Store token in database for additional security
        reset_token = PasswordResetToken(
            token=token,
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        await self.user_repository.save_password_reset_token(reset_token)
        
        # Send email with reset link
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        await self.email_adapter.send_password_reset_email(
            recipient_email=user.email,
            recipient_name=f"{user.first_name} {user.last_name}",
            reset_url=reset_url
        )
        
        logger.info(f"Password reset email sent to: {email}")
    
    async def reset_password(self, token: str, new_password: str) -> None:
        """
        Reset a user's password using a reset token.
        
        Args:
            token: Password reset token
            new_password: New password
            
        Raises:
            ValueError: If token is invalid or expired
        """
        try:
            # Decode the token
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            
            if payload.get("type") != "password_reset":
                raise ValueError("Invalid token type")
            
            user_id = payload.get("sub")
            if not user_id:
                raise ValueError("Invalid token")
            
            # Verify token in database
            stored_token = await self.user_repository.get_password_reset_token(token)
            if not stored_token:
                raise ValueError("Invalid or already used token")
            
            if stored_token.used:
                raise ValueError("Token already used")
            
            if stored_token.expires_at < datetime.utcnow():
                raise ValueError("Token expired")
            
            # Get user
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            
            # Update password
            password_hash = get_password_hash(new_password)
            await self.user_repository.update_password(user_id, password_hash)
            
            # Mark token as used
            await self.user_repository.mark_token_as_used(token)
            
            logger.info(f"Password reset successful for user: {user.email}")
            
        except JWTError as e:
            logger.warning(f"Invalid password reset token: {str(e)}")
            raise ValueError("Invalid or expired token")
    
    async def change_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> None:
        """
        Change a user's password.
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            
        Raises:
            ValueError: If current password is incorrect
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Verify current password
        if not verify_password(current_password, user.password_hash):
            logger.warning(f"Failed password change attempt for user: {user.email}")
            raise ValueError("Current password is incorrect")
        
        # Update password
        password_hash = get_password_hash(new_password)
        await self.user_repository.update_password(user_id, password_hash)
        
        logger.info(f"Password changed successfully for user: {user.email}")
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            Decoded token payload
            
        Raises:
            ValueError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            
            return payload
        except JWTError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise ValueError("Invalid or expired token")
