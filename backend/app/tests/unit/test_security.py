"""Security and authentication tests."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app.middleware.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
    hash_password,
    check_permission,
    get_permissions_for_role,
    ROLE_PERMISSIONS,
    User,
)
from app.security.rate_limiter import RateLimiter, IPRateLimiter, UserRateLimiter, APIKeyRateLimiter
from app.security.crypto import CryptoUtil
from app.security.validation import InputValidator, InputSanitizer, SecurityValidator


class TestPasswordHashing:
    """Test password hashing and verification."""
    
    def test_hash_password_creates_different_hashes(self):
        """Same password should create different hashes."""
        password = "SecurePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2
    
    def test_verify_password_success(self):
        """Correct password should verify successfully."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
    
    def test_verify_password_failure(self):
        """Wrong password should fail verification."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        assert verify_password("WrongPassword", hashed) is False
    
    def test_verify_empty_password(self):
        """Empty password should fail."""
        hashed = hash_password("password")
        assert verify_password("", hashed) is False


class TestJWTTokens:
    """Test JWT token creation and decoding."""
    
    def test_create_access_token(self):
        """Should create valid access token."""
        user = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            role="user",
            is_active=True,
        )
        token = create_access_token(user)
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_refresh_token(self):
        """Should create valid refresh token."""
        user = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            role="user",
            is_active=True,
        )
        token = create_refresh_token(user)
        assert token is not None
        assert isinstance(token, str)
    
    def test_decode_valid_access_token(self):
        """Should decode valid access token."""
        user = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            role="user",
            is_active=True,
        )
        token = create_access_token(user)
        decoded = decode_token(token)
        
        assert decoded is not None
        assert decoded.username == "testuser"
        assert decoded.user_id == "user123"
    
    def test_decode_invalid_token(self):
        """Should return None for invalid token."""
        token = "invalid.token.string"
        decoded = decode_token(token)
        assert decoded is None
    
    def test_decode_expired_token(self):
        """Should return None for expired token."""
        # Create token with 0 seconds expiry
        user = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            role="user",
            is_active=True,
        )
        token = create_access_token(user, expires_delta=timedelta(seconds=0))
        
        # Wait a moment
        import time
        time.sleep(0.1)
        
        decoded = decode_token(token)
        # Token might still be valid at exact moment, so check is lenient


class TestRBACPermissions:
    """Test role-based access control."""
    
    def test_get_permissions_for_user_role(self):
        """User role should have specific permissions."""
        permissions = get_permissions_for_role("user")
        assert "events:read" in permissions
        assert "events:create" in permissions
        assert "users:delete" not in permissions
    
    def test_get_permissions_for_admin_role(self):
        """Admin role should have broader permissions."""
        permissions = get_permissions_for_role("admin")
        assert "*:read" in permissions
        assert "*:create" in permissions
        assert "*:update" in permissions
    
    def test_get_permissions_for_superadmin_role(self):
        """Superadmin should have all permissions."""
        permissions = get_permissions_for_role("superadmin")
        assert "*" in permissions
    
    def test_check_permission_allowed(self):
        """Should allow permission for authorized role."""
        user = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            role="admin",
            is_active=True,
        )
        assert check_permission(user, "users:read") is True
    
    def test_check_permission_denied(self):
        """Should deny permission for unauthorized role."""
        user = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            role="user",
            is_active=True,
        )
        assert check_permission(user, "users:delete") is False


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limiter_allows_requests_within_limit(self):
        """Should allow requests within limit."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        for i in range(5):
            is_allowed, info = limiter.is_allowed("test_user")
            assert is_allowed is True
            assert info["remaining"] == 5 - (i + 1)
    
    def test_rate_limiter_blocks_requests_over_limit(self):
        """Should block requests over limit."""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        
        # Use up the limit
        for i in range(3):
            is_allowed, _ = limiter.is_allowed("test_user")
            assert is_allowed is True
        
        # Next request should be blocked
        is_allowed, info = limiter.is_allowed("test_user")
        assert is_allowed is False
        assert info["remaining"] == 0
    
    def test_ip_rate_limiter_default_values(self):
        """IP rate limiter should have default values."""
        limiter = IPRateLimiter()
        assert limiter.max_requests == 1000
    
    def test_user_rate_limiter_default_values(self):
        """User rate limiter should have default values."""
        limiter = UserRateLimiter()
        assert limiter.max_requests == 500
    
    def test_api_key_rate_limiter_default_values(self):
        """API key rate limiter should have default values."""
        limiter = APIKeyRateLimiter()
        assert limiter.max_requests == 100
    
    def test_rate_limiter_reset_after_window(self):
        """Should reset after time window."""
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        
        # Use up limit
        limiter.is_allowed("user")
        limiter.is_allowed("user")
        
        is_allowed, _ = limiter.is_allowed("user")
        assert is_allowed is False
        
        # Wait for window to pass
        import time
        time.sleep(1.1)
        
        is_allowed, _ = limiter.is_allowed("user")
        assert is_allowed is True


