"""
RQ Worker Process Manager
Manages worker processes for distributed task execution.

This module provides:
- Worker initialization and configuration
- Graceful shutdown and signal handling
- Worker status monitoring
- Multi-worker orchestration
"""

import logging
import signal
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime

from rq import Worker
from redis import Redis

logger = logging.getLogger(__name__)


class WorkerManager:
    """
    Manages RQ worker lifecycle and status.
    
    Responsibilities:
    - Initialize workers
    - Handle graceful shutdown
    - Monitor worker health
    - Log worker events
    """
    
    def __init__(
        self,
        redis_conn: Redis,
        queue_names: List[str] = None,
        worker_name: Optional[str] = None,
        job_timeout: int = 3600,
        result_ttl: int = 500,
        failure_ttl: int = 86400,
        max_jobs: Optional[int] = None,
    ):
        """
        Initialize worker manager.
        
        Args:
            redis_conn: Redis connection instance
            queue_names: List of queue names to process (default: ['default'])
            worker_name: Unique worker name (auto-generated if None)
            job_timeout: Seconds before job is considered failed
            result_ttl: Seconds to keep job results
            failure_ttl: Seconds to keep failed jobs
            max_jobs: Maximum jobs per worker (None = unlimited)
        """
        self.redis_conn = redis_conn
        self.queue_names = queue_names or ["default"]
        self.worker_name = worker_name
        self.job_timeout = job_timeout
        self.result_ttl = result_ttl
        self.failure_ttl = failure_ttl
        self.max_jobs = max_jobs
        
        self.worker: Optional[Worker] = None
        self.running = False
        self.jobs_processed = 0
        self.jobs_failed = 0
        self.start_time: Optional[datetime] = None
        
        logger.info(f"Worker Manager initialized: queues={self.queue_names}")
    
    def create_worker(self) -> Worker:
        """
        Create and configure RQ worker.
        
        Returns:
            Configured Worker instance
        """
        try:
            worker = Worker(
                queues=self.queue_names,
                connection=self.redis_conn,
                name=self.worker_name,
                job_timeout=self.job_timeout,
                result_ttl=self.result_ttl,
                failure_ttl=self.failure_ttl,
                max_jobs=self.max_jobs,
                log_level=logging.INFO,
            )
            
            self.worker = worker
            logger.info(f"✓ Worker created: {worker.name}")
            return worker
        
        except Exception as e:
            logger.error(f"✗ Failed to create worker: {e}")
            raise
    
    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("✓ Signal handlers installed")
    
    def run(self, burst: bool = False) -> int:
        """
        Start worker and process jobs.
        
        Args:
            burst: If True, process all current jobs and exit
                   If False, run indefinitely
        
        Returns:
            Exit code (0=success, non-zero=error)
        """
        try:
            self.setup_signal_handlers()
            
            if self.worker is None:
                self.create_worker()
            
            self.running = True
            self.start_time = datetime.utcnow()
            
            logger.info(f"✓ Worker starting: name={self.worker.name}, burst={burst}")
            
            # Run worker
            self.worker.work(burst=burst)
            
            logger.info(f"✓ Worker finished: jobs_processed={self.jobs_processed}")
            return 0
        
        except Exception as e:
            logger.error(f"✗ Worker error: {e}")
            self.jobs_failed += 1
            return 1
        
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Gracefully shut down worker."""
        try:
            if self.worker:
                self.running = False
                logger.info(f"✓ Shutting down worker: {self.worker.name}")
            
            if self.redis_conn:
                self.redis_conn.close()
                logger.info("✓ Redis connection closed")
        
        except Exception as e:
            logger.error(f"✗ Error during shutdown: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get worker status.
        
        Returns:
            Dictionary with worker information
        """
        uptime = None
        if self.start_time:
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "worker_name": self.worker.name if self.worker else None,
            "queues": self.queue_names,
            "running": self.running,
            "jobs_processed": self.jobs_processed,
            "jobs_failed": self.jobs_failed,
            "uptime_seconds": uptime,
            "current_job": self.worker.get_current_job().id if self.worker and self.worker.get_current_job() else None,
        }


def run_worker(
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_db: int = 0,
    redis_password: Optional[str] = None,
    queue_names: List[str] = None,
    worker_name: Optional[str] = None,
    burst: bool = False,
    max_jobs: Optional[int] = None,
) -> int:
    """
    Standalone function to run a worker.
    
    Args:
        redis_host: Redis host
        redis_port: Redis port
        redis_db: Redis database
        redis_password: Redis password (optional)
        queue_names: List of queues to process
        worker_name: Worker name
        burst: Run in burst mode (process all current jobs and exit)
        max_jobs: Maximum jobs to process
    
    Returns:
        Exit code
    """
    try:
        # Import here to avoid circular dependency
        import redis
        
        # Connect to Redis
        redis_conn = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True,
        )
        
        # Test connection
        redis_conn.ping()
        logger.info("✓ Redis connection established")
        
        # Create and run worker
        manager = WorkerManager(
            redis_conn=redis_conn,
            queue_names=queue_names or ["default"],
            worker_name=worker_name,
            max_jobs=max_jobs,
        )
        
        return manager.run(burst=burst)
    
    except Exception as e:
        logger.error(f"✗ Worker startup failed: {e}")
        return 1


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="RQ Worker Process")
    parser.add_argument("--host", default="localhost", help="Redis host")
    parser.add_argument("--port", type=int, default=6379, help="Redis port")
    parser.add_argument("--db", type=int, default=0, help="Redis database")
    parser.add_argument("--password", help="Redis password")
    parser.add_argument("--queues", default="default", help="Comma-separated queue names")
    parser.add_argument("--name", help="Worker name")
    parser.add_argument("--burst", action="store_true", help="Burst mode (process all and exit)")
    parser.add_argument("--max-jobs", type=int, help="Maximum jobs to process")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Parse queues
    queues = [q.strip() for q in args.queues.split(",")]
    
    # Run worker
    exit_code = run_worker(
        redis_host=args.host,
        redis_port=args.port,
        redis_db=args.db,
        redis_password=args.password,
        queue_names=queues,
        worker_name=args.name,
        burst=args.burst,
        max_jobs=args.max_jobs,
    )
    
    sys.exit(exit_code)
