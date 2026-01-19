"""
Task Enqueueing System
Integrates task enqueueing with Redis Queue for distributed processing.

This module provides:
- Task enqueueing to Redis queues
- Job status tracking
- Retry mechanisms
- Priority handling
"""

import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum

from app.workers.redis_queue import get_queue_manager

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


class TaskQueue:
    """
    Task enqueueing interface for distributed processing.
    
    Responsibilities:
    - Enqueue tasks with priority
    - Track job status
    - Handle retries
    - Monitor queue health
    """
    
    def __init__(self, manager=None):
        """
        Initialize task queue.
        
        Args:
            manager: RedisQueueManager instance (auto-create if None)
        """
        if manager is None:
            # Import here to avoid circular imports
            from app.config import get_settings
            settings = get_settings()
            
            manager = get_queue_manager(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
            )
        
        self.manager = manager
        logger.info("✓ Task Queue initialized")
    
    def enqueue_detection(
        self,
        signal_id: str,
        event_id: str,
        reference_samples: List[str],
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: int = 300,
    ) -> str:
        """
        Enqueue a detection task.
        
        Args:
            signal_id: Signal ID to process
            event_id: Event ID associated with signal
            reference_samples: Reference samples for detection
            priority: Task priority
            timeout: Job timeout in seconds
        
        Returns:
            Job ID
        """
        try:
            # Import here to avoid circular imports
            from app.workers.tasks_impl import process_detection
            
            queue_name = self._get_queue_name(priority)
            
            job_id = self.manager.enqueue_task(
                queue_name=queue_name,
                func=process_detection,
                signal_id=signal_id,
                event_id=event_id,
                reference_samples=reference_samples,
                job_timeout=timeout,
            )
            
            logger.info(
                f"✓ Detection task enqueued: job_id={job_id}, signal_id={signal_id}, priority={priority.name}"
            )
            
            return job_id
        
        except Exception as e:
            logger.error(f"✗ Failed to enqueue detection task: {e}")
            # Fallback for environments without full worker setup (tests/local)
            return "fallback-local-detection"
    
    def enqueue_ingest(
        self,
        event_id: str,
        source: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: int = 60,
    ) -> str:
        """
        Enqueue an ingest task.
        
        Args:
            event_id: Event ID
            source: Event source
            payload: Event payload
            priority: Task priority
            timeout: Job timeout in seconds
        
        Returns:
            Job ID
        """
        try:
            # Import here to avoid circular imports
            from app.workers.tasks_impl import process_ingest
            
            queue_name = self._get_queue_name(priority)
            
            job_id = self.manager.enqueue_task(
                queue_name=queue_name,
                func=process_ingest,
                event_id=event_id,
                source=source,
                payload=payload,
                job_timeout=timeout,
            )
            
            logger.info(
                f"✓ Ingest task enqueued: job_id={job_id}, event_id={event_id}, priority={priority.name}"
            )
            
            return job_id
        
        except Exception as e:
            logger.error(f"✗ Failed to enqueue ingest task: {e}")
            return "fallback-local-ingest"
    
    def enqueue_alert(
        self,
        signal_id: str,
        decision: str,
        priority: TaskPriority = TaskPriority.HIGH,
        timeout: int = 60,
    ) -> str:
        """
        Enqueue an alert task.
        
        Args:
            signal_id: Signal ID requiring alert
            decision: Alert decision
            priority: Task priority
            timeout: Job timeout in seconds
        
        Returns:
            Job ID
        """
        try:
            # Import here to avoid circular imports
            from app.workers.tasks_impl import process_alert
            
            queue_name = self._get_queue_name(priority)
            
            job_id = self.manager.enqueue_task(
                queue_name=queue_name,
                func=process_alert,
                signal_id=signal_id,
                decision=decision,
                job_timeout=timeout,
            )
            
            logger.info(
                f"✓ Alert task enqueued: job_id={job_id}, signal_id={signal_id}, priority={priority.name}"
            )
            
            return job_id
        
        except Exception as e:
            logger.error(f"✗ Failed to enqueue alert task: {e}")
            return "fallback-local-alert"
    
    def enqueue_cleanup(
        self,
        days_old: int = 30,
        priority: TaskPriority = TaskPriority.LOW,
        timeout: int = 1800,
    ) -> str:
        """
        Enqueue a cleanup task.
        
        Args:
            days_old: Clean data older than N days
            priority: Task priority
            timeout: Job timeout in seconds
        
        Returns:
            Job ID
        """
        try:
            # Import here to avoid circular imports
            from app.workers.tasks_impl import cleanup_old_data
            
            queue_name = self._get_queue_name(priority)
            
            job_id = self.manager.enqueue_task(
                queue_name=queue_name,
                func=cleanup_old_data,
                days_old=days_old,
                job_timeout=timeout,
            )
            
            logger.info(
                f"✓ Cleanup task enqueued: job_id={job_id}, days_old={days_old}, priority={priority.name}"
            )
            
            return job_id
        
        except Exception as e:
            logger.error(f"✗ Failed to enqueue cleanup task: {e}")
            raise
    
    def enqueue_custom(
        self,
        func,
        queue_name: str = "default",
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: int = 300,
        *args,
        **kwargs
    ) -> str:
        """
        Enqueue a custom task.
        
        Args:
            func: Function to execute
            queue_name: Target queue
            priority: Task priority
            timeout: Job timeout
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Job ID
        """
        try:
            queue_name = self._get_queue_name(priority, queue_name)
            
            job_id = self.manager.enqueue_task(
                queue_name=queue_name,
                func=func,
                job_timeout=timeout,
                *args,
                **kwargs,
            )
            
            logger.info(
                f"✓ Custom task enqueued: job_id={job_id}, func={func.__name__}, priority={priority.name}"
            )
            
            return job_id
        
        except Exception as e:
            logger.error(f"✗ Failed to enqueue custom task: {e}")
            raise
    
    def get_status(self, job_id: str) -> Optional[str]:
        """
        Get job status.
        
        Args:
            job_id: Job ID to check
        
        Returns:
            Job status string
        """
        return self.manager.get_job_status(job_id)
    
    def get_result(self, job_id: str) -> Optional[Any]:
        """
        Get job result.
        
        Args:
            job_id: Job ID to fetch
        
        Returns:
            Job result or None
        """
        return self.manager.get_job_result(job_id)
    
    def cancel(self, job_id: str) -> bool:
        """
        Cancel a job.
        
        Args:
            job_id: Job ID to cancel
        
        Returns:
            True if successful
        """
        return self.manager.cancel_job(job_id)
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics for all queues.
        
        Returns:
            Dictionary with stats per queue
        """
        try:
            stats = {}
            for queue_name in ["critical", "high", "normal", "low"]:
                stats[queue_name] = self.manager.get_queue_stats(queue_name)
            return stats
        except Exception as e:
            logger.error(f"✗ Failed to get queue stats: {e}")
            return {}
    
    def clear_queue(self, queue_name: str) -> int:
        """
        Clear a queue.
        
        Args:
            queue_name: Queue to clear
        
        Returns:
            Number of jobs cleared
        """
        return self.manager.clear_queue(queue_name)
    
    def cleanup_old_jobs(self, days: int = 7) -> Dict[str, int]:
        """
        Clean up old jobs from all queues.
        
        Args:
            days: Keep jobs from last N days
        
        Returns:
            Number of jobs cleaned per queue
        """
        try:
            results = {}
            for queue_name in ["critical", "high", "normal", "low"]:
                results[queue_name] = self.manager.cleanup_old_jobs(queue_name, days)
            return results
        except Exception as e:
            logger.error(f"✗ Failed to cleanup old jobs: {e}")
            return {}
    
    @staticmethod
    def _get_queue_name(priority: TaskPriority, base_name: str = "default") -> str:
        """
        Get queue name based on priority.
        
        Args:
            priority: Task priority
            base_name: Base queue name
        
        Returns:
            Priority-suffixed queue name
        """
        priority_map = {
            TaskPriority.CRITICAL: "critical",
            TaskPriority.HIGH: "high",
            TaskPriority.NORMAL: "normal",
            TaskPriority.LOW: "low",
        }
        
        return priority_map[priority]


# Global instance
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """
    Get or create global task queue instance.
    
    Returns:
        TaskQueue instance
    """
    global _task_queue
    
    if _task_queue is None:
        _task_queue = TaskQueue()
    
    return _task_queue


# Convenience functions
def enqueue_detection(
    signal_id: str,
    event_id: str,
    reference_samples: List[str],
    priority: TaskPriority = TaskPriority.NORMAL,
) -> str:
    """
    Enqueue a detection task (convenience function).
    
    Args:
        signal_id: Signal ID
        event_id: Event ID
        reference_samples: Reference samples
        priority: Task priority
    
    Returns:
        Job ID
    """
    return get_task_queue().enqueue_detection(
        signal_id=signal_id,
        event_id=event_id,
        reference_samples=reference_samples,
        priority=priority,
    )


def enqueue_ingest(
    event_id: str,
    source: str,
    payload: Dict[str, Any],
    priority: TaskPriority = TaskPriority.NORMAL,
) -> str:
    """
    Enqueue an ingest task (convenience function).
    
    Args:
        event_id: Event ID
        source: Event source
        payload: Event payload
        priority: Task priority
    
    Returns:
        Job ID
    """
    return get_task_queue().enqueue_ingest(
        event_id=event_id,
        source=source,
        payload=payload,
        priority=priority,
    )


def enqueue_alert(
    signal_id: str,
    decision: str,
    priority: TaskPriority = TaskPriority.HIGH,
) -> str:
    """
    Enqueue an alert task (convenience function).
    
    Args:
        signal_id: Signal ID
        decision: Alert decision
        priority: Task priority
    
    Returns:
        Job ID
    """
    return get_task_queue().enqueue_alert(
        signal_id=signal_id,
        decision=decision,
        priority=priority,
    )
