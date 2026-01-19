"""Authentication and authorization middleware with OAuth2, JWT, and RBAC support.

REFACTORED: JWT logic moved to app.security.jwt for better separation of concerns.
This module now handles:
- Middleware dispatch and validation
- Dependency injection for auth checks
- API key validation
- Re-exports from security.jwt for backward compatibility
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from functools import lru_cache

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, APIKeyHeader

# Try importing HTTPAuthCredentials, fallback if not available
try:
    from fastapi.security import HTTPAuthCredentials
except ImportError:
    from typing import NamedTuple
    class HTTPAuthCredentials(NamedTuple):
        scheme: str
        credentials: str

from passlib.context import CryptContext
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Import JWT functions from security module
from app.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    TokenData,
    get_permissions_for_role,
    check_permission,
)

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer scheme
bearer_scheme = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# ============================================================================
# DATA MODELS
# ============================================================================

class User(BaseModel):
    """User model."""
    id: str
    username: str
    email: str
    role: str = "user"  # user, admin, superadmin
    permissions: List[str] = []
    is_active: bool = True
    last_login: Optional[datetime] = None


class APIKey(BaseModel):
    """API Key model."""
    key: str
    name: str
    user_id: str
    role: str = "user"
    permissions: List[str] = []
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None


# ============================================================================
# PASSWORD HASHING
# ============================================================================

def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password."""
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# API KEY VALIDATION
# ============================================================================

@lru_cache(maxsize=1000)
def validate_api_key(key: str) -> Optional[APIKey]:
    """Validate API key (with caching)."""
    # In production, query from database
    # For now, use environment-based keys
    valid_keys = {
        "test-key": APIKey(
            key="test-key",
            name="Test Key",
            user_id="test-user",
            role="admin",
            permissions=get_permissions_for_role("admin"),
        ),
    }
    
    key_obj = valid_keys.get(key)
    
    if key_obj and key_obj.is_active:
        # Update last_used timestamp (in production, save to database)
        return key_obj
    
    return None


# ============================================================================
# DEPENDENCY FUNCTIONS
# ============================================================================

async def get_current_user(
    credentials: Optional[HTTPAuthCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header),
) -> User:
    """Get current authenticated user from JWT or API Key."""
    
    # Try JWT first
    if credentials:
        token = credentials.credentials
        token_data = decode_token(token)
        
        if token_data:
            return User(
                id=token_data.sub,
                username=token_data.username,
                email=f"{token_data.username}@ddas.local",
                role=token_data.role,
                permissions=token_data.permissions,
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid JWT token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Try API Key
    if api_key:
        key_obj = validate_api_key(api_key)
        
        if key_obj:
            return User(
                id=key_obj.user_id,
                username=key_obj.user_id,
                email=f"{key_obj.user_id}@ddas.local",
                role=key_obj.role,
                permissions=key_obj.permissions,
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    # No auth provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current user and verify admin role."""
    if current_user.role not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def check_permission_dependency(permission: str):
    """Create permission checker dependency."""
    async def _check_permission(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not check_permission(permission, current_user.permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required",
            )
        return current_user
    
    return _check_permission


# ============================================================================
# MIDDLEWARE
# ============================================================================

class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware for API Key validation."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip auth for public endpoints
        public_paths = [
            "/",
            "/health",
            "/api/v1/live",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            "/auth/login",
            "/auth/refresh",
        ]
        
        if request.url.path in public_paths or any(
            request.url.path.startswith(p) for p in public_paths
        ):
            return await call_next(request)
        
        # Endpoints starting with /auth/ are handled separately
        if request.url.path.startswith("/auth/"):
            return await call_next(request)
        
        # Check for API Key or JWT
        api_key = request.headers.get("X-API-Key")
        auth_header = request.headers.get("Authorization")
        
        is_valid = False
        
        # Check API Key
        if api_key:
            key_obj = validate_api_key(api_key)
            is_valid = key_obj is not None
        
        # Check JWT
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            token_data = decode_token(token)
            is_valid = token_data is not None
        
        # If invalid, return 401
        if not is_valid:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "unauthorized",
                    "message": "Authentication required",
                    "status_code": 401,
                },
            )
        
        response = await call_next(request)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline';"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for audit logging."""
    
    async def dispatch(self, request: Request, call_next):
        # Extract user info if available
        api_key = request.headers.get("X-API-Key", "unknown")
        auth_header = request.headers.get("Authorization", "")
        
        user_id = "unknown"
        if api_key and api_key != "unknown":
            key_obj = validate_api_key(api_key)
            if key_obj:
                user_id = key_obj.user_id
        elif auth_header:
            token = auth_header.replace("Bearer ", "")
            token_data = decode_token(token)
            if token_data:
                user_id = token_data.sub
        
        # Log request
        start_time = time.time()
        logger.info(
            f"AUDIT: {request.method} {request.url.path} - User: {user_id} - IP: {request.client.host}"
        )
        
        response = await call_next(request)
        
        # Log response
        duration = time.time() - start_time
        logger.info(
            f"AUDIT: {request.method} {request.url.path} - Status: {response.status_code} - Duration: {duration:.3f}s"
        )
        
        return response

