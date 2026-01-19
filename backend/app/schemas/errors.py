"""
Error response schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class ErrorResponse(BaseModel):
    """Response: Error details."""
    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    status_code: int = Field(description="HTTP status code")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")


class ValidationErrorResponse(BaseModel):
    """Response: Validation error details."""
    error: str = "validation_error"
    message: str = "Request validation failed"
    status_code: int = 422
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    fields: Dict[str, List[str]] = Field(description="Field-specific errors")
