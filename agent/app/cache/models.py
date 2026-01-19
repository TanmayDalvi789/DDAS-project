"""Cache data models."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class CacheEntry:
    """Cached decision entry."""
    file_hash: str
    decision: str
    confidence: float
    timestamp: datetime
    ttl_seconds: int


@dataclass
class FileObservation:
    """Observation of file download."""
    file_hash: str
    url: str
    timestamp: datetime
    count: int  # Times seen
