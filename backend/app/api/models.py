"""Request/Response models for ingestion."""

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DataSourceType(str, Enum):
    """Data source type enum."""
    AGENT = "agent"
    PROXY = "proxy"
    DASHBOARD = "dashboard"


class RawEventRequest(BaseModel):
    """Model for raw event ingestion from any source."""
    
    source_type: DataSourceType
    source_id: str = Field(..., description="Agent ID, proxy ID, or dashboard user ID")
    event_type: str
    timestamp: datetime
    payload: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "source_type": "agent",
                "source_id": "agent-001",
                "event_type": "file_scanned",
                "timestamp": "2024-01-15T10:30:00Z",
                "payload": {
                    "file_hash": "abc123def456",
                    "file_path": "/path/to/file",
                    "size": 1024,
                },
                "metadata": {"priority": "high"}
            }
        }


class DetectionRequest(BaseModel):
    """Model for triggering detection on ingested data."""
    
    event_id: str
    detection_type: str = Field(..., description="e.g., 'fuzzy', 'semantic', 'exact'")
    config: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt-001",
                "detection_type": "semantic",
                "config": {"threshold": 0.7}
            }
        }


class SignalResponse(BaseModel):
    """Model for detection signal/result."""
    
    signal_id: str
    event_id: str
    detection_type: str
    confidence: float
    result: Dict[str, Any]
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "signal_id": "sig-001",
                "event_id": "evt-001",
                "detection_type": "semantic",
                "confidence": 0.92,
                "result": {"matches": [{"file_hash": "xyz789"}]},
                "created_at": "2024-01-15T10:35:00Z"
            }
        }


class AlertRequest(BaseModel):
    """Model for creating alerts/decisions."""
    
    signal_id: str
    decision: str = Field(..., description="ALLOW, WARN, or BLOCK")
    reason: Optional[str] = None
    priority: int = Field(default=5, ge=1, le=10)
    
    class Config:
        json_schema_extra = {
            "example": {
                "signal_id": "sig-001",
                "decision": "BLOCK",
                "reason": "High confidence match with malicious asset",
                "priority": 9
            }
        }


class AlertResponse(BaseModel):
    """Model for alert response."""
    
    alert_id: str
    signal_id: str
    decision: str
    status: str
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "alert_id": "alr-001",
                "signal_id": "sig-001",
                "decision": "BLOCK",
                "status": "active",
                "created_at": "2024-01-15T10:35:30Z"
            }
        }


class AgentStatusRequest(BaseModel):
    """Model for agent status/health updates."""
    
    agent_id: str
    status: str = Field(..., description="online, offline, error")
    last_seen: datetime
    detection_count: int = 0
    error_count: int = 0
    metadata: Optional[Dict[str, Any]] = None


class WorkerStatusResponse(BaseModel):
    """Model for worker/service status."""
    
    worker_id: str
    status: str
    last_heartbeat: datetime
    tasks_processed: int
    errors: int
    queue_size: Optional[int] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "worker_id": "worker-001",
                "status": "running",
                "last_heartbeat": "2024-01-15T10:40:00Z",
                "tasks_processed": 1250,
                "errors": 0,
                "queue_size": 45
            }
        }
