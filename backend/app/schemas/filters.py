"""
Filter/query parameter schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.schemas.enums import AlertStatus, DetectionDecision


class EventFilterParams(BaseModel):
    """Event filtering parameters."""
    source_id: Optional[str] = Field(default=None, description="Filter by source ID")
    source_type: Optional[str] = Field(default=None, description="Filter by source type")
    event_type: Optional[str] = Field(default=None, description="Filter by event type")
    start_date: Optional[datetime] = Field(default=None, description="Filter by start date")
    end_date: Optional[datetime] = Field(default=None, description="Filter by end date")


class AlertFilterParams(BaseModel):
    """Alert filtering parameters."""
    status: Optional[AlertStatus] = Field(default=None, description="Filter by status")
    decision: Optional[DetectionDecision] = Field(default=None, description="Filter by decision")
    priority_min: Optional[int] = Field(default=None, ge=1, le=10, description="Minimum priority")
    priority_max: Optional[int] = Field(default=None, ge=1, le=10, description="Maximum priority")
    start_date: Optional[datetime] = Field(default=None, description="Filter by start date")
    end_date: Optional[datetime] = Field(default=None, description="Filter by end date")
