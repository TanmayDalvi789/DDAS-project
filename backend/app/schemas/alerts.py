"""
Alert-related schemas.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.schemas.enums import AlertStatus, DetectionDecision


class AlertCreate(BaseModel):
    """Request: Create alert."""
    signal_id: str = Field(..., description="Signal ID to alert on")
    decision: DetectionDecision = Field(..., description="Alert decision")
    reason: str = Field(..., min_length=1, max_length=500, description="Alert reason")
    priority: int = Field(default=5, ge=1, le=10, description="Alert priority (1-10)")


class AlertResponse(BaseModel):
    """Response: Alert details."""
    id: str
    signal_id: str
    decision: DetectionDecision
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    priority: int
    status: AlertStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """Response: List of alerts."""
    total: int
    count: int
    alerts: List[AlertResponse]


class AlertUpdateRequest(BaseModel):
    """Request: Update alert."""
    status: Optional[AlertStatus] = Field(default=None, description="New status")
    priority: Optional[int] = Field(default=None, ge=1, le=10, description="New priority")
    notes: Optional[str] = Field(default=None, max_length=1000, description="Additional notes")
