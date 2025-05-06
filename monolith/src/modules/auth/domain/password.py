import re
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class PasswordPolicy:
    """
    Password policy configuration.
    """
    min_length: int = 8
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special_char: bool = False
    max_length: Optional[int] = 128
    disallow_common_passwords: bool = True
    disallow_username_in_password: bool = True
    max_repeated_chars: Optional[int] = 3
    password_history_count: int = 5
    
    def __post_init__(self):
        if self.max_length is not None and self.min_length > self.max_length:
            raise ValueError("min_length cannot be greater than max_length")

class PasswordValidator:
    """
    Validator for password creation and changes.
    """
    
    def __init__(self, policy: Optional[PasswordPolicy] = None):
        self.policy = policy or PasswordPolicy()
        # Load common passwords list if enabled
        self.common_passwords = set()
        if self.policy.disallow_common_passwords:
            self._load_common_passwords()
    
    def _load_common_passwords(self) -> None:
        """Load list of common passwords to be disallowed."""
        # In a real implementation, this would load from a file
        # For simplicity, we'll just add a few common ones here
        common = [
            "password", "123456", "12345678", "qwerty", "abc123",
            "letmein", "monkey", "password1", "1234", "12345"
        ]
        self.common_passwords = set(common)
    
    def validate(self, password: str, username: Optional[str] = None) -> List[str]:
        """
        Validate a password against the policy.
        
        Args:
            password: The password to validate
            username: The username to check against, if disallow_username_in_password is enabled
            
        Returns:
            List of validation error messages. Empty list if valid.
        """
        errors = []
        
        # Check length
        if len(password) < self.policy.min_length:
            errors.append(f"Password must be at least {self.policy.min_length} characters long")
        
        if self.policy.max_length is not None and len(password) > self.policy.max_length:
            errors.append(f"Password cannot be longer than {self.policy.max_length} characters")
        
        # Check character requirements
        if self.policy.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.policy.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.policy.require_digit and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if self.policy.require_special_char and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        # Check for repeated characters
        if self.policy.max_repeated_chars is not None:
            # Find sequences of repeated characters
            for i in range(len(password) - self.policy.max_repeated_chars + 1):
                if len(set(password[i:i+self.policy.max_repeated_chars])) == 1:
                    errors.append(f"Password cannot contain more than {self.policy.max_repeated_chars} repeated characters")
                    break
        
        # Check for common passwords
        if self.policy.disallow_common_passwords and password.lower() in self.common_passwords:
            errors.append("Password is too common and easily guessable")
        
        # Check for username in password
        if self.policy.disallow_username_in_password and username and username.lower() in password.lower():
            errors.append("Password cannot contain your username")
        
        return errors
    
    def is_valid(self, password: str, username: Optional[str] = None) -> bool:
        """
        Check if a password is valid according to the policy.
        
        Args:
            password: The password to validate
            username: The username to check against, if disallow_username_in_password is enabled
            
        Returns:
            True if password is valid, False otherwise
        """
        return len(self.validate(password, username)) == 0


class PasswordStrengthChecker:
    """
    Checks the strength of a password and provides a score.
    """
    
    @staticmethod
    def calculate_strength(password: str) -> int:
        """
        Calculate the strength of a password on a scale of 0-100.
        
        Args:
            password: The password to check
            
        Returns:
            Strength score between 0-100
        """
        score = 0
        
        # Basic length check (up to 40 points)
        length_score = min(len(password) * 4, 40)
        score += length_score
        
        # Character variety (up to 20 points)
        has_lowercase = any(c.islower() for c in password)
        has_uppercase = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = re.search(r'[!@#$%^&*(),.?":{}|<>]', password) is not None
        
        variety_score = (has_lowercase + has_uppercase + has_digit + has_special) * 5
        score += variety_score
        
        # Distribution - more points if mixed well (up to 20 points)
        if has_lowercase and has_uppercase:
            lower_count = sum(1 for c in password if c.islower())
            upper_count = sum(1 for c in password if c.isupper())
            distribution_ratio = min(lower_count, upper_count) / max(lower_count, upper_count) if max(lower_count, upper_count) > 0 else 0
            score += int(distribution_ratio * 10)
        
        if has_digit:
            digit_positions = [i for i, c in enumerate(password) if c.isdigit()]
            if len(digit_positions) > 1 and digit_positions[-1] - digit_positions[0] > len(password) / 2:
                score += 5
        
        if has_special:
            score += 5
        
        # Penalize for patterns
        # Sequential characters
        for seq in ["abcdefghijklmnopqrstuvwxyz", "qwertyuiop", "asdfghjkl", "zxcvbnm", "01234567890"]:
            for i in range(len(seq) - 2):
                if seq[i:i+3].lower() in password.lower() or seq[i:i+3][::-1].lower() in password.lower():
                    score -= 5
                    break
        
        # Repeated characters
        for i in range(len(password) - 2):
            if password[i] == password[i+1] == password[i+2]:
                score -= 5
                break
        
        # Ensure score is within 0-100 range
        return max(0, min(score, 100))
    
    @staticmethod
    def get_strength_label(score: int) -> str:
        """
        Get a descriptive label for a password strength score.
        
        Args:
            score: The strength score (0-100)
            
        Returns:
            Descriptive label ('Very Weak', 'Weak', 'Moderate', 'Strong', 'Very Strong')
        """
        if score < 20:
            return "Very Weak"
        elif score < 40:
            return "Weak"
        elif score < 60:
            return "Moderate"
        elif score < 80:
            return "Strong"
        else:
            return "Very Strong"
