"""API Keys repository for api_keys table CRUD operations."""

from typing import Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import APIKey

import logging

logger = logging.getLogger(__name__)


class ApiKeysRepository:
    """Repository for managing API keys."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        api_key_id: str,
        key_hash: str,
        source_id: str,
        source_type: str,
        metadata: Optional[dict] = None,
    ) -> ApiKey:
        """Create a new API key."""
        logger.debug(f"Creating API key {api_key_id}")
        
        api_key = ApiKey(
            api_key_id=api_key_id,
            key_hash=key_hash,
            source_id=source_id,
            source_type=source_type,
            active=True,
            metadata=metadata or {},
        )
        
        self.db.add(api_key)
        await self.db.flush()
        
        return api_key
    
    async def get_by_hash(self, key_hash: str) -> Optional[ApiKey]:
        """Get API key by hash."""
        logger.debug(f"Looking up API key by hash")
        
        stmt = select(ApiKey).where(
            (ApiKey.key_hash == key_hash) & (ApiKey.active == True)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_id(self, api_key_id: str) -> Optional[ApiKey]:
        """Get API key by ID."""
        logger.debug(f"Retrieving API key {api_key_id}")
        
        stmt = select(ApiKey).where(ApiKey.api_key_id == api_key_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_last_used(self, api_key_id: str) -> Optional[ApiKey]:
        """Update last_used timestamp."""
        logger.debug(f"Updating last_used for API key {api_key_id}")
        
        api_key = await self.get_by_id(api_key_id)
        if not api_key:
            return None
        
        api_key.last_used = datetime.utcnow()
        await self.db.flush()
        
        return api_key
    
    async def deactivate(self, api_key_id: str) -> Optional[ApiKey]:
        """Deactivate an API key."""
        logger.debug(f"Deactivating API key {api_key_id}")
        
        api_key = await self.get_by_id(api_key_id)
        if not api_key:
            return None
        
        api_key.active = False
        await self.db.flush()
        
        return api_key
    
    async def activate(self, api_key_id: str) -> Optional[ApiKey]:
        """Activate an API key."""
        logger.debug(f"Activating API key {api_key_id}")
        
        api_key = await self.get_by_id(api_key_id)
        if not api_key:
            return None
        
        api_key.active = True
        await self.db.flush()
        
        return api_key
