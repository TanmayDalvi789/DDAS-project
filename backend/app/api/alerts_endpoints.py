"""Alerts and decision API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models import AlertRequest, AlertResponse
from app.db.base import get_db
from app.security.auth import verify_api_key
from app.services.alerts import AlertService

router = APIRouter()


@router.post("/create")
async def create_alert(
    request: AlertRequest,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Create alert/decision based on detection signal.
    
    - **signal_id**: ID of the detection signal
    - **decision**: ALLOW, WARN, or BLOCK
    - **reason**: Optional reason for decision
    - **priority**: 1-10, higher = more urgent
    """
    
    await verify_api_key(x_api_key, db)
    
    alert_id = str(uuid.uuid4())
    
    try:
        alert_service = AlertService(db)
        
        # Verify signal exists
        signal = await alert_service.get_signal(request.signal_id)
        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")
        
        # Create alert
        alert = await alert_service.create_alert(
            alert_id=alert_id,
            signal_id=request.signal_id,
            decision=request.decision,
            reason=request.reason,
            priority=request.priority,
        )
        
        return {
            "alert_id": alert_id,
            "signal_id": request.signal_id,
            "decision": request.decision,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alert creation failed: {str(e)}")


@router.get("/alert/{alert_id}")
async def get_alert(
    alert_id: str,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve alert details."""
    
    await verify_api_key(x_api_key, db)
    
    alert_service = AlertService(db)
    alert = await alert_service.get_alert(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return alert


@router.get("/signal/{signal_id}/alert")
async def get_alert_for_signal(
    signal_id: str,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Get alert associated with a signal."""
    
    await verify_api_key(x_api_key, db)
    
    alert_service = AlertService(db)
    alert = await alert_service.get_alert_for_signal(signal_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="No alert for this signal")
    
    return alert


@router.get("/active")
async def list_active_alerts(
    limit: int = 100,
    offset: int = 0,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """List active alerts."""
    
    await verify_api_key(x_api_key, db)
    
    alert_service = AlertService(db)
    alerts = await alert_service.list_active_alerts(limit, offset)
    
    return {
        "count": len(alerts),
        "limit": limit,
        "offset": offset,
        "alerts": alerts,
    }


@router.patch("/alert/{alert_id}/status")
async def update_alert_status(
    alert_id: str,
    status: str,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Update alert status (e.g., resolved, acknowledged)."""
    
    await verify_api_key(x_api_key, db)
    
    alert_service = AlertService(db)
    
    try:
        updated_alert = await alert_service.update_alert_status(alert_id, status)
        if not updated_alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {
            "alert_id": alert_id,
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")
