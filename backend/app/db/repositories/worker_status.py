"""Worker Status repository for worker_status table CRUD operations."""

from typing import Optional, List
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import WorkerStatus

import logging

logger = logging.getLogger(__name__)


class WorkerStatusRepository:
    """Repository for managing worker status."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def upsert(
        self,
        worker_id: str,
        status: str,
        queue_size: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> WorkerStatus:
        """Create or update worker status."""
        logger.debug(f"Upserting status for worker {worker_id}")
        
        existing = await self.get_by_id(worker_id)
        
        if existing:
            existing.status = status
            existing.last_heartbeat = datetime.utcnow()
            if queue_size is not None:
                existing.queue_size = queue_size
            if metadata is not None:
                existing.metadata = metadata
            await self.db.flush()
            return existing
        
        worker = WorkerStatus(
            worker_id=worker_id,
            status=status,
            queue_size=queue_size,
            metadata=metadata or {},
        )
        
        self.db.add(worker)
        await self.db.flush()
        
        return worker
    
    async def get_by_id(self, worker_id: str) -> Optional[WorkerStatus]:
        """Get worker status by ID."""
        logger.debug(f"Retrieving status for worker {worker_id}")
        
        stmt = select(WorkerStatus).where(WorkerStatus.worker_id == worker_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_all(self) -> List[WorkerStatus]:
        """List all worker statuses."""
        logger.debug(f"Listing all worker statuses")
        
        stmt = select(WorkerStatus).order_by(WorkerStatus.worker_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def increment_tasks(self, worker_id: str, count: int = 1) -> Optional[WorkerStatus]:
        """Increment task count."""
        logger.debug(f"Incrementing task count for worker {worker_id}")
        
        worker = await self.get_by_id(worker_id)
        if not worker:
            return None
        
        worker.tasks_processed += count
        worker.updated_at = datetime.utcnow()
        await self.db.flush()
        
        return worker
    
    async def increment_errors(self, worker_id: str, count: int = 1) -> Optional[WorkerStatus]:
        """Increment error count."""
        logger.debug(f"Incrementing error count for worker {worker_id}")
        
        worker = await self.get_by_id(worker_id)
        if not worker:
            return None
        
        worker.errors += count
        worker.updated_at = datetime.utcnow()
        await self.db.flush()
        
        return worker
    
    async def update_status(self, worker_id: str, status: str) -> Optional[WorkerStatus]:
        """Update worker status."""
        logger.debug(f"Updating worker {worker_id} status to {status}")
        
        worker = await self.get_by_id(worker_id)
        if not worker:
            return None
        
        worker.status = status
        worker.updated_at = datetime.utcnow()
        await self.db.flush()
        
        return worker
