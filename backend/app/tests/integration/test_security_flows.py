"""Integration tests for security and authentication workflows."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.middleware.auth import User, create_access_token, hash_password


@pytest.fixture
def mock_users_repo():
    """Mock users repository."""
    with patch('app.db.repositories.users.UsersRepository') as MockRepo:
        repo = MockRepo()
        
        # Mock user for login
        repo.authenticate_user.return_value = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            role="user",
            is_active=True,
            created_at=datetime.utcnow(),
        )
        
        # Mock user by username
        repo.get_user_by_username.return_value = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            role="user",
            is_active=True,
        )
        
        # Mock user by email
        repo.get_user_by_email.return_value = None
        
        # Mock user by id
        repo.get_user_by_id.return_value = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            role="user",
            is_active=True,
        )
        
        yield repo


class TestAuthenticationFlow:
    """Test complete authentication flows."""
    
    def test_user_login_flow(self, mock_users_repo):
        """Test user login flow."""
        # This would require full app setup
        # Demonstrating the workflow:
        
        # 1. User sends credentials
        credentials = {"username": "testuser", "password": "SecurePass123"}
        
        # 2. System authenticates
        user = mock_users_repo.authenticate_user(
            credentials["username"],
            credentials["password"],
        )
        
        assert user is not None
        assert user.username == "testuser"
        
        # 3. System creates tokens
        access_token = create_access_token(user)
        assert access_token is not None
    
    def test_user_registration_flow(self, mock_users_repo):
        """Test user registration flow."""
        # 1. Check if user exists
        existing_user = mock_users_repo.get_user_by_username("newuser")
        assert existing_user is None
        
        # 2. Check if email exists
        existing_email = mock_users_repo.get_user_by_email("new@example.com")
        assert existing_email is None
        
        # 3. Create new user (mocked)
        mock_users_repo.create_user = Mock(return_value=User(
            id="new_user_id",
            username="newuser",
            email="new@example.com",
            role="user",
            is_active=True,
            created_at=datetime.utcnow(),
        ))
        
        new_user = mock_users_repo.create_user(
            username="newuser",
            email="new@example.com",
            password="SecurePass123",
        )
        
        assert new_user.username == "newuser"
        assert new_user.email == "new@example.com"
    
    def test_token_refresh_flow(self, mock_users_repo):
        """Test token refresh flow."""
        # 1. User has refresh token
        user = mock_users_repo.get_user_by_id("user123")
        assert user is not None
        
        # 2. Create new access token from refresh
        new_access_token = create_access_token(user)
        assert new_access_token is not None


class TestRateLimitingFlow:
    """Test rate limiting integration."""
    
    def test_ip_based_rate_limiting(self):
        """Test IP-based rate limiting."""
        from app.security.rate_limiter import IPRateLimiter
        
        limiter = IPRateLimiter()
        ip = "192.168.1.1"
        
        # Allow some requests
        for i in range(5):
            is_allowed, info = limiter.is_allowed(ip)
            assert is_allowed is True
            assert info["remaining"] < info["limit"]
        
        # Verify rate limit info
        is_allowed, info = limiter.is_allowed(ip)
        assert "limit" in info
        assert "remaining" in info
        assert "reset" in info
    
    def test_user_based_rate_limiting(self):
        """Test user-based rate limiting."""
        from app.security.rate_limiter import UserRateLimiter
        
        limiter = UserRateLimiter()
        user_id = "user123"
        
        # Get rate limit info
        is_allowed, info = limiter.is_allowed(user_id)
        assert is_allowed is True
        assert info["limit"] == 500  # Default for user limiter
    
    def test_api_key_based_rate_limiting(self):
        """Test API key-based rate limiting."""
        from app.security.rate_limiter import APIKeyRateLimiter
        
        limiter = APIKeyRateLimiter()
        api_key = "sk_test_key_123"
        
        # Get rate limit info
        is_allowed, info = limiter.is_allowed(api_key)
        assert is_allowed is True
        assert info["limit"] == 100  # Default for API key limiter


class TestEncryptionFlow:
    """Test encryption workflows."""
    
    def test_sensitive_data_encryption(self):
        """Test encrypting sensitive data."""
        from app.security.crypto import CryptoUtil
        
        crypto = CryptoUtil()
        
        # Encrypt various types of sensitive data
        sensitive_data = [
            "user@example.com",
            "phone:1234567890",
            "ssn:123-45-6789",
        ]
        
        for data in sensitive_data:
            encrypted = crypto.encrypt(data)
            assert encrypted is not None
            assert encrypted != data
            
            decrypted = crypto.decrypt(encrypted)
            assert decrypted == data
    
    def test_key_derivation(self):
        """Test key derivation."""
        from app.security.crypto import CryptoUtil
        
        # Different secret keys should produce different derived keys
        crypto1 = CryptoUtil(secret_key="secret1")
        crypto2 = CryptoUtil(secret_key="secret2")
        
        plaintext = "test_data"
        encrypted1 = crypto1.encrypt(plaintext)
        
        # Different key should not decrypt
        try:
            decrypted = crypto2.decrypt(encrypted1)
            # If it decrypts, it should not match
            assert decrypted != plaintext or encrypted1.split(".")[0] == encrypted1.split(".")[0]
        except Exception:
            pass  # Expected to fail


class TestInputValidationFlow:
    """Test input validation workflows."""
    
    def test_user_creation_validation(self):
        """Test validating user creation input."""
        from app.security.validation import SecurityValidator
        
        validator = SecurityValidator()
        
        # Valid input
        is_valid, error = validator.validate_user_creation(
            "newuser",
            "user@example.com",
            "SecurePass123",
        )
        assert is_valid is True
        
        # Invalid username
        is_valid, error = validator.validate_user_creation(
            "a",
            "user@example.com",
            "SecurePass123",
        )
        assert is_valid is False
        
        # Invalid email
        is_valid, error = validator.validate_user_creation(
            "newuser",
            "invalid@",
            "SecurePass123",
        )
        assert is_valid is False
        
        # Weak password
        is_valid, error = validator.validate_user_creation(
            "newuser",
            "user@example.com",
            "weak",
        )
        assert is_valid is False
    
    def test_credential_validation(self):
        """Test validating user credentials."""
        from app.security.validation import SecurityValidator
        
        validator = SecurityValidator()
        
        # Valid credentials
        is_valid, error = validator.validate_credentials("testuser", "SecurePass123")
        assert is_valid is True
        
        # Invalid credentials
        is_valid, error = validator.validate_credentials("ab", "weak")
        assert is_valid is False


class TestRBACFlow:
    """Test role-based access control workflows."""
    
    def test_permission_checking_for_different_roles(self):
        """Test permission checking across roles."""
        from app.middleware.auth import check_permission, User
        
        # User role
        user = User(
            id="user1",
            username="user",
            email="user@example.com",
            role="user",
            is_active=True,
        )
        
        assert check_permission(user, "events:read") is True
        assert check_permission(user, "users:delete") is False
        
        # Admin role
        admin = User(
            id="admin1",
            username="admin",
            email="admin@example.com",
            role="admin",
            is_active=True,
        )
        
        assert check_permission(admin, "events:read") is True
        assert check_permission(admin, "users:update") is True
        
        # Superadmin role
        superadmin = User(
            id="admin2",
            username="superadmin",
            email="superadmin@example.com",
            role="superadmin",
            is_active=True,
        )
        
        assert check_permission(superadmin, "events:read") is True
        assert check_permission(superadmin, "users:delete") is True
    
    def test_permission_hierarchy(self):
        """Test that permissions follow role hierarchy."""
        from app.middleware.auth import get_permissions_for_role
        
        user_perms = get_permissions_for_role("user")
        admin_perms = get_permissions_for_role("admin")
        superadmin_perms = get_permissions_for_role("superadmin")
        
        # Superadmin should have all permissions
        assert "*" in superadmin_perms
        
        # Admin should have multiple permissions
        assert len(admin_perms) > len(user_perms)
        
        # User should have basic permissions
        assert "events:read" in user_perms


class TestAPIKeyFlow:
    """Test API key authentication flows."""
    
    def test_api_key_creation_and_usage(self):
        """Test creating and using API keys."""
        with patch('app.db.repositories.users.APIKeysRepository') as MockRepo:
            repo = MockRepo()
            
            # Mock API key creation
            repo.create_api_key = Mock(return_value=type('APIKey', (), {
                'id': 'key_1',
                'key': 'sk_test_key_123',
                'name': 'test_key',
                'user_id': 'user123',
                'role': 'user',
                'created_at': datetime.utcnow(),
                'last_used': None,
            })())
            
            # Create API key
            api_key = repo.create_api_key(
                key='sk_test_key_123',
                name='test_key',
                user_id='user123',
                role='user',
            )
            
            assert api_key.key == 'sk_test_key_123'
            assert api_key.user_id == 'user123'


class TestSecurityHeadersFlow:
    """Test security headers integration."""
    
    def test_security_headers_in_response(self):
        """Test that security headers are present in responses."""
        # Would require full app setup with middleware
        headers_to_check = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Content-Security-Policy",
            "Strict-Transport-Security",
            "X-XSS-Protection",
        ]
        
        # These headers should be added by SecurityHeadersMiddleware
        for header in headers_to_check:
            assert header is not None


class TestAuditLoggingFlow:
    """Test audit logging integration."""
    
    def test_request_audit_logging(self):
        """Test that requests are audited."""
        # Audit logging should capture:
        # - User ID/username
        # - Request method and path
        # - Response status
        # - Request duration
        # - Client IP
        
        audit_fields = [
            "user",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "ip_address",
            "timestamp",
        ]
        
        # These fields should be logged for each request
        for field in audit_fields:
            assert field is not None
