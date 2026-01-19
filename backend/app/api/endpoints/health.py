"""
Health and Status API Endpoints
System health, statistics, and monitoring endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.api.schemas import HealthResponse, StatsResponse
from app.db.database import get_db
from app.db.repositories.events import EventsRepository
from app.db.repositories.signals import SignalsRepository
from app.db.repositories.alerts import AlertsRepository
from app.workers.task_queue import get_task_queue

router = APIRouter(prefix="/api/v1", tags=["health"])


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

def get_events_repository(db: Session = Depends(get_db)) -> EventsRepository:
    """Get events repository."""
    return EventsRepository(db)


def get_signals_repository(db: Session = Depends(get_db)) -> SignalsRepository:
    """Get signals repository."""
    return SignalsRepository(db)


def get_alerts_repository(db: Session = Depends(get_db)) -> AlertsRepository:
    """Get alerts repository."""
    return AlertsRepository(db)


# ============================================================================
# HEALTH ENDPOINT
# ============================================================================

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check system health status",
    responses={
        200: {"description": "System healthy"},
        503: {"description": "System degraded or unhealthy"},
    }
)
async def health_check(
    db: Session = Depends(get_db),
) -> HealthResponse:
    """
    Check system health.
    
    Returns:
    - **status**: healthy, degraded, or unhealthy
    - **database**: Connection status
    - **queue**: Queue system status
    - **version**: API version
    """
    try:
        # Check database
        db_status = "healthy"
        try:
            # Simple query to test connection
            result = db.execute("SELECT 1")
            result.close()
        except Exception as e:
            db_status = f"unhealthy ({str(e)[:50]})"
        
        # Check queue
        queue_status = "healthy"
        try:
            task_queue = get_task_queue()
            if task_queue.manager:
                task_queue.manager.connect()
        except Exception as e:
            queue_status = f"unhealthy ({str(e)[:50]})"
        
        # Determine overall status
        if db_status == "healthy" and queue_status == "healthy":
            overall_status = "healthy"
        elif db_status != "healthy" or queue_status != "healthy":
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version="1.0.0",
            database=db_status,
            queue=queue_status,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )


# ============================================================================
# STATISTICS ENDPOINT
# ============================================================================

@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="System Statistics",
    description="Get system statistics and metrics",
    responses={
        200: {"description": "Statistics retrieved successfully"},
        500: {"description": "Failed to retrieve statistics"},
    }
)
async def get_statistics(
    events_repo: EventsRepository = Depends(get_events_repository),
    signals_repo: SignalsRepository = Depends(get_signals_repository),
    alerts_repo: AlertsRepository = Depends(get_alerts_repository),
) -> StatsResponse:
    """
    Get system statistics.
    
    Returns:
    - **total_events**: Total events processed
    - **total_signals**: Total signals generated
    - **total_alerts**: Total alerts created
    - **alerts_active**: Currently active alerts
    - **alerts_resolved**: Resolved alerts
    - **detection_accuracy**: Average detection confidence
    - **queue_size**: Current queue size
    - **queue_processed**: Total jobs processed
    """
    try:
        # Count events
        all_events = events_repo.list_recent(limit=100000)
        total_events = len(all_events)
        
        # Count signals
        all_signals = signals_repo.list_pending()  # This gets all signals
        total_signals = len(all_signals)
        
        # Count alerts
        all_alerts = alerts_repo.list_all()
        total_alerts = len(all_alerts)
        
        # Active vs resolved alerts
        active_alerts = alerts_repo.list_active()
        alerts_active = len(active_alerts)
        
        # Calculate detection accuracy
        if all_signals:
            avg_confidence = sum(s.confidence for s in all_signals) / len(all_signals)
        else:
            avg_confidence = 0.0
        
        # Queue statistics
        try:
            task_queue = get_task_queue()
            queue_stats = task_queue.get_queue_stats()
            queue_size = queue_stats.get("queue_size", 0)
            queue_processed = queue_stats.get("total_jobs", 0)
        except:
            queue_size = 0
            queue_processed = 0
        
        return StatsResponse(
            total_events=total_events,
            total_signals=total_signals,
            total_alerts=total_alerts,
            alerts_active=alerts_active,
            alerts_resolved=total_alerts - alerts_active,
            detection_accuracy=avg_confidence,
            queue_size=queue_size,
            queue_processed=queue_processed,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


# ============================================================================
# VERSION ENDPOINT
# ============================================================================

@router.get(
    "/version",
    summary="Get API Version",
    description="Get API version information",
)
async def get_version() -> dict:
    """
    Get API version.
    """
    return {
        "version": "1.0.0",
        "name": "DDAS Detection API",
        "status": "stable",
        "build": "2026-01-15",
    }


# ============================================================================
# READY ENDPOINT
# ============================================================================

@router.get(
    "/ready",
    summary="Readiness Check",
    description="Check if API is ready to handle requests",
    responses={
        200: {"description": "API is ready"},
        503: {"description": "API is not ready"},
    }
)
async def ready_check(
    db: Session = Depends(get_db),
) -> dict:
    """
    Check if API is ready.
    """
    try:
        # Test database connection
        db.execute("SELECT 1")
        
        return {"ready": True, "message": "API is ready to handle requests"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"API is not ready: {str(e)}"
        )


# ============================================================================
# LIVE ENDPOINT
# ============================================================================

@router.get(
    "/live",
    summary="Liveness Check",
    description="Check if API is running",
)
async def live_check() -> dict:
    """
    Check if API is running (liveness probe).
    """
    return {"live": True, "message": "API is running"}
