"""
Event-related schemas.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any
from datetime import datetime


class EventCreate(BaseModel):
    """Request: Create event."""
    source_id: str = Field(..., min_length=1, max_length=255, description="Event source ID")
    source_type: str = Field(..., min_length=1, max_length=50, description="Source type (agent, proxy, etc)")
    event_type: str = Field(..., min_length=1, max_length=50, description="Event type (scan, traffic, etc)")
    payload: Dict[str, Any] = Field(default={}, description="Event payload")
    
    @validator('source_id')
    def validate_source_id(cls, v):
        """Validate source ID format."""
        if not v or len(v) < 1:
            raise ValueError("source_id must not be empty")
        return v


class EventResponse(BaseModel):
    """Response: Event details."""
    event_id: str
    source_id: str
    source_type: str
    event_type: str
    payload: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    """Response: List of events."""
    total: int
    count: int
    events: List[EventResponse]
