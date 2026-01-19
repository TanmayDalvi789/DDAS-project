"""
Signal-related schemas.
"""

from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from app.schemas.enums import SignalStatus


class SignalResponse(BaseModel):
    """Response: Signal details."""
    id: str
    event_id: str
    detection_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    detected_items: List[str]
    status: SignalStatus
    created_at: datetime
    
    class Config:
        from_attributes = True


class SignalListResponse(BaseModel):
    """Response: List of signals."""
    total: int
    count: int
    signals: List[SignalResponse]
