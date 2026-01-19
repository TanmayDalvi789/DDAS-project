"""
API Request and Response Schemas (Compatibility Shim)

DEPRECATED: This module is a backward-compatibility shim.
New code should import from app.schemas directly.

All schemas have been moved to app.schemas for better organization.
This module re-exports them to maintain API compatibility.

Example:
    from app.api.schemas import DetectionRequest  # Still works
    from app.schemas import DetectionRequest       # Preferred

For organization details, see: app/schemas/
"""

# Re-export all schemas from app.schemas for backward compatibility
from app.schemas import (
    # Enums
    DetectionDecision,
    SignalStatus,
    AlertStatus,
    TaskPriority,
    # Events
    EventCreate,
    EventResponse,
    EventListResponse,
    # Detection
    DetectionRequest,
    DetectionResult,
    DetectionResponse,
    JobStatusResponse,
    # Signals
    SignalResponse,
    SignalListResponse,
    # Alerts
    AlertCreate,
    AlertResponse,
    AlertListResponse,
    AlertUpdateRequest,
    # Health
    HealthResponse,
    StatsResponse,
    # Errors
    ErrorResponse,
    ValidationErrorResponse,
    # Common
    PaginationParams,
    # Filters
    EventFilterParams,
    AlertFilterParams,
)

__all__ = [
    # Enums
    "DetectionDecision",
    "SignalStatus",
    "AlertStatus",
    "TaskPriority",
    # Events
    "EventCreate",
    "EventResponse",
    "EventListResponse",
    # Detection
    "DetectionRequest",
    "DetectionResult",
    "DetectionResponse",
    "JobStatusResponse",
    # Signals
    "SignalResponse",
    "SignalListResponse",
    # Alerts
    "AlertCreate",
    "AlertResponse",
    "AlertListResponse",
    "AlertUpdateRequest",
    # Health
    "HealthResponse",
    "StatsResponse",
    # Errors
    "ErrorResponse",
    "ValidationErrorResponse",
    # Common
    "PaginationParams",
    # Filters
    "EventFilterParams",
    "AlertFilterParams",
]
