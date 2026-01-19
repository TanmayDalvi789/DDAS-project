"""Signals repository for detection_signals table CRUD operations."""

from typing import Optional, List
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DetectionSignal

import logging

logger = logging.getLogger(__name__)


class SignalsRepository:
    """Repository for managing detection signals."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        signal_id: str,
        event_id: str,
        detection_type: str,
        status: str,
        config: Optional[dict] = None,
    ) -> DetectionSignal:
        """Create a new detection signal."""
        logger.debug(f"Creating signal {signal_id}")
        
        signal = DetectionSignal(
            signal_id=signal_id,
            event_id=event_id,
            detection_type=detection_type,
            status=status,
            config=config or {},
        )
        
        self.db.add(signal)
        await self.db.flush()
        
        return signal
    
    async def get_by_id(self, signal_id: str) -> Optional[DetectionSignal]:
        """Get signal by ID."""
        logger.debug(f"Retrieving signal {signal_id}")
        
        stmt = select(DetectionSignal).where(DetectionSignal.signal_id == signal_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_by_event(self, event_id: str) -> List[DetectionSignal]:
        """List all signals for an event."""
        logger.debug(f"Listing signals for event {event_id}")
        
        stmt = (
            select(DetectionSignal)
            .where(DetectionSignal.event_id == event_id)
            .order_by(DetectionSignal.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def update_status(
        self,
        signal_id: str,
        status: str,
        confidence: Optional[float] = None,
        result: Optional[dict] = None,
    ) -> Optional[DetectionSignal]:
        """Update signal status and optional result."""
        logger.debug(f"Updating signal {signal_id} status to {status}")
        
        signal = await self.get_by_id(signal_id)
        if not signal:
            return None
        
        signal.status = status
        signal.updated_at = datetime.utcnow()
        
        if confidence is not None:
            signal.confidence = confidence
        
        if result is not None:
            signal.result = result
        
        await self.db.flush()
        return signal
    
    async def list_pending(self, limit: int = 100) -> List[DetectionSignal]:
        """List pending signals."""
        logger.debug(f"Listing pending signals (limit={limit})")
        
        stmt = (
            select(DetectionSignal)
            .where(DetectionSignal.status.in_(["pending", "processing"]))
            .order_by(DetectionSignal.created_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def count_by_status(self, status: str) -> int:
        """Count signals by status."""
        logger.debug(f"Counting signals with status {status}")
        
        stmt = select(DetectionSignal).where(DetectionSignal.status == status)
        result = await self.db.execute(stmt)
        return len(result.scalars().all())
