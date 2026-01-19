"""Detection orchestration API endpoints."""

import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models import DetectionRequest, SignalResponse
from app.db.base import get_db
from app.security.auth import verify_api_key
from app.services.detection import DetectionService
from app.workers.queue import enqueue_task

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/trigger")
async def trigger_detection(
    request: DetectionRequest,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None,
):
    """
    Trigger detection pipeline for an ingested event.
    
    Detection runs asynchronously in the background.
    
    - **event_id**: ID of the ingested event
    - **detection_type**: Type of detection (fuzzy, semantic, exact)
    - **config**: Optional detection configuration
    """
    
    await verify_api_key(x_api_key, db)
    
    signal_id = str(uuid.uuid4())
    
    # CHECKPOINT: Detection requested
    logger.info(f"[CHECKPOINT] Detection triggered")
    logger.info(f"  - Signal ID: {signal_id}")
    logger.info(f"  - Event ID: {request.event_id}")
    logger.info(f"  - Type: {request.detection_type}")
    
    try:
        detection_service = DetectionService(db)
        
        # Verify event exists
        event = await detection_service.get_event(request.event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Create signal record
        await detection_service.create_signal(
            signal_id=signal_id,
            event_id=request.event_id,
            detection_type=request.detection_type,
            status="pending",
            config=request.config or {},
        )
        
        logger.info(f"[CHECKPOINT] Signal record created")
        
        # Enqueue detection task (async, non-blocking)
        if background_tasks:
            background_tasks.add_task(
                enqueue_task,
                "run_detection",
                {
                    "signal_id": signal_id,
                    "event_id": request.event_id,
                    "detection_type": request.detection_type,
                    "config": request.config or {},
                },
            )
            logger.info(f"[CHECKPOINT] Detection queued for background processing")
        
        return {
            "signal_id": signal_id,
            "event_id": request.event_id,
            "status": "queued",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"[CHECKPOINT] Detection trigger failed: {e}")
        raise HTTPException(status_code=500, detail=f"Detection trigger failed: {str(e)}")


@router.get("/signal/{signal_id}")
async def get_signal(
    signal_id: str,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve signal/detection result."""
    
    await verify_api_key(x_api_key, db)
    
    detection_service = DetectionService(db)
    signal = await detection_service.get_signal(signal_id)
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    return signal


@router.get("/event/{event_id}/signals")
async def list_signals_for_event(
    event_id: str,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """List all detection signals for an event."""
    
    await verify_api_key(x_api_key, db)
    
    detection_service = DetectionService(db)
    signals = await detection_service.list_signals_for_event(event_id)
    
    return {
        "event_id": event_id,
        "count": len(signals),
        "signals": signals,
    }


@router.get("/status")
async def detection_pipeline_status(
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Get detection pipeline status."""
    
    await verify_api_key(x_api_key, db)
    
    detection_service = DetectionService(db)
    stats = await detection_service.get_pipeline_stats()
    
    return {
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "stats": stats,
    }