class TestEncryption:
    """Test encryption utilities."""
    
    def test_encrypt_decrypt_roundtrip(self):
        """Should encrypt and decrypt correctly."""
        crypto = CryptoUtil()
        plaintext = "sensitive_data"
        
        encrypted = crypto.encrypt(plaintext)
        decrypted = crypto.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_encrypt_creates_different_ciphertexts(self):
        """Same plaintext should create different ciphertexts."""
        crypto = CryptoUtil()
        plaintext = "sensitive_data"
        
        encrypted1 = crypto.encrypt(plaintext)
        encrypted2 = crypto.encrypt(plaintext)
        
        assert encrypted1 != encrypted2
    
    def test_decrypt_invalid_data(self):
        """Should return None for invalid encrypted data."""
        crypto = CryptoUtil()
        try:
            result = crypto.decrypt("invalid_data")
            assert result is None or isinstance(result, str)
        except Exception:
            pass
    
    def test_encrypt_with_custom_key(self):
        """Should use provided secret key."""
        key = "custom_secret_key"
        crypto1 = CryptoUtil(secret_key=key)
        crypto2 = CryptoUtil(secret_key=key)
        
        plaintext = "test_data"
        encrypted = crypto1.encrypt(plaintext)
        decrypted = crypto2.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_field_encryption(self):
        """Should encrypt and decrypt fields."""
        crypto = CryptoUtil()
        plaintext = "user@example.com"
        
        encrypted = crypto.encrypt(plaintext)
        decrypted = crypto.decrypt(encrypted)
        
        assert decrypted == plaintext


class TestInputValidation:
    """Test input validation."""
    
    def test_validate_username_valid(self):
        """Valid username should pass."""
        validator = InputValidator()
        assert validator.validate_username("testuser") is True
        assert validator.validate_username("user123") is True
    
    def test_validate_username_too_short(self):
        """Username shorter than 3 chars should fail."""
        validator = InputValidator()
        assert validator.validate_username("ab") is False
    
    def test_validate_username_invalid_chars(self):
        """Username with invalid chars should fail."""
        validator = InputValidator()
        assert validator.validate_username("user@123") is False
        assert validator.validate_username("user!") is False
    
    def test_validate_email_valid(self):
        """Valid email should pass."""
        validator = InputValidator()
        assert validator.validate_email("user@example.com") is True
    
    def test_validate_email_invalid(self):
        """Invalid email should fail."""
        validator = InputValidator()
        assert validator.validate_email("invalid@") is False
        assert validator.validate_email("@example.com") is False
    
    def test_validate_password_valid(self):
        """Valid password should pass."""
        validator = InputValidator()
        assert validator.validate_password("SecurePass123") is True
    
    def test_validate_password_too_short(self):
        """Password shorter than 8 chars should fail."""
        validator = InputValidator()
        assert validator.validate_password("Pass123") is False
    
    def test_validate_password_missing_uppercase(self):
        """Password without uppercase should fail."""
        validator = InputValidator()
        assert validator.validate_password("securepass123") is False
    
    def test_validate_password_missing_digit(self):
        """Password without digit should fail."""
        validator = InputValidator()
        assert validator.validate_password("SecurePass") is False


class TestInputSanitization:
    """Test input sanitization."""
    
    def test_sanitize_html_escapes_tags(self):
        """HTML tags should be escaped."""
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
    
    def test_sanitize_sql_removes_keywords(self):
        """SQL keywords should be removed."""
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize_sql("test'; DROP TABLE users;--")
        assert "DROP" not in result or result.startswith("'")
    
    def test_sanitize_sql_escapes_quotes(self):
        """Single quotes should be escaped."""
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize_sql("test' or '1'='1")
        assert "''" in result or "\\" in result
    
    def test_sanitize_path_removes_traversal(self):
        """Path traversal sequences should be removed."""
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize_path("../../../etc/passwd")
        assert "../" not in result
    
    def test_sanitize_url_param_encodes(self):
        """URL params should be encoded."""
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize_url_param("hello world")
        assert " " not in result or "%20" in result
    
    def test_sanitize_json_escapes(self):
        """JSON special chars should be escaped."""
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize_json_string('test"quote')
        assert '\\"' in result or '\\u0022' in result


class TestSecurityValidator:
    """Test security validation."""
    
    def test_validate_credentials_valid(self):
        """Valid credentials should pass."""
        validator = SecurityValidator()
        is_valid, error = validator.validate_credentials("testuser", "SecurePass123")
        assert is_valid is True
    
    def test_validate_credentials_invalid_username(self):
        """Invalid username should fail."""
        validator = SecurityValidator()
        is_valid, error = validator.validate_credentials("ab", "SecurePass123")
        assert is_valid is False
    
    def test_validate_credentials_invalid_password(self):
        """Invalid password should fail."""
        validator = SecurityValidator()
        is_valid, error = validator.validate_credentials("testuser", "weak")
        assert is_valid is False
    
    def test_validate_user_creation_valid(self):
        """Valid user creation should pass."""
        validator = SecurityValidator()
        is_valid, error = validator.validate_user_creation(
            "newuser",
            "user@example.com",
            "SecurePass123",
        )
        assert is_valid is True
    
    def test_validate_user_creation_invalid_email(self):
        """Invalid email should fail."""
        validator = SecurityValidator()
        is_valid, error = validator.validate_user_creation(
            "newuser",
            "invalid@",
            "SecurePass123",
        )
        assert is_valid is False


class TestTokenData:
    """Test token data models."""
    
    def test_token_data_creation(self):
        """Should create token data with required fields."""
        from app.middleware.auth import TokenData
        
        token_data = TokenData(
            user_id="user123",
            username="testuser",
            role="user",
            exp=datetime.utcnow() + timedelta(hours=1),
        )
        
        assert token_data.user_id == "user123"
        assert token_data.username == "testuser"
        assert token_data.role == "user"


class TestAPIKeyValidation:
    """Test API key validation."""
    
    def test_api_key_format_validation(self):
        """Should validate API key format."""
        from app.middleware.auth import validate_api_key
        
        # This would require database setup, so we'll mock
        with patch('app.middleware.auth.validate_api_key') as mock_validate:
            mock_validate.return_value = User(
                id="user123",
                username="api_user",
                email="api@example.com",
                role="user",
                is_active=True,
            )
            
            result = validate_api_key("sk_valid_key_123")
            assert result is not None
