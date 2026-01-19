"""Ingestion API endpoints."""

from typing import List
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models import RawEventRequest, DataSourceType
from app.db.base import get_db
from app.security.auth import verify_api_key
from app.services.ingestion import IngestService
from app.workers.queue import enqueue_task

router = APIRouter()


@router.post("/raw-event")
async def ingest_raw_event(
    request: RawEventRequest,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None,
):
    """
    Ingest raw event from agent, proxy, or dashboard.
    
    - **source_type**: AGENT, PROXY, or DASHBOARD
    - **source_id**: Identifier of the data source
    - **event_type**: Type of event being ingested
    - **payload**: Event data (flexible structure)
    """
    
    # Verify API key
    await verify_api_key(x_api_key, db)
    
    event_id = str(uuid.uuid4())
    
    try:
        # Store raw event
        ingest_service = IngestService(db)
        await ingest_service.store_raw_event(
            event_id=event_id,
            source_type=request.source_type.value,
            source_id=request.source_id,
            event_type=request.event_type,
            payload=request.payload,
            metadata=request.metadata or {},
        )
        
        # Enqueue for detection processing (non-blocking)
        if background_tasks:
            background_tasks.add_task(
                enqueue_task,
                "process_detection",
                {"event_id": event_id, "source_type": request.source_type.value},
            )
        
        return {
            "event_id": event_id,
            "status": "received",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Event queued for processing",
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/batch-events")
async def ingest_batch_events(
    requests: List[RawEventRequest],
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None,
):
    """
    Batch ingest multiple raw events.
    
    Useful for agents sending multiple events in a single request.
    """
    
    # Verify API key
    await verify_api_key(x_api_key, db)
    
    event_ids = []
    ingest_service = IngestService(db)
    
    try:
        for request in requests:
            event_id = str(uuid.uuid4())
            await ingest_service.store_raw_event(
                event_id=event_id,
                source_type=request.source_type.value,
                source_id=request.source_id,
                event_type=request.event_type,
                payload=request.payload,
                metadata=request.metadata or {},
            )
            event_ids.append(event_id)
            
            # Enqueue for processing
            if background_tasks:
                background_tasks.add_task(
                    enqueue_task,
                    "process_detection",
                    {"event_id": event_id},
                )
        
        return {
            "event_ids": event_ids,
            "count": len(event_ids),
            "status": "received",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch ingestion failed: {str(e)}")


@router.get("/event/{event_id}")
async def get_event(
    event_id: str,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve stored event details."""
    
    await verify_api_key(x_api_key, db)
    
    ingest_service = IngestService(db)
    event = await ingest_service.get_event(event_id)
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return event


@router.get("/events/source/{source_id}")
async def list_events_by_source(
    source_id: str,
    limit: int = 100,
    offset: int = 0,
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """List events from a specific source (agent/proxy/dashboard)."""
    
    await verify_api_key(x_api_key, db)
    
    ingest_service = IngestService(db)
    events = await ingest_service.list_events_by_source(source_id, limit, offset)
    
    return {
        "source_id": source_id,
        "count": len(events),
        "limit": limit,
        "offset": offset,
        "events": events,
    }
