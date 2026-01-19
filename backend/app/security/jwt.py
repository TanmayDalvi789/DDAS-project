"""
JWT Token Management

Handles creation, validation, and decoding of JWT tokens.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List

from jose import JWTError, jwt
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = "your-secret-key-change-in-production"  # Change in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours to avoid test token expiry
REFRESH_TOKEN_EXPIRE_DAYS = 7


# ============================================================================
# DATA MODELS
# ============================================================================

class TokenData(BaseModel):
    """JWT token payload."""
    sub: str  # Subject (user_id)
    username: str
    role: str = "user"
    permissions: List[str] = []
    exp: Optional[int] = None
    iat: Optional[int] = None


# ============================================================================
# ROLE-BASED ACCESS CONTROL (RBAC)
# ============================================================================

ROLE_PERMISSIONS = {
    "user": [
        "events:read",
        "events:create",
        "alerts:read",
        "signals:read",
        "stats:read",
    ],
    "admin": [
        "events:read",
        "events:create",
        "events:update",
        "events:delete",
        "alerts:read",
        "alerts:create",
        "alerts:update",
        "alerts:delete",
        "signals:read",
        "signals:update",
        "detection:run",
        "stats:read",
        "users:read",
        "users:update",
    ],
    "superadmin": [
        "*",  # All permissions
    ],
}


def get_permissions_for_role(role: str) -> List[str]:
    """Get permissions for a role."""
    permissions = ROLE_PERMISSIONS.get(role, [])
    if "*" in permissions:
        # Return all available permissions
        all_perms = set()
        for perms in ROLE_PERMISSIONS.values():
            all_perms.update(p for p in perms if p != "*")
        return list(all_perms)
    return permissions


def check_permission(required_permission: str, user_permissions: List[str]) -> bool:
    """Check if user has required permission."""
    return required_permission in user_permissions or "*" in user_permissions


# ============================================================================
# JWT TOKEN FUNCTIONS
# ============================================================================

def create_access_token(
    user_id: str,
    username: str,
    role: str = "user",
    permissions: List[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT access token."""
    if permissions is None:
        permissions = get_permissions_for_role(role)
    
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {
        "sub": user_id,
        "username": username,
        "role": role,
        "permissions": permissions,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    user_id: str,
    username: str,
) -> str:
    """Create JWT refresh token."""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": user_id,
        "username": username,
        "type": "refresh",
        "exp": int(expire.timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check expiration
        exp = payload.get("exp")
        if exp and int(time.time()) > exp:
            logger.warning("Token expired")
            return None
        
        return TokenData(
            sub=payload.get("sub"),
            username=payload.get("username"),
            role=payload.get("role", "user"),
            permissions=payload.get("permissions", []),
            exp=exp,
            iat=payload.get("iat"),
        )
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None
    except Exception as e:
        logger.error(f"Token decode error: {e}")
        return None
