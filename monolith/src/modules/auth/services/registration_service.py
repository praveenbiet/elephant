from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.auth import get_password_hash
from src.common.logger import get_logger
from src.common.messaging import event_publisher, EventBase
from src.modules.auth.persistence.user_repository import UserRepository
from src.modules.auth.domain.user import User
from src.modules.auth.adapters.email_adapter import EmailAdapter

logger = get_logger(__name__)

class RegistrationService:
    """
    Service for user registration and account management.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repository = UserRepository(db)
        self.email_adapter = EmailAdapter()
    
    async def register_user(
        self, 
        email: str, 
        password: str,
        first_name: str,
        last_name: str,
        require_email_verification: bool = True
    ) -> User:
        """
        Register a new user.
        
        Args:
            email: User's email address
            password: User's plain password
            first_name: User's first name
            last_name: User's last name
            require_email_verification: Whether to require email verification
            
        Returns:
            Created user entity
            
        Raises:
            ValueError: If email already exists or other validation errors
        """
        # Check if email already exists
        existing_user = await self.user_repository.get_by_email(email)
        if existing_user:
            logger.warning(f"Registration attempt with existing email: {email}")
            raise ValueError(f"User with email {email} already exists")
        
        # Create new user
        user_id = str(uuid.uuid4())
        now = datetime.utcnow()
        password_hash = get_password_hash(password)
        
        user = User(
            id=user_id,
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            is_active=not require_email_verification,  # If verification required, account starts inactive
            is_verified=False,
            created_at=now,
            updated_at=now
        )
        
        # Save user to database
        await self.user_repository.create(user)
        logger.info(f"User registered successfully: {email}")
        
        # Send welcome email
        await self.email_adapter.send_welcome_email(
            recipient_email=email,
            recipient_name=f"{first_name} {last_name}"
        )
        
        # If email verification is required, send verification email
        if require_email_verification:
            await self.send_verification_email(user)
        
        # Publish user created event
        await self._publish_user_created_event(user)
        
        return user
    
    async def send_verification_email(self, user: User) -> None:
        """
        Send email verification to a user.
        
        Args:
            user: User entity
        """
        # Generate verification token
        verification_token = await self.user_repository.create_email_verification_token(user.id)
        
        # Send verification email
        await self.email_adapter.send_verification_email(
            recipient_email=user.email,
            recipient_name=f"{user.first_name} {user.last_name}",
            verification_url=f"/verify-email?token={verification_token}"
        )
        
        logger.info(f"Verification email sent to: {user.email}")
    
    async def verify_email(self, token: str) -> Optional[User]:
        """
        Verify a user's email with a verification token.
        
        Args:
            token: Email verification token
            
        Returns:
            User entity if verification is successful, None otherwise
            
        Raises:
            ValueError: If token is invalid or expired
        """
        # Verify token
        user_id = await self.user_repository.verify_email_token(token)
        if not user_id:
            logger.warning(f"Invalid verification token used: {token}")
            raise ValueError("Invalid or expired verification token")
        
        # Update user
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            logger.error(f"User not found for verification token: {token}")
            raise ValueError("User not found")
        
        # Activate user and mark as verified
        user.is_active = True
        user.is_verified = True
        user.updated_at = datetime.utcnow()
        
        await self.user_repository.update(user)
        logger.info(f"Email verified for user: {user.email}")
        
        # Publish user verified event
        await self._publish_user_verified_event(user)
        
        return user
    
    async def _publish_user_created_event(self, user: User) -> None:
        """
        Publish a user created event.
        
        Args:
            user: User entity
        """
        try:
            event = EventBase(
                event_type="user.created",
                producer="auth_service",
                data={
                    "user_id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "created_at": user.created_at.isoformat()
                }
            )
            
            await event_publisher.publish_event(
                topic="users",
                event=event,
                key=user.id
            )
            
            logger.debug(f"Published user.created event for: {user.email}")
        except Exception as e:
            logger.error(f"Failed to publish user.created event: {str(e)}", exc_info=True)
    
    async def _publish_user_verified_event(self, user: User) -> None:
        """
        Publish a user verified event.
        
        Args:
            user: User entity
        """
        try:
            event = EventBase(
                event_type="user.verified",
                producer="auth_service",
                data={
                    "user_id": user.id,
                    "email": user.email,
                    "verified_at": datetime.utcnow().isoformat()
                }
            )
            
            await event_publisher.publish_event(
                topic="users",
                event=event,
                key=user.id
            )
            
            logger.debug(f"Published user.verified event for: {user.email}")
        except Exception as e:
            logger.error(f"Failed to publish user.verified event: {str(e)}", exc_info=True)
