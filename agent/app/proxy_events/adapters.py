"""
Event Adapters - STEP-3 Implementation

Convert proxy events to internal format.

Adapters normalize proxy events, decoupling the agent from proxy
implementation details.

STEP-3 Decisions:
- HTTP adapter fully implemented (primary)
- File and Socket adapters as stubs for future phases
"""

import logging
from typing import Callable

logger = logging.getLogger(__name__)


class EventAdapter:
    """
    Base interface for event adapters.
    
    Adapters normalize proxy events to internal format.
    Decouples agent from proxy implementation details.
    """
    
    def receive_event(self, event: dict) -> dict:
        """
        Normalize proxy event to internal format.
        
        Args:
            event: Raw event from proxy
        
        Returns:
            dict: Normalized event
        """
        raise NotImplementedError


class HTTPEventAdapter(EventAdapter):
    """
    HTTP adapter for events from MITM proxy (STEP-3).
    
    Receives events via HTTP POST /event from the proxy.
    Normalizes to internal format for processing.
    
    This is the primary event transport in STEP-3.
    
    Defensive Guards:
    - Validates input is dict
    - Validates required fields present
    - Logs validation failures
    - Never crashes (degrades gracefully)
    """
    
    # Contract: Required fields in normalized event
    REQUIRED_FIELDS = {"filename", "file_size", "source_url"}
    
    def receive_event(self, event: dict) -> dict:
        """
        Normalize HTTP proxy event with contract validation.
        
        The proxy sends events with:
        {
            "event_type": "file_download" | "network_flow" | ...
            "timestamp": unix_timestamp,
            "data": {
                "url": "https://example.com/file.zip",
                "filename": "file.zip",
                "mime_type": "application/zip",
                "file_size": 1024000,
                ...
            }
        }
        
        Normalized output:
        {
            "event_type": "file_download",
            "timestamp": unix_timestamp,
            "data": {...}
        }
        
        Args:
            event: Raw event from HTTP proxy
        
        Returns:
            dict: Normalized event
        
        Raises:
            ValueError: If event is malformed (fails-closed)
        """
        # Defensive guard: Input must be dict
        if not isinstance(event, dict):
            logger.error(
                f"[ADAPT] Invalid event type: {type(event).__name__}. Expected dict. "
                f"Event will be rejected."
            )
            raise ValueError(f"Event must be dict, got {type(event).__name__}")
        
        # Extract normalized form
        normalized = {
            "event_type": event.get("event_type", "file_download"),
            "timestamp": event.get("timestamp"),
            "data": event.get("data", {}),
        }
        
        # Defensive guard: Validate required fields in data
        data = normalized.get("data", {})
        missing_fields = self.REQUIRED_FIELDS - set(data.keys())
        
        if missing_fields:
            logger.error(
                f"[ADAPT] Event missing required fields: {missing_fields}. "
                f"Fields required: {self.REQUIRED_FIELDS}. "
                f"Event will be rejected."
            )
            raise ValueError(f"Missing required fields: {missing_fields}")
        
        # Defensive guard: Validate field types
        filename = data.get("filename")
        file_size = data.get("file_size")
        source_url = data.get("source_url")
        
        if not isinstance(filename, str) or not filename:
            logger.error(f"[ADAPT] Invalid filename: {filename!r}. Must be non-empty string.")
            raise ValueError("filename must be non-empty string")
        
        if not isinstance(file_size, int) or file_size < 0:
            logger.error(f"[ADAPT] Invalid file_size: {file_size!r}. Must be non-negative int.")
            raise ValueError("file_size must be non-negative integer")
        
        if not isinstance(source_url, str) or not source_url:
            logger.error(f"[ADAPT] Invalid source_url: {source_url!r}. Must be non-empty string.")
            raise ValueError("source_url must be non-empty string")
        
        logger.info(f"[ADAPT] Event validated: {filename} ({file_size} bytes)")
        return normalized


class FileEventAdapter(EventAdapter):
    """
    File adapter for testing (STUB - Phase-4+).
    
    Would read events from JSON lines file.
    
    Not implemented in STEP-3.
    """
    
    def receive_event(self, event: dict) -> dict:
        """
        Parse event from file.
        
        TODO Phase-4: Implement file-based event reading
        """
        logger.warning("FileEventAdapter not implemented yet")
        return event


class SocketEventAdapter(EventAdapter):
    """
    Socket adapter for IPC (STUB - Phase-4+).
    
    Would receive events from Unix/Windows named socket.
    
    Not implemented in STEP-3.
    """
    
    def receive_event(self, event: dict) -> dict:
        """
        Parse event from socket.
        
        TODO Phase-4: Implement socket-based event reading
        """
        logger.warning("SocketEventAdapter not implemented yet")
        return event

