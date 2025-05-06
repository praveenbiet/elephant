import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Dict, Any, List
from pathlib import Path

from src.common.config import get_settings
from src.common.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

class EmailAdapter:
    """
    Adapter for sending emails related to authentication.
    """
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_USER or "noreply@example.com"
        self.from_name = "E-Learning Platform"
        self.template_dir = Path(__file__).parent.parent.parent.parent / "templates" / "emails"
    
    async def send_email(
        self, 
        recipient_email: str,
        subject: str, 
        text_content: str,
        html_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None
    ) -> bool:
        """
        Send an email.
        
        Args:
            recipient_email: Recipient's email address
            subject: Email subject
            text_content: Plain text content
            html_content: HTML content
            cc: Carbon copy recipients
            bcc: Blind carbon copy recipients
            reply_to: Reply-to email address
            
        Returns:
            True if sent successfully, False otherwise
        """
        # If email settings not configured, log message and return
        if not all([self.smtp_host, self.smtp_port, self.smtp_user, self.smtp_password]):
            logger.warning(
                f"Email not sent - SMTP not configured. Would have sent to: {recipient_email}, subject: {subject}"
            )
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = recipient_email
            
            if cc:
                msg['Cc'] = ", ".join(cc)
            
            if reply_to:
                msg['Reply-To'] = reply_to
            
            # Add text part
            text_part = MIMEText(text_content, 'plain')
            msg.attach(text_part)
            
            # Add HTML part if provided
            if html_content:
                html_part = MIMEText(html_content, 'html')
                msg.attach(html_part)
            
            # Determine all recipients
            recipients = [recipient_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if settings.DEBUG:
                    server.set_debuglevel(1)
                
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, recipients, msg.as_string())
            
            logger.info(f"Email sent successfully to {recipient_email}, subject: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}", exc_info=True)
            return False
    
    def _render_template(
        self, 
        template_name: str, 
        context: Dict[str, Any]
    ) -> str:
        """
        Render an email template.
        
        Args:
            template_name: Name of the template file
            context: Template variables
            
        Returns:
            Rendered template as string
        """
        # In a real app, use a template engine like Jinja2
        # For simplicity, we'll use a very basic string replacement here
        template_path = self.template_dir / template_name
        
        if not template_path.exists():
            logger.warning(f"Email template not found: {template_name}")
            # Fallback to simple format string
            if "password_reset" in template_name:
                return f"Hello {context.get('name', 'there')},\n\nUse this link to reset your password: {context.get('reset_url', '')}\n\nThis link will expire in 24 hours.\n\nThanks,\nThe E-Learning Platform Team"
            elif "welcome" in template_name:
                return f"Welcome to the E-Learning Platform, {context.get('name', 'there')}!\n\nThank you for signing up. We're excited to have you as a new member.\n\nBest regards,\nThe E-Learning Platform Team"
            elif "verification" in template_name:
                return f"Hello {context.get('name', 'there')},\n\nPlease verify your email address by clicking this link: {context.get('verification_url', '')}\n\nThanks,\nThe E-Learning Platform Team"
            else:
                return "Email content not available."
        
        with open(template_path, 'r') as file:
            template = file.read()
            
        # Replace variables
        for key, value in context.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
            
        return template
    
    async def send_welcome_email(
        self,
        recipient_email: str,
        recipient_name: str
    ) -> bool:
        """
        Send a welcome email to a new user.
        
        Args:
            recipient_email: Recipient's email address
            recipient_name: Recipient's name
            
        Returns:
            True if sent successfully, False otherwise
        """
        subject = "Welcome to E-Learning Platform"
        context = {
            "name": recipient_name,
            "platform_name": "E-Learning Platform"
        }
        
        text_content = self._render_template("welcome.txt", context)
        html_content = self._render_template("welcome.html", context)
        
        return await self.send_email(
            recipient_email=recipient_email,
            subject=subject,
            text_content=text_content,
            html_content=html_content
        )
    
    async def send_verification_email(
        self,
        recipient_email: str,
        recipient_name: str,
        verification_url: str
    ) -> bool:
        """
        Send an email verification link.
        
        Args:
            recipient_email: Recipient's email address
            recipient_name: Recipient's name
            verification_url: URL for email verification
            
        Returns:
            True if sent successfully, False otherwise
        """
        subject = "Verify Your Email Address"
        context = {
            "name": recipient_name,
            "verification_url": f"{settings.FRONTEND_URL}{verification_url}"
        }
        
        text_content = self._render_template("verification.txt", context)
        html_content = self._render_template("verification.html", context)
        
        return await self.send_email(
            recipient_email=recipient_email,
            subject=subject,
            text_content=text_content,
            html_content=html_content
        )
    
    async def send_password_reset_email(
        self,
        recipient_email: str,
        recipient_name: str,
        reset_url: str
    ) -> bool:
        """
        Send a password reset link.
        
        Args:
            recipient_email: Recipient's email address
            recipient_name: Recipient's name
            reset_url: URL for password reset
            
        Returns:
            True if sent successfully, False otherwise
        """
        subject = "Reset Your Password"
        context = {
            "name": recipient_name,
            "reset_url": reset_url
        }
        
        text_content = self._render_template("password_reset.txt", context)
        html_content = self._render_template("password_reset.html", context)
        
        return await self.send_email(
            recipient_email=recipient_email,
            subject=subject,
            text_content=text_content,
            html_content=html_content
        )
