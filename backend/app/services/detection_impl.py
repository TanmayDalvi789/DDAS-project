"""Detection service for orchestrating detection operations."""

from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.repositories import SignalsRepository
import uuid

import logging

logger = logging.getLogger(__name__)


class DetectionService:
    """Service for managing detection signals and orchestration."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.signals_repo = SignalsRepository(db)
    
    async def create_signal(
        self,
        event_id: str,
        detection_type: str,
        config: Optional[dict] = None,
    ) -> dict:
        """Create a detection signal record."""
        logger.info(f"Creating detection signal for event {event_id}")
        
        signal_id = str(uuid.uuid4())
        
        try:
            signal = await self.signals_repo.create(
                signal_id=signal_id,
                event_id=event_id,
                detection_type=detection_type,
                status="pending",
                config=config,
            )
            await self.db.commit()
            
            logger.info(f"Signal {signal_id} created successfully")
            return {
                "signal_id": signal_id,
                "event_id": event_id,
                "status": "pending",
            }
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create signal for event {event_id}: {str(e)}")
            raise
    
    async def get_signal(self, signal_id: str) -> Optional[dict]:
        """Retrieve signal by ID."""
        logger.info(f"Retrieving signal {signal_id}")
        
        try:
            signal = await self.signals_repo.get_by_id(signal_id)
            
            if not signal:
                logger.warning(f"Signal {signal_id} not found")
                return None
            
            return {
                "signal_id": signal.signal_id,
                "event_id": signal.event_id,
                "detection_type": signal.detection_type,
                "status": signal.status,
                "confidence": signal.confidence,
                "result": signal.result,
                "created_at": signal.created_at.isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to retrieve signal {signal_id}: {str(e)}")
            raise
    
    async def list_signals_for_event(self, event_id: str) -> List[dict]:
        """List all signals for an event."""
        logger.info(f"Listing signals for event {event_id}")
        
        try:
            signals = await self.signals_repo.list_by_event(event_id)
            
            return [
                {
                    "signal_id": signal.signal_id,
                    "detection_type": signal.detection_type,
                    "status": signal.status,
                    "confidence": signal.confidence,
                }
                for signal in signals
            ]
        except Exception as e:
            logger.error(f"Failed to list signals for event {event_id}: {str(e)}")
            raise
    
    async def update_signal_status(
        self,
        signal_id: str,
        status: str,
        confidence: Optional[float] = None,
        result: Optional[dict] = None,
    ) -> Optional[dict]:
        """Update signal status with detection result."""
        logger.info(f"Updating signal {signal_id} status to {status}")
        
        try:
            signal = await self.signals_repo.update_status(
                signal_id=signal_id,
                status=status,
                confidence=confidence,
                result=result,
            )
            await self.db.commit()
            
            if not signal:
                logger.warning(f"Signal {signal_id} not found for update")
                return None
            
            return {
                "signal_id": signal.signal_id,
                "status": signal.status,
                "confidence": signal.confidence,
            }
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update signal {signal_id}: {str(e)}")
            raise
    
    async def get_pipeline_stats(self) -> dict:
        """Get pipeline statistics."""
        logger.info("Retrieving pipeline statistics")
        
        try:
            pending = await self.signals_repo.count_by_status("pending")
            processing = await self.signals_repo.count_by_status("processing")
            completed = await self.signals_repo.count_by_status("completed")
            failed = await self.signals_repo.count_by_status("failed")
            
            return {
                "pending": pending,
                "processing": processing,
                "completed": completed,
                "failed": failed,
                "total": pending + processing + completed + failed,
            }
        except Exception as e:
            logger.error(f"Failed to get pipeline statistics: {str(e)}")
            raise
