"""
Redis Queue Configuration
Manages connection to Redis and RQ (Redis Queue) setup for distributed task processing.

This module provides:
- Redis connection pooling
- RQ queue initialization
- Job monitoring utilities
- Graceful shutdown handling
"""

import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

import redis
from redis import Redis
from rq import Queue, Worker, get_current_job
from rq.job import JobStatus

# Handle different RQ versions
try:
    from rq.registry import StartedRegistry, FailedRegistry, FinishedRegistry
except ImportError:
    # Fallback for older RQ versions
    try:
        from rq.registry import FailedRegistry, FinishedRegistry
        StartedRegistry = None
    except ImportError:
        StartedRegistry = None
        FailedRegistry = None
        FinishedRegistry = None

logger = logging.getLogger(__name__)


class RedisQueueManager:
    """
    Manages Redis connection and RQ queue operations.
    
    Responsibilities:
    - Connection pooling to Redis
    - Queue management (create, get, clear)
    - Job monitoring (status, results, errors)
    - Worker management (heartbeat, status)
    - Graceful shutdown
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 50,
    ):
        """
        Initialize Redis connection manager.
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            password: Redis password (optional)
            max_connections: Maximum connection pool size
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections
        
        # Connection pool
        self.connection_pool: Optional[redis.ConnectionPool] = None
        self.redis_conn: Optional[Redis] = None
        
        # Queues
        self.queues: Dict[str, Queue] = {}
        
        logger.info(f"Redis Queue Manager initialized: {host}:{port}")
    
    def connect(self) -> Redis:
        """
        Establish or return cached Redis connection.
        
        Returns:
            Redis connection instance
            
        Raises:
            redis.ConnectionError: If connection fails
        """
        if self.redis_conn is not None:
            return self.redis_conn
        
        try:
            # Create connection pool
            self.connection_pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                decode_responses=True,
            )
            
            # Create connection
            self.redis_conn = redis.Redis(connection_pool=self.connection_pool)
            
            # Test connection
            self.redis_conn.ping()
            logger.info("✓ Redis connection established successfully")
            
            return self.redis_conn
        
        except redis.ConnectionError as e:
            logger.error(f"✗ Failed to connect to Redis: {e}")
            raise
    
    def get_connection(self) -> Redis:
        """
        Get cached Redis connection, connecting if needed.
        
        Returns:
            Redis connection instance
        """
        if self.redis_conn is None:
            self.connect()
        return self.redis_conn
    
    def get_queue(self, name: str = "default", is_async: bool = True) -> Queue:
        """
        Get or create RQ queue.
        
        Args:
            name: Queue name (default, detection, ingest, alerts)
            is_async: Whether queue processes jobs asynchronously
            
        Returns:
            RQ Queue instance
        """
        if name in self.queues:
            return self.queues[name]
        
        try:
            queue = Queue(
                name=name,
                connection=self.get_connection(),
                is_async=is_async,
            )
            self.queues[name] = queue
            logger.info(f"✓ Queue '{name}' created/retrieved")
            return queue
        
        except Exception as e:
            logger.error(f"✗ Failed to get queue '{name}': {e}")
            raise
    
    def enqueue_task(
        self,
        queue_name: str,
        func,
        *args,
        **kwargs
    ) -> str:
        """
        Enqueue a task to specified queue.
        
        Args:
            queue_name: Target queue name
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Job ID
        """
        try:
            queue = self.get_queue(queue_name)
            job = queue.enqueue(func, *args, **kwargs)
            logger.info(f"✓ Task enqueued to '{queue_name}': job_id={job.id}")
            return job.id
        
        except Exception as e:
            logger.error(f"✗ Failed to enqueue task: {e}")
            raise
    
    def get_job_status(self, job_id: str) -> Optional[str]:
        """
        Get status of a job.
        
        Args:
            job_id: Job ID to check
            
        Returns:
            Job status (queued, started, finished, failed, stopped)
        """
        try:
            conn = self.get_connection()
            from rq.job import Job
            job = Job.fetch(job_id, connection=conn)
            return job.get_status()
        except Exception as e:
            logger.warning(f"✗ Failed to get job status for {job_id}: {e}")
            return None
    
    def get_job_result(self, job_id: str) -> Optional[Any]:
        """
        Get result of completed job.
        
        Args:
            job_id: Job ID to fetch result from
            
        Returns:
            Job result or None if not ready
        """
        try:
            conn = self.get_connection()
            from rq.job import Job
            job = Job.fetch(job_id, connection=conn)
            
            if job.is_finished:
                return job.result
            elif job.is_failed:
                logger.warning(f"Job {job_id} failed: {job.exc_info}")
                return None
            else:
                return None
        except Exception as e:
            logger.warning(f"✗ Failed to get job result for {job_id}: {e}")
            return None
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a queued or started job.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.get_connection()
            from rq.job import Job
            job = Job.fetch(job_id, connection=conn)
            job.cancel()
            logger.info(f"✓ Job {job_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to cancel job {job_id}: {e}")
            return False
    
    def get_queue_stats(self, queue_name: str) -> Dict[str, Any]:
        """
        Get statistics for a queue.
        
        Args:
            queue_name: Queue name
            
        Returns:
            Dictionary with queue statistics
        """
        try:
            queue = self.get_queue(queue_name)
            conn = self.get_connection()
            
            # Get job counts by status
            stats = {
                "queue": queue_name,
                "queued": len(queue),
                "started": 0,
                "finished": 0,
                "failed": 0,
                "total": len(queue),
            }
            
            # Add registry counts if available
            if StartedRegistry is not None:
                try:
                    started_registry = StartedRegistry(queue_name, connection=conn)
                    stats["started"] = len(started_registry)
                    stats["total"] += stats["started"]
                except Exception:
                    pass
            
            if FinishedRegistry is not None:
                try:
                    finished_registry = FinishedRegistry(queue_name, connection=conn)
                    stats["finished"] = len(finished_registry)
                    stats["total"] += stats["finished"]
                except Exception:
                    pass
            
            if FailedRegistry is not None:
                try:
                    failed_registry = FailedRegistry(queue_name, connection=conn)
                    stats["failed"] = len(failed_registry)
                    stats["total"] += stats["failed"]
                except Exception:
                    pass
            
            return stats
        except Exception as e:
            logger.error(f"✗ Failed to get queue stats for '{queue_name}': {e}")
            return {"error": str(e)}
    
    def clear_queue(self, queue_name: str) -> int:
        """
        Clear all jobs from a queue (careful!).
        
        Args:
            queue_name: Queue to clear
            
        Returns:
            Number of jobs cleared
        """
        try:
            queue = self.get_queue(queue_name)
            count = queue.empty()
            logger.warning(f"✓ Queue '{queue_name}' cleared ({count} jobs)")
            return count
        except Exception as e:
            logger.error(f"✗ Failed to clear queue '{queue_name}': {e}")
            return 0
    
    def cleanup_old_jobs(self, queue_name: str, days: int = 7) -> int:
        """
        Clean up old finished jobs from registry.
        
        Args:
            queue_name: Queue to clean
            days: Only keep jobs from last N days
            
        Returns:
            Number of jobs deleted
        """
        try:
            conn = self.get_connection()
            finished_registry = FinishedRegistry(queue_name, connection=conn)
            failed_registry = FailedRegistry(queue_name, connection=conn)
            
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            # Clean finished jobs
            cleaned = 0
            for job_id in finished_registry.get_job_ids():
                from rq.job import Job
                job = Job.fetch(job_id, connection=conn)
                if job.ended_at and job.ended_at < cutoff:
                    job.delete()
                    cleaned += 1
            
            # Clean failed jobs
            for job_id in failed_registry.get_job_ids():
                from rq.job import Job
                job = Job.fetch(job_id, connection=conn)
                if job.ended_at and job.ended_at < cutoff:
                    job.delete()
                    cleaned += 1
            
            logger.info(f"✓ Cleaned {cleaned} old jobs from '{queue_name}'")
            return cleaned
        
        except Exception as e:
            logger.error(f"✗ Failed to cleanup old jobs: {e}")
            return 0
    
    def shutdown(self):
        """Close Redis connection gracefully."""
        try:
            if self.redis_conn:
                self.redis_conn.close()
                logger.info("✓ Redis connection closed")
            if self.connection_pool:
                self.connection_pool.disconnect()
                logger.info("✓ Redis connection pool closed")
        except Exception as e:
            logger.error(f"✗ Error during shutdown: {e}")


# Global instance
_queue_manager: Optional[RedisQueueManager] = None


def get_queue_manager(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None,
) -> RedisQueueManager:
    """
    Get or create global queue manager instance.
    
    Args:
        host: Redis host
        port: Redis port
        db: Redis database number
        password: Redis password
        
    Returns:
        RedisQueueManager instance
    """
    global _queue_manager
    
    if _queue_manager is None:
        _queue_manager = RedisQueueManager(
            host=host,
            port=port,
            db=db,
            password=password,
        )
    
    return _queue_manager


def get_job() -> Optional[object]:
    """
    Get current RQ job (only works within worker context).
    
    Returns:
        Current job object or None if not in worker context
    """
    return get_current_job()
