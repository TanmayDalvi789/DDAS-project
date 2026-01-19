"""
Application Schemas
Pydantic models for request/response validation, organized by domain.

Use lazy imports to avoid circular dependencies:
    from app.schemas.enums import DetectionDecision
    from app.schemas.detection import DetectionRequest

Or import commonly used schemas from this package:
    from app.schemas import DetectionRequest, DetectionDecision
"""

def __getattr__(name):
    """Lazy load schemas to avoid circular imports."""
    # Enums
    if name == "DetectionDecision":
        from app.schemas.enums import DetectionDecision
        return DetectionDecision
    elif name == "SignalStatus":
        from app.schemas.enums import SignalStatus
        return SignalStatus
    elif name == "AlertStatus":
        from app.schemas.enums import AlertStatus
        return AlertStatus
    elif name == "TaskPriority":
        from app.schemas.enums import TaskPriority
        return TaskPriority
    # Events
    elif name == "EventCreate":
        from app.schemas.events import EventCreate
        return EventCreate
    elif name == "EventResponse":
        from app.schemas.events import EventResponse
        return EventResponse
    elif name == "EventListResponse":
        from app.schemas.events import EventListResponse
        return EventListResponse
    # Detection
    elif name == "DetectionRequest":
        from app.schemas.detection import DetectionRequest
        return DetectionRequest
    elif name == "DetectionResult":
        from app.schemas.detection import DetectionResult
        return DetectionResult
    elif name == "DetectionResponse":
        from app.schemas.detection import DetectionResponse
        return DetectionResponse
    elif name == "JobStatusResponse":
        from app.schemas.detection import JobStatusResponse
        return JobStatusResponse
    # Signals
    elif name == "SignalResponse":
        from app.schemas.signals import SignalResponse
        return SignalResponse
    elif name == "SignalListResponse":
        from app.schemas.signals import SignalListResponse
        return SignalListResponse
    # Alerts
    elif name == "AlertCreate":
        from app.schemas.alerts import AlertCreate
        return AlertCreate
    elif name == "AlertResponse":
        from app.schemas.alerts import AlertResponse
        return AlertResponse
    elif name == "AlertListResponse":
        from app.schemas.alerts import AlertListResponse
        return AlertListResponse
    elif name == "AlertUpdateRequest":
        from app.schemas.alerts import AlertUpdateRequest
        return AlertUpdateRequest
    # Health
    elif name == "HealthResponse":
        from app.schemas.health import HealthResponse
        return HealthResponse
    elif name == "StatsResponse":
        from app.schemas.health import StatsResponse
        return StatsResponse
    # Errors
    elif name == "ErrorResponse":
        from app.schemas.errors import ErrorResponse
        return ErrorResponse
    elif name == "ValidationErrorResponse":
        from app.schemas.errors import ValidationErrorResponse
        return ValidationErrorResponse
    # Common
    elif name == "PaginationParams":
        from app.schemas.common import PaginationParams
        return PaginationParams
    # Filters
    elif name == "EventFilterParams":
        from app.schemas.filters import EventFilterParams
        return EventFilterParams
    elif name == "AlertFilterParams":
        from app.schemas.filters import AlertFilterParams
        return AlertFilterParams
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

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
