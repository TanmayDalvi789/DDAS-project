"""
Detection-related schemas.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.schemas.enums import DetectionDecision, TaskPriority


class DetectionRequest(BaseModel):
    """Request: Run detection on samples."""
    event_id: str = Field(..., description="Event ID to analyze")
    samples: List[str] = Field(..., min_items=1, description="Samples to detect against")
    threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Detection confidence threshold")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority")


class DetectionResult(BaseModel):
    """Detection algorithm result."""
    algorithm: str = Field(description="Algorithm name (fuzzy, semantic, exact)")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    found: bool = Field(description="Whether match found")
    matches: List[str] = Field(default=[], description="Matched items")


class DetectionResponse(BaseModel):
    """Response: Detection results."""
    event_id: str
    decision: DetectionDecision
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    results: List[DetectionResult] = Field(description="Results from each algorithm")
    job_id: Optional[str] = Field(default=None, description="Background job ID (if async)")
    
    class Config:
        from_attributes = True


class JobStatusResponse(BaseModel):
    """Response: Background job status."""
    job_id: str
    status: str = Field(description="Job status (queued, started, finished, failed)")
    progress: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Progress percentage")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Job result (when finished)")
    error: Optional[str] = Field(default=None, description="Error message (if failed)")
