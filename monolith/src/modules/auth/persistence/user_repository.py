import uuid
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy import select, update, insert, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from src.common.logger import get_logger
from src.modules.auth.domain.user import User
from src.modules.auth.domain.token import PasswordResetToken, EmailVerificationToken
from src.modules.auth.models.user import UserModel, PasswordResetTokenModel, EmailVerificationTokenModel

logger = get_logger(__name__)

class UserRepository:
    """
    Repository for user-related database operations.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Get a user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User domain entity if found, None otherwise
        """
        try:
            query = select(UserModel).where(UserModel.id == user_id)
            result = await self.db.execute(query)
            user_model = result.scalars().first()
            
            if not user_model:
                return None
                
            return self._map_to_domain(user_model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by ID {user_id}: {str(e)}", exc_info=True)
            return None
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email.
        
        Args:
            email: User email
            
        Returns:
            User domain entity if found, None otherwise
        """
        try:
            query = select(UserModel).where(UserModel.email == email.lower())
            result = await self.db.execute(query)
            user_model = result.scalars().first()
            
            if not user_model:
                return None
                
            return self._map_to_domain(user_model)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by email {email}: {str(e)}", exc_info=True)
            return None
    
    async def create(self, user: User) -> bool:
        """
        Create a new user.
        
        Args:
            user: User domain entity
            
        Returns:
            True if created successfully, False otherwise
        """
        try:
            user_model = UserModel(
                id=user.id,
                email=user.email.lower(),
                password_hash=user.password_hash,
                first_name=user.first_name,
                last_name=user.last_name,
                is_active=user.is_active,
                is_verified=user.is_verified,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
            
            self.db.add(user_model)
            await self.db.commit()
            return True
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error creating user {user.email}: {str(e)}", exc_info=True)
            return False
    
    async def update(self, user: User) -> bool:
        """
        Update an existing user.
        
        Args:
            user: User domain entity
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            query = update(UserModel).where(UserModel.id == user.id).values(
                email=user.email.lower(),
                first_name=user.first_name,
                last_name=user.last_name,
                is_active=user.is_active,
                is_verified=user.is_verified,
                updated_at=datetime.utcnow(),
                last_login_at=user.last_login_at
            )
            
            await self.db.execute(query)
            await self.db.commit()
            return True
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error updating user {user.id}: {str(e)}", exc_info=True)
            return False
    
    async def update_password(self, user_id: str, password_hash: str) -> bool:
        """
        Update a user's password.
        
        Args:
            user_id: User ID
            password_hash: New password hash
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            query = update(UserModel).where(UserModel.id == user_id).values(
                password_hash=password_hash,
                updated_at=datetime.utcnow()
            )
            
            await self.db.execute(query)
            await self.db.commit()
            return True
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error updating password for user {user_id}: {str(e)}", exc_info=True)
            return False
    
    async def delete(self, user_id: str) -> bool:
        """
        Delete a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            query = delete(UserModel).where(UserModel.id == user_id)
            await self.db.execute(query)
            await self.db.commit()
            return True
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error deleting user {user_id}: {str(e)}", exc_info=True)
            return False
    
    async def save_password_reset_token(self, token: PasswordResetToken) -> bool:
        """
        Save a password reset token.
        
        Args:
            token: Password reset token entity
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            token_model = PasswordResetTokenModel(
                id=str(uuid.uuid4()),
                token=token.token,
                user_id=token.user_id,
                expires_at=token.expires_at,
                created_at=token.created_at or datetime.utcnow(),
                used=token.used,
                used_at=token.used_at
            )
            
            self.db.add(token_model)
            await self.db.commit()
            return True
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error saving password reset token for user {token.user_id}: {str(e)}", exc_info=True)
            return False
    
    async def get_password_reset_token(self, token: str) -> Optional[PasswordResetToken]:
        """
        Get a password reset token.
        
        Args:
            token: Token string
            
        Returns:
            Password reset token entity if found, None otherwise
        """
        try:
            query = select(PasswordResetTokenModel).where(PasswordResetTokenModel.token == token)
            result = await self.db.execute(query)
            token_model = result.scalars().first()
            
            if not token_model:
                return None
                
            return PasswordResetToken(
                token=token_model.token,
                user_id=token_model.user_id,
                expires_at=token_model.expires_at,
                created_at=token_model.created_at,
                used=token_model.used,
                used_at=token_model.used_at
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting password reset token: {str(e)}", exc_info=True)
            return None
    
    async def mark_token_as_used(self, token: str) -> bool:
        """
        Mark a password reset token as used.
        
        Args:
            token: Token string
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            query = update(PasswordResetTokenModel).where(
                PasswordResetTokenModel.token == token
            ).values(
                used=True,
                used_at=datetime.utcnow()
            )
            
            await self.db.execute(query)
            await self.db.commit()
            return True
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error marking token as used: {str(e)}", exc_info=True)
            return False
    
    async def create_email_verification_token(self, user_id: str) -> str:
        """
        Create a new email verification token.
        
        Args:
            user_id: User ID
            
        Returns:
            Token string
        """
        token = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        try:
            token_model = EmailVerificationTokenModel(
                id=str(uuid.uuid4()),
                token=token,
                user_id=user_id,
                expires_at=expires_at,
                created_at=datetime.utcnow(),
                used=False
            )
            
            self.db.add(token_model)
            await self.db.commit()
            return token
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error creating email verification token for user {user_id}: {str(e)}", exc_info=True)
            raise
    
    async def verify_email_token(self, token: str) -> Optional[str]:
        """
        Verify an email verification token.
        
        Args:
            token: Token string
            
        Returns:
            User ID if token is valid, None otherwise
        """
        try:
            query = select(EmailVerificationTokenModel).where(
                EmailVerificationTokenModel.token == token,
                EmailVerificationTokenModel.used == False,
                EmailVerificationTokenModel.expires_at > datetime.utcnow()
            )
            
            result = await self.db.execute(query)
            token_model = result.scalars().first()
            
            if not token_model:
                return None
                
            # Mark token as used
            token_model.used = True
            token_model.used_at = datetime.utcnow()
            
            await self.db.commit()
            return token_model.user_id
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error verifying email token: {str(e)}", exc_info=True)
            return None
    
    async def update_last_login(self, user_id: str) -> bool:
        """
        Update a user's last login timestamp.
        
        Args:
            user_id: User ID
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            query = update(UserModel).where(UserModel.id == user_id).values(
                last_login_at=datetime.utcnow()
            )
            
            await self.db.execute(query)
            await self.db.commit()
            return True
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Error updating last login for user {user_id}: {str(e)}", exc_info=True)
            return False
    
    def _map_to_domain(self, user_model: UserModel) -> User:
        """
        Map a database model to a domain entity.
        
        Args:
            user_model: Database model
            
        Returns:
            Domain entity
        """
        return User(
            id=user_model.id,
            email=user_model.email,
            password_hash=user_model.password_hash,
            first_name=user_model.first_name,
            last_name=user_model.last_name,
            is_active=user_model.is_active,
            is_verified=user_model.is_verified,
            created_at=user_model.created_at,
            updated_at=user_model.updated_at,
            last_login_at=user_model.last_login_at
        )
