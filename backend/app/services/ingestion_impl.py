"""Ingestion service for handling raw events."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.models import RawEventRequest
from app.db.repositories import EventsRepository
import uuid

import logging

logger = logging.getLogger(__name__)


class IngestService:
    """Service for ingesting raw events."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.events_repo = EventsRepository(db)
    
    async def store_raw_event(self, event_id: str, request: RawEventRequest) -> dict:
        """Store raw event in database."""
        logger.info(f"Storing raw event {event_id}")
        
        try:
            event = await self.events_repo.create(
                event_id=event_id,
                source_type=request.source_type,
                source_id=request.source_id,
                event_type=request.event_type,
                payload=request.payload,
                metadata=request.metadata,
            )
            await self.db.commit()
            
            logger.info(f"Event {event_id} stored successfully")
            return {
                "event_id": event_id,
                "status": "stored",
            }
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to store event {event_id}: {str(e)}")
            raise
    
    async def get_event(self, event_id: str) -> Optional[dict]:
        """Retrieve event by ID."""
        logger.info(f"Retrieving event {event_id}")
        
        try:
            event = await self.events_repo.get_by_id(event_id)
            
            if not event:
                logger.warning(f"Event {event_id} not found")
                return None
            
            return {
                "event_id": event.event_id,
                "source_id": event.source_id,
                "source_type": event.source_type,
                "event_type": event.event_type,
                "payload": event.payload,
                "created_at": event.created_at.isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to retrieve event {event_id}: {str(e)}")
            raise
    
    async def list_events_by_source(
        self,
        source_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """List events by source ID with pagination."""
        logger.info(f"Listing events for source {source_id}")
        
        try:
            events = await self.events_repo.list_by_source(
                source_id=source_id,
                limit=limit,
                offset=offset,
            )
            
            total_count = await self.events_repo.count_by_source(source_id)
            
            return {
                "events": [
                    {
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "created_at": event.created_at.isoformat(),
                    }
                    for event in events
                ],
                "total": total_count,
                "limit": limit,
                "offset": offset,
            }
        except Exception as e:
            logger.error(f"Failed to list events for source {source_id}: {str(e)}")
            raise
