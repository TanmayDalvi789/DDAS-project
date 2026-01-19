"""Alerts repository for alerts table CRUD operations."""

from typing import Optional, List
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert

import logging

logger = logging.getLogger(__name__)


class AlertsRepository:
    """Repository for managing alerts."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(
        self,
        alert_id: str,
        signal_id: str,
        decision: str,
        status: str = "active",
        reason: Optional[str] = None,
        priority: int = 5,
    ) -> Alert:
        """Create a new alert."""
        logger.debug(f"Creating alert {alert_id}")
        
        alert = Alert(
            alert_id=alert_id,
            signal_id=signal_id,
            decision=decision,
            status=status,
            reason=reason,
            priority=priority,
        )
        
        self.db.add(alert)
        await self.db.flush()
        
        return alert
    
    async def get_by_id(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID."""
        logger.debug(f"Retrieving alert {alert_id}")
        
        stmt = select(Alert).where(Alert.alert_id == alert_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_signal(self, signal_id: str) -> Optional[Alert]:
        """Get alert for a signal."""
        logger.debug(f"Retrieving alert for signal {signal_id}")
        
        stmt = select(Alert).where(Alert.signal_id == signal_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_active(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Alert]:
        """List active alerts."""
        logger.debug(f"Listing active alerts")
        
        stmt = (
            select(Alert)
            .where(Alert.status == "active")
            .order_by(Alert.priority.desc(), Alert.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def update_status(
        self,
        alert_id: str,
        status: str,
    ) -> Optional[Alert]:
        """Update alert status."""
        logger.debug(f"Updating alert {alert_id} status to {status}")
        
        alert = await self.get_by_id(alert_id)
        if not alert:
            return None
        
        alert.status = status
        alert.updated_at = datetime.utcnow()
        
        await self.db.flush()
        return alert
    
    async def count_by_decision(self, decision: str) -> int:
        """Count alerts by decision."""
        logger.debug(f"Counting alerts with decision {decision}")
        
        stmt = select(Alert).where(Alert.decision == decision)
        result = await self.db.execute(stmt)
        return len(result.scalars().all())
    
    async def count_by_status(self, status: str) -> int:
        """Count alerts by status."""
        logger.debug(f"Counting alerts with status {status}")
        
        stmt = select(Alert).where(Alert.status == status)
        result = await self.db.execute(stmt)
        return len(result.scalars().all())
