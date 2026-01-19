"""Events repository for raw_events table CRUD operations."""

from typing import Optional, List
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RawEvent

import logging

logger = logging.getLogger(__name__)


class EventsRepository:
    """Repository for managing raw events."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        event_id: str,
        source_type: str,
        source_id: str,
        event_type: str,
        payload: dict,
        metadata: Optional[dict] = None,
    ) -> RawEvent:
        """Create a new raw event."""
        logger.debug(f"Creating event {event_id}")
        
        event = RawEvent(
            event_id=event_id,
            source_type=source_type,
            source_id=source_id,
            event_type=event_type,
            payload=payload,
            metadata=metadata or {},
        )
        
        self.db.add(event)
        await self.db.flush()
        
        return event
    
    async def get_by_id(self, event_id: str) -> Optional[RawEvent]:
        """Get event by ID."""
        logger.debug(f"Retrieving event {event_id}")
        
        stmt = select(RawEvent).where(RawEvent.event_id == event_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_by_source(
        self,
        source_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[RawEvent]:
        """List events by source ID."""
        logger.debug(f"Listing events for source {source_id}")
        
        stmt = (
            select(RawEvent)
            .where(RawEvent.source_id == source_id)
            .order_by(RawEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def list_recent(
        self,
        limit: int = 100,
    ) -> List[RawEvent]:
        """List recent events."""
        logger.debug(f"Listing recent events (limit={limit})")
        
        stmt = (
            select(RawEvent)
            .order_by(RawEvent.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def count_by_source(self, source_id: str) -> int:
        """Count events by source."""
        logger.debug(f"Counting events for source {source_id}")
        
        stmt = select(RawEvent).where(RawEvent.source_id == source_id)
        result = await self.db.execute(stmt)
        return len(result.scalars().all())
