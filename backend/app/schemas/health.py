"""
Health and statistics schemas.
"""

from pydantic import BaseModel, Field
from datetime import datetime


class HealthResponse(BaseModel):
    """Response: Health check."""
    status: str = Field(description="Health status (healthy, degraded, unhealthy)")
    timestamp: datetime
    version: str = Field(description="API version")
    database: str = Field(description="Database status")
    queue: str = Field(description="Queue status")


class StatsResponse(BaseModel):
    """Response: System statistics."""
    total_events: int
    total_signals: int
    total_alerts: int
    alerts_active: int
    alerts_resolved: int
    detection_accuracy: float = Field(ge=0.0, le=1.0, description="Average detection confidence")
    queue_size: int
    queue_processed: int
