"""
Worker Management Script
Standalone script for managing RQ workers with common operations.

Usage:
    python manage_workers.py start       # Start a worker
    python manage_workers.py status      # Show queue status
    python manage_workers.py cleanup     # Clean old jobs
    python manage_workers.py clear       # Clear a queue
"""

import argparse
import logging
import sys
from typing import Optional

from app.workers.redis_queue import get_queue_manager
from app.workers.worker import run_worker
from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def start_worker(
    host: str,
    port: int,
    db: int,
    password: Optional[str],
    queues: list,
    burst: bool,
    max_jobs: Optional[int],
):
    """Start a worker."""
    logger.info("Starting RQ worker...")
    exit_code = run_worker(
        redis_host=host,
        redis_port=port,
        redis_db=db,
        redis_password=password,
        queue_names=queues,
        burst=burst,
        max_jobs=max_jobs,
    )
    sys.exit(exit_code)


def show_status(
    host: str,
    port: int,
    db: int,
    password: Optional[str],
):
    """Show queue status."""
    try:
        manager = get_queue_manager(host=host, port=port, db=db, password=password)
        
        print("\n" + "=" * 60)
        print("QUEUE STATUS")
        print("=" * 60)
        
        for queue_name in ["critical", "high", "normal", "low"]:
            stats = manager.get_queue_stats(queue_name)
            
            if "error" in stats:
                print(f"\n{queue_name.upper()}: ERROR - {stats['error']}")
            else:
                print(f"\n{queue_name.upper()}")
                print(f"  Queued:   {stats['queued']}")
                print(f"  Started:  {stats['started']}")
                print(f"  Finished: {stats['finished']}")
                print(f"  Failed:   {stats['failed']}")
                print(f"  Total:    {stats['total']}")
        
        print("\n" + "=" * 60 + "\n")
    
    except Exception as e:
        logger.error(f"✗ Failed to get status: {e}")
        sys.exit(1)


def cleanup_jobs(
    host: str,
    port: int,
    db: int,
    password: Optional[str],
    days: int,
):
    """Clean up old jobs."""
    try:
        manager = get_queue_manager(host=host, port=port, db=db, password=password)
        
        print("\n" + "=" * 60)
        print(f"CLEANING OLD JOBS (older than {days} days)")
        print("=" * 60 + "\n")
        
        total_cleaned = 0
        for queue_name in ["critical", "high", "normal", "low"]:
            cleaned = manager.cleanup_old_jobs(queue_name, days)
            total_cleaned += cleaned
            print(f"{queue_name.upper()}: {cleaned} jobs cleaned")
        
        print(f"\nTotal cleaned: {total_cleaned}")
        print("=" * 60 + "\n")
    
    except Exception as e:
        logger.error(f"✗ Failed to cleanup jobs: {e}")
        sys.exit(1)


def clear_queue(
    host: str,
    port: int,
    db: int,
    password: Optional[str],
    queue_name: str,
):
    """Clear a queue."""
    try:
        manager = get_queue_manager(host=host, port=port, db=db, password=password)
        
        # Confirm
        response = input(f"Really clear '{queue_name}' queue? (yes/no): ")
        if response.lower() != "yes":
            print("Cancelled.")
            return
        
        print(f"\nClearing queue '{queue_name}'...")
        count = manager.clear_queue(queue_name)
        print(f"✓ Cleared {count} jobs\n")
    
    except Exception as e:
        logger.error(f"✗ Failed to clear queue: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DDAS Worker Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_workers.py start                    # Start worker with defaults
  python manage_workers.py start --queues high,normal --burst
  python manage_workers.py status                   # Show queue status
  python manage_workers.py cleanup --days 7         # Clean jobs older than 7 days
  python manage_workers.py clear --queue normal     # Clear 'normal' queue
        """
    )
    
    parser.add_argument("command", help="Command: start, status, cleanup, clear")
    
    # Connection arguments
    parser.add_argument("--host", default="localhost", help="Redis host")
    parser.add_argument("--port", type=int, default=6379, help="Redis port")
    parser.add_argument("--db", type=int, default=0, help="Redis database")
    parser.add_argument("--password", help="Redis password")
    
    # Worker arguments
    parser.add_argument("--queues", default="critical,high,normal,low", help="Comma-separated queue names")
    parser.add_argument("--burst", action="store_true", help="Run in burst mode (process all and exit)")
    parser.add_argument("--max-jobs", type=int, help="Maximum jobs to process")
    
    # Cleanup arguments
    parser.add_argument("--days", type=int, default=7, help="Days threshold for cleanup")
    
    # Clear arguments
    parser.add_argument("--queue", default="normal", help="Queue to clear")
    
    args = parser.parse_args()
    
    # Get Redis config from environment if not provided
    if args.host == "localhost" and args.port == 6379:
        try:
            settings = get_settings()
            args.host = settings.REDIS_HOST
            args.port = settings.REDIS_PORT
            args.db = settings.REDIS_DB
            args.password = settings.REDIS_PASSWORD
        except:
            pass
    
    # Parse queues
    queues = [q.strip() for q in args.queues.split(",")]
    
    # Execute command
    if args.command == "start":
        start_worker(
            host=args.host,
            port=args.port,
            db=args.db,
            password=args.password,
            queues=queues,
            burst=args.burst,
            max_jobs=args.max_jobs,
        )
    
    elif args.command == "status":
        show_status(
            host=args.host,
            port=args.port,
            db=args.db,
            password=args.password,
        )
    
    elif args.command == "cleanup":
        cleanup_jobs(
            host=args.host,
            port=args.port,
            db=args.db,
            password=args.password,
            days=args.days,
        )
    
    elif args.command == "clear":
        clear_queue(
            host=args.host,
            port=args.port,
            db=args.db,
            password=args.password,
            queue_name=args.queue,
        )
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
