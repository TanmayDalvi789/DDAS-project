"""
Enum definitions for API schemas.
"""

from enum import Enum


class DetectionDecision(str, Enum):
    """Detection decision types."""
    BLOCK = "BLOCK"
    WARN = "WARN"
    WATCH = "WATCH"
    ALLOW = "ALLOW"


class SignalStatus(str, Enum):
    """Signal status types."""
    PENDING_ALERT = "pending_alert"
    ALERTED = "alerted"
    RESOLVED = "resolved"


class AlertStatus(str, Enum):
    """Alert status types."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
