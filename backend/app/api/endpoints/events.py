"""
Events API Endpoints
RESTful API for event management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.api.schemas import (
    EventCreate, EventResponse, EventListResponse, 
    ErrorResponse, EventFilterParams, PaginationParams
)
from app.db.database import get_db
from app.db.repositories.events_repo import EventsRepository
from app.services.ingest_service import IngestService

router = APIRouter(prefix="/api/v1/events", tags=["events"])


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

def get_events_repository(db: Session = Depends(get_db)) -> EventsRepository:
    """Get events repository."""
    return EventsRepository(db)


def get_ingest_service(db: Session = Depends(get_db)) -> IngestService:
    """Get ingest service."""
    return IngestService(db)


# ============================================================================
# CREATE ENDPOINTS
# ============================================================================

@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Event",
    description="Create a new event from specified source",
    responses={
        201: {"description": "Event created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Server error"},
    }
)
async def create_event(
    event_data: EventCreate,
    db: Session = Depends(get_db),
) -> EventResponse:
    """
    Create a new event.
    
    - **source_id**: Unique identifier for the event source
    - **source_type**: Type of source (agent, proxy, etc)
    - **event_type**: Type of event (scan, traffic, etc)
    - **payload**: Event data (arbitrary JSON)
    """
    try:
        import uuid
        from app.db.models import RawEvent
        
        event_id = str(uuid.uuid4())
        
        # Create raw event directly
        event = RawEvent(
            event_id=event_id,
            source_type=event_data.source_type,
            source_id=event_data.source_id,
            event_type=event_data.event_type,
            payload=event_data.payload,
            event_metadata={}
        )
        
        db.add(event)
        db.commit()
        db.refresh(event)
        
        return EventResponse.from_orm(event)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event: {str(e)}"
        )


# ============================================================================
# READ ENDPOINTS
# ============================================================================

@router.get(
    "",
    response_model=List[EventResponse],
    summary="List Events",
    description="List all events with optional filtering and pagination",
    responses={
        200: {"description": "Events retrieved successfully"},
        400: {"model": ErrorResponse, "description": "Invalid filters"},
        500: {"model": ErrorResponse, "description": "Server error"},
    }
)
async def list_events(
    skip: int = Query(0, ge=0, description="Skip N events"),
    limit: int = Query(100, ge=1, le=1000, description="Return up to N events"),
    source_id: Optional[str] = Query(None, description="Filter by source ID"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    db: Session = Depends(get_db),
) -> List[EventResponse]:
    """
    List events with optional filtering.
    
    Query Parameters:
    - **skip**: Number of events to skip (pagination)
    - **limit**: Number of events to return (1-1000)
    - **source_id**: Filter by source ID
    - **source_type**: Filter by source type
    - **event_type**: Filter by event type
    """
    try:
        from app.db.models import RawEvent
        
        # Query all events
        query = db.query(RawEvent)
        
        # Apply filters
        if source_id:
            query = query.filter(RawEvent.source_id == source_id)
        if source_type:
            query = query.filter(RawEvent.source_type == source_type)
        if event_type:
            query = query.filter(RawEvent.event_type == event_type)
        
        # Apply pagination and order by creation date
        all_events = query.order_by(RawEvent.created_at.desc()).offset(skip).limit(limit).all()
        
        return [EventResponse.from_orm(e) for e in all_events]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve events: {str(e)}"
        )


@router.get(
    "/{event_id}",
    response_model=EventResponse,
    summary="Get Event",
    description="Get details of a specific event",
    responses={
        200: {"description": "Event retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Event not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    }
)
async def get_event(
    event_id: str,
    repo: EventsRepository = Depends(get_events_repository),
) -> EventResponse:
    """
    Get details of a specific event.
    
    - **event_id**: Event ID (UUID)
    """
    try:
        event = repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {event_id} not found"
            )
        return EventResponse.from_orm(event)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve event: {str(e)}"
        )


@router.get(
    "/{event_id}/count",
    response_model=dict,
    summary="Get Event Count by Source",
    description="Count events from a specific source",
)
async def count_events_by_source(
    event_id: str,
    repo: EventsRepository = Depends(get_events_repository),
) -> dict:
    """
    Count events from a source.
    
    - **event_id**: Source ID to count from
    """
    try:
        event = repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {event_id} not found"
            )
        
        count = repo.count_by_source(event.source_id)
        return {"source_id": event.source_id, "count": count}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to count events: {str(e)}"
        )
