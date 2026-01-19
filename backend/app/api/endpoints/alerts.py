"""
Alerts API Endpoints
RESTful API for alert management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api.schemas import (
    AlertCreate, AlertResponse, AlertListResponse, AlertUpdateRequest,
    ErrorResponse, AlertStatus
)
from app.db.database import get_db
from app.db.repositories.alerts_repo import AlertsRepository
from app.db.repositories.signals_repo import SignalsRepository
from app.services.alert_service import AlertService

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

def get_alerts_repository(db: Session = Depends(get_db)) -> AlertsRepository:
    """Get alerts repository."""
    return AlertsRepository(db)


def get_signals_repository(db: Session = Depends(get_db)) -> SignalsRepository:
    """Get signals repository."""
    return SignalsRepository(db)


def get_alert_service(db: Session = Depends(get_db)) -> AlertService:
    """Get alert service."""
    return AlertService(db)


# ============================================================================
# CREATE ENDPOINTS
# ============================================================================

@router.post(
    "",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Alert",
    description="Create alert from detection signal",
    responses={
        201: {"description": "Alert created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Signal not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    }
)
async def create_alert(
    alert_data: AlertCreate,
    signals_repo: SignalsRepository = Depends(get_signals_repository),
    service: AlertService = Depends(get_alert_service),
) -> AlertResponse:
    """
    Create alert from signal.
    
    - **signal_id**: Signal ID to alert on
    - **decision**: Decision (BLOCK, WARN, WATCH, ALLOW)
    - **reason**: Reason for alert
    - **priority**: Priority level (1-10)
    """
    try:
        # Verify signal exists
        signal = signals_repo.get_by_id(alert_data.signal_id)
        if not signal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Signal {alert_data.signal_id} not found"
            )
        
        # Create alert
        alert = service.create_from_signal(
            signal_id=alert_data.signal_id,
            decision=alert_data.decision.value,
            reason=alert_data.reason,
            confidence=signal.confidence,
            priority=alert_data.priority,
        )
        
        return AlertResponse.from_orm(alert)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create alert: {str(e)}"
        )


# ============================================================================
# READ ENDPOINTS
# ============================================================================

@router.get(
    "",
    response_model=AlertListResponse,
    summary="List Alerts",
    description="List all alerts with optional filtering",
    responses={
        200: {"description": "Alerts retrieved successfully"},
        500: {"model": ErrorResponse, "description": "Server error"},
    }
)
async def list_alerts(
    skip: int = Query(0, ge=0, description="Skip N alerts"),
    limit: int = Query(100, ge=1, le=1000, description="Return up to N alerts"),
    status: Optional[AlertStatus] = Query(None, description="Filter by status"),
    priority_min: Optional[int] = Query(None, ge=1, le=10, description="Minimum priority"),
    priority_max: Optional[int] = Query(None, ge=1, le=10, description="Maximum priority"),
    repo: AlertsRepository = Depends(get_alerts_repository),
) -> AlertListResponse:
    """
    List alerts with optional filtering.
    
    Query Parameters:
    - **skip**: Number of alerts to skip
    - **limit**: Number of alerts to return (1-1000)
    - **status**: Filter by status (active, resolved, escalated)
    - **priority_min**: Minimum priority (1-10)
    - **priority_max**: Maximum priority (1-10)
    """
    try:
        # Get all alerts
        if status:
            all_alerts = repo.list_by_status(status.value)
        else:
            all_alerts = repo.list_all()
        
        # Apply priority filtering
        filtered_alerts = all_alerts
        if priority_min:
            filtered_alerts = [a for a in filtered_alerts if a.priority >= priority_min]
        if priority_max:
            filtered_alerts = [a for a in filtered_alerts if a.priority <= priority_max]
        
        # Apply pagination
        paginated_alerts = filtered_alerts[skip:skip + limit]
        
        return AlertListResponse(
            total=len(filtered_alerts),
            count=len(paginated_alerts),
            alerts=[AlertResponse.from_orm(a) for a in paginated_alerts]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve alerts: {str(e)}"
        )


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Get Alert",
    description="Get details of a specific alert",
    responses={
        200: {"description": "Alert retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Alert not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    }
)
async def get_alert(
    alert_id: str,
    repo: AlertsRepository = Depends(get_alerts_repository),
) -> AlertResponse:
    """
    Get details of a specific alert.
    
    - **alert_id**: Alert ID (UUID)
    """
    try:
        alert = repo.get_by_id(alert_id)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found"
            )
        return AlertResponse.from_orm(alert)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve alert: {str(e)}"
        )


@router.get(
    "/active/count",
    response_model=dict,
    summary="Count Active Alerts",
    description="Get count of active alerts",
)
async def count_active_alerts(
    repo: AlertsRepository = Depends(get_alerts_repository),
) -> dict:
    """
    Count active alerts.
    """
    try:
        active_alerts = repo.list_active()
        return {"count": len(active_alerts), "status": "active"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to count alerts: {str(e)}"
        )


# ============================================================================
# UPDATE ENDPOINTS
# ============================================================================

@router.put(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Update Alert",
    description="Update alert status, priority, or notes",
    responses={
        200: {"description": "Alert updated successfully"},
        404: {"model": ErrorResponse, "description": "Alert not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    }
)
async def update_alert(
    alert_id: str,
    update_data: AlertUpdateRequest,
    repo: AlertsRepository = Depends(get_alerts_repository),
    service: AlertService = Depends(get_alert_service),
) -> AlertResponse:
    """
    Update alert.
    
    - **alert_id**: Alert ID to update
    - **status**: New status (active, resolved, escalated)
    - **priority**: New priority (1-10)
    - **notes**: Additional notes
    """
    try:
        alert = repo.get_by_id(alert_id)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found"
            )
        
        # Update status if provided
        if update_data.status:
            repo.update_status(alert_id, update_data.status.value)
        
        # Update priority if provided
        if update_data.priority is not None:
            from app.db.models import Alert
            from sqlalchemy import update
            stmt = update(Alert).where(Alert.id == alert_id).values(priority=update_data.priority)
            repo.db.execute(stmt)
            repo.db.commit()
        
        # Refresh alert
        updated_alert = repo.get_by_id(alert_id)
        return AlertResponse.from_orm(updated_alert)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update alert: {str(e)}"
        )


@router.post(
    "/{alert_id}/resolve",
    response_model=AlertResponse,
    summary="Resolve Alert",
    description="Resolve/close an alert",
)
async def resolve_alert(
    alert_id: str,
    repo: AlertsRepository = Depends(get_alerts_repository),
    service: AlertService = Depends(get_alert_service),
) -> AlertResponse:
    """
    Resolve alert.
    
    - **alert_id**: Alert ID to resolve
    """
    try:
        alert = repo.get_by_id(alert_id)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found"
            )
        
        repo.update_status(alert_id, "resolved")
        
        updated_alert = repo.get_by_id(alert_id)
        return AlertResponse.from_orm(updated_alert)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve alert: {str(e)}"
        )


@router.post(
    "/{alert_id}/escalate",
    response_model=AlertResponse,
    summary="Escalate Alert",
    description="Escalate alert priority",
)
async def escalate_alert(
    alert_id: str,
    repo: AlertsRepository = Depends(get_alerts_repository),
    service: AlertService = Depends(get_alert_service),
) -> AlertResponse:
    """
    Escalate alert priority.
    
    - **alert_id**: Alert ID to escalate
    """
    try:
        alert = repo.get_by_id(alert_id)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found"
            )
        
        escalated = service.escalate_priority(alert_id)
        return AlertResponse.from_orm(escalated)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to escalate alert: {str(e)}"
        )
