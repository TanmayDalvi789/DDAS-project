"""Input validation and sanitization utilities."""

import re
from typing import Any, Optional
from html import escape
from urllib.parse import quote


class InputValidator:
    """Input validation utilities."""
    
    # Regex patterns
    USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    PASSWORD_PATTERN = re.compile(r"^.{8,128}$")  # At least 8 chars
    UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format."""
        if not isinstance(username, str):
            return False
        return bool(InputValidator.USERNAME_PATTERN.match(username))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        if not isinstance(email, str):
            return False
        return bool(InputValidator.EMAIL_PATTERN.match(email))
    
    @staticmethod
    def validate_password(password: str) -> bool:
        """Validate password strength."""
        if not isinstance(password, str):
            return False
        
        # Check length
        if not InputValidator.PASSWORD_PATTERN.match(password):
            return False
        
        # Check for variety (at least one uppercase, one lowercase, one digit)
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        return has_upper and has_lower and has_digit
    
    @staticmethod
    def validate_uuid(value: str) -> bool:
        """Validate UUID format."""
        if not isinstance(value, str):
            return False
        return bool(InputValidator.UUID_PATTERN.match(value))
    
    @staticmethod
    def validate_length(value: str, min_len: int = 1, max_len: int = 1000) -> bool:
        """Validate string length."""
        if not isinstance(value, str):
            return False
        return min_len <= len(value) <= max_len
    
    @staticmethod
    def validate_numeric(value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None) -> bool:
        """Validate numeric value."""
        try:
            num = int(value)
            if min_val is not None and num < min_val:
                return False
            if max_val is not None and num > max_val:
                return False
            return True
        except (ValueError, TypeError):
            return False


class InputSanitizer:
    """Input sanitization utilities."""
    
    @staticmethod
    def sanitize_html(text: str, allow_tags: bool = False) -> str:
        """
        Sanitize HTML content.
        
        Args:
            text: Text to sanitize
            allow_tags: Whether to allow HTML tags
        
        Returns:
            Sanitized text
        """
        if not isinstance(text, str):
            return ""
        
        if allow_tags:
            # Only escape dangerous characters
            return escape(text)
        else:
            # Escape all HTML
            return escape(text)
    
    @staticmethod
    def sanitize_sql(text: str) -> str:
        """
        Sanitize SQL injection attempts.
        
        Args:
            text: Text that might contain SQL
        
        Returns:
            Sanitized text (should not be used in queries, use parameterized instead)
        """
        if not isinstance(text, str):
            return ""
        
        # Escape single quotes
        text = text.replace("'", "''")
        
        # Remove SQL keywords at start
        dangerous_keywords = [
            "DROP", "DELETE", "INSERT", "UPDATE", "ALTER",
            "EXEC", "EXECUTE", "UNION", "SELECT",
        ]
        
        for keyword in dangerous_keywords:
            if text.upper().startswith(keyword):
                text = text[len(keyword):].strip()
        
        return text
    
    @staticmethod
    def sanitize_path(path: str) -> str:
        """
        Sanitize file path.
        
        Args:
            path: File path
        
        Returns:
            Sanitized path
        """
        if not isinstance(path, str):
            return ""
        
        # Remove directory traversal attempts
        path = path.replace("..", "")
        path = path.replace("\\", "/")
        
        # Remove leading slashes
        while path.startswith("/"):
            path = path[1:]
        
        return path
    
    @staticmethod
    def sanitize_url_param(param: str) -> str:
        """
        Sanitize URL parameter.
        
        Args:
            param: URL parameter
        
        Returns:
            Sanitized parameter
        """
        if not isinstance(param, str):
            return ""
        
        # URL encode the parameter
        return quote(param, safe="")
    
    @staticmethod
    def sanitize_json_string(text: str) -> str:
        """
        Sanitize JSON string.
        
        Args:
            text: Text for JSON
        
        Returns:
            Sanitized text safe for JSON
        """
        if not isinstance(text, str):
            return ""
        
        # Escape special JSON characters
        text = text.replace("\\", "\\\\")
        text = text.replace('"', '\\"')
        text = text.replace("\n", "\\n")
        text = text.replace("\r", "\\r")
        text = text.replace("\t", "\\t")
        
        return text
    
    @staticmethod
    def sanitize_field(value: str, field_type: str = "text") -> str:
        """
        Sanitize field based on type.
        
        Args:
            value: Field value
            field_type: Type of field (text, email, username, path, url_param)
        
        Returns:
            Sanitized value
        """
        if not isinstance(value, str):
            return ""
        
        if field_type == "email":
            return value.strip().lower()
        elif field_type == "username":
            return value.strip().lower()
        elif field_type == "path":
            return InputSanitizer.sanitize_path(value)
        elif field_type == "url_param":
            return InputSanitizer.sanitize_url_param(value)
        else:
            # Default: sanitize HTML
            return InputSanitizer.sanitize_html(value)


class SecurityValidator:
    """Combined validation and security checks."""
    
    @staticmethod
    def validate_credentials(username: str, password: str) -> tuple[bool, str]:
        """
        Validate username and password.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not InputValidator.validate_username(username):
            return False, "Invalid username format"
        
        if not InputValidator.validate_password(password):
            return False, "Password must be 8+ characters with uppercase, lowercase, and digits"
        
        return True, ""
    
    @staticmethod
    def validate_user_creation(username: str, email: str, password: str) -> tuple[bool, str]:
        """
        Validate user creation inputs.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not InputValidator.validate_username(username):
            return False, "Invalid username format (3-32 alphanumeric, underscore, hyphen)"
        
        if not InputValidator.validate_email(email):
            return False, "Invalid email format"
        
        if not InputValidator.validate_password(password):
            return False, "Password requirements: 8+ characters, uppercase, lowercase, digits"
        
        return True, ""
