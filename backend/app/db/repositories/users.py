"""User repository for database operations."""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session
from app.models.user import User, APIKey, UserRole
from app.middleware.auth import hash_password, verify_password


class UsersRepository:
    """Repository for user database operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        role: UserRole = UserRole.USER,
    ) -> User:
        """Create a new user."""
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=hash_password(password),
            role=role,
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.session.query(User).filter(User.id == user_id).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.session.query(User).filter(User.username == username).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.session.query(User).filter(User.email == email).first()
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password."""
        user = self.get_user_by_username(username)
        if not user or not user.is_active:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        return user
    
    def update_last_login(self, user_id: str) -> Optional[User]:
        """Update user's last login time."""
        user = self.get_user_by_id(user_id)
        if user:
            user.last_login = datetime.utcnow()
            self.session.commit()
            self.session.refresh(user)
        return user
    
    def update_user_role(self, user_id: str, role: UserRole) -> Optional[User]:
        """Update user's role."""
        user = self.get_user_by_id(user_id)
        if user:
            user.role = role
            user.updated_at = datetime.utcnow()
            self.session.commit()
            self.session.refresh(user)
        return user
    
    def deactivate_user(self, user_id: str) -> Optional[User]:
        """Deactivate a user."""
        user = self.get_user_by_id(user_id)
        if user:
            user.is_active = False
            user.updated_at = datetime.utcnow()
            self.session.commit()
            self.session.refresh(user)
        return user
    
    def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List all users."""
        return self.session.query(User).offset(skip).limit(limit).all()
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        user = self.get_user_by_id(user_id)
        if user:
            self.session.delete(user)
            self.session.commit()
            return True
        return False


class APIKeysRepository:
    """Repository for API key database operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_api_key(
        self,
        key: str,
        name: str,
        user_id: str,
        role: UserRole = UserRole.USER,
    ) -> APIKey:
        """Create a new API key."""
        api_key = APIKey(
            id=str(uuid.uuid4()),
            key=key,
            name=name,
            user_id=user_id,
            role=role,
        )
        self.session.add(api_key)
        self.session.commit()
        self.session.refresh(api_key)
        return api_key
    
    def get_api_key(self, key: str) -> Optional[APIKey]:
        """Get API key by key string."""
        return self.session.query(APIKey).filter(APIKey.key == key).first()
    
    def get_api_key_by_id(self, key_id: str) -> Optional[APIKey]:
        """Get API key by ID."""
        return self.session.query(APIKey).filter(APIKey.id == key_id).first()
    
    def get_user_api_keys(self, user_id: str) -> List[APIKey]:
        """Get all API keys for a user."""
        return self.session.query(APIKey).filter(APIKey.user_id == user_id).all()
    
    def update_last_used(self, key: str) -> Optional[APIKey]:
        """Update API key's last used time."""
        api_key = self.get_api_key(key)
        if api_key:
            api_key.last_used = datetime.utcnow()
            self.session.commit()
            self.session.refresh(api_key)
        return api_key
    
    def deactivate_api_key(self, key_id: str) -> Optional[APIKey]:
        """Deactivate an API key."""
        api_key = self.get_api_key_by_id(key_id)
        if api_key:
            api_key.is_active = False
            self.session.commit()
            self.session.refresh(api_key)
        return api_key
    
    def delete_api_key(self, key_id: str) -> bool:
        """Delete an API key."""
        api_key = self.get_api_key_by_id(key_id)
        if api_key:
            self.session.delete(api_key)
            self.session.commit()
            return True
        return False
    
    def list_api_keys(self, skip: int = 0, limit: int = 100) -> List[APIKey]:
        """List all API keys."""
        return self.session.query(APIKey).offset(skip).limit(limit).all()
