"""Alerts service for managing alerts and decisions."""

from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.repositories import AlertsRepository
import uuid

import logging

logger = logging.getLogger(__name__)


class AlertService:
    """Service for managing alerts and decisions."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.alerts_repo = AlertsRepository(db)
    
    async def create_alert(
        self,
        signal_id: str,
        decision: str,
        reason: Optional[str] = None,
        priority: int = 5,
    ) -> dict:
        """Create an alert based on detection signal."""
        logger.info(f"Creating alert for signal {signal_id} with decision {decision}")
        
        alert_id = str(uuid.uuid4())
        
        try:
            alert = await self.alerts_repo.create(
                alert_id=alert_id,
                signal_id=signal_id,
                decision=decision,
                status="active",
                reason=reason,
                priority=priority,
            )
            await self.db.commit()
            
            logger.info(f"Alert {alert_id} created successfully")
            return {
                "alert_id": alert_id,
                "signal_id": signal_id,
                "decision": decision,
                "status": "active",
                "priority": priority,
            }
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create alert for signal {signal_id}: {str(e)}")
            raise
    
    async def get_alert(self, alert_id: str) -> Optional[dict]:
        """Retrieve alert by ID."""
        logger.info(f"Retrieving alert {alert_id}")
        
        try:
            alert = await self.alerts_repo.get_by_id(alert_id)
            
            if not alert:
                logger.warning(f"Alert {alert_id} not found")
                return None
            
            return {
                "alert_id": alert.alert_id,
                "signal_id": alert.signal_id,
                "decision": alert.decision,
                "status": alert.status,
                "reason": alert.reason,
                "priority": alert.priority,
                "created_at": alert.created_at.isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to retrieve alert {alert_id}: {str(e)}")
            raise
    
    async def get_alert_for_signal(self, signal_id: str) -> Optional[dict]:
        """Get alert for a detection signal."""
        logger.info(f"Retrieving alert for signal {signal_id}")
        
        try:
            alert = await self.alerts_repo.get_by_signal(signal_id)
            
            if not alert:
                logger.warning(f"No alert found for signal {signal_id}")
                return None
            
            return {
                "alert_id": alert.alert_id,
                "decision": alert.decision,
                "status": alert.status,
            }
        except Exception as e:
            logger.error(f"Failed to retrieve alert for signal {signal_id}: {str(e)}")
            raise
    
    async def list_active_alerts(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """List active alerts."""
        logger.info(f"Listing active alerts")
        
        try:
            alerts = await self.alerts_repo.list_active(limit=limit, offset=offset)
            
            return [
                {
                    "alert_id": alert.alert_id,
                    "decision": alert.decision,
                    "priority": alert.priority,
                    "created_at": alert.created_at.isoformat(),
                }
                for alert in alerts
            ]
        except Exception as e:
            logger.error(f"Failed to list active alerts: {str(e)}")
            raise
    
    async def update_alert_status(
        self,
        alert_id: str,
        status: str,
    ) -> Optional[dict]:
        """Update alert status."""
        logger.info(f"Updating alert {alert_id} status to {status}")
        
        try:
            alert = await self.alerts_repo.update_status(alert_id, status)
            await self.db.commit()
            
            if not alert:
                logger.warning(f"Alert {alert_id} not found for update")
                return None
            
            return {
                "alert_id": alert.alert_id,
                "status": alert.status,
            }
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update alert {alert_id}: {str(e)}")
            raise
    
    async def get_alert_stats(self) -> dict:
        """Get alert statistics."""
        logger.info("Retrieving alert statistics")
        
        try:
            allow_count = await self.alerts_repo.count_by_decision("ALLOW")
            warn_count = await self.alerts_repo.count_by_decision("WARN")
            block_count = await self.alerts_repo.count_by_decision("BLOCK")
            active_count = await self.alerts_repo.count_by_status("active")
            resolved_count = await self.alerts_repo.count_by_status("resolved")
            
            return {
                "allow": allow_count,
                "warn": warn_count,
                "block": block_count,
                "active": active_count,
                "resolved": resolved_count,
            }
        except Exception as e:
            logger.error(f"Failed to get alert statistics: {str(e)}")
            raise
