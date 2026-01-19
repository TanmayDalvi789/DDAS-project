"""
Proxy Event Listener - STEP-3 Implementation

HTTP listener for proxy events with immediate processing.

Key design decisions (STEP-3):
1. HTTP listener on configurable port (default 9999)
2. Invalid events logged and discarded (FAIL-CLOSED)
3. Immediate processing via callback (no queue)
4. Stub files for secondary adapters (file, socket)
5. Immediate shutdown (no draining)
"""

import logging
import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ProxyEventHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for proxy events.
    
    STEP-3: Validates event format and processes immediately via callback.
    Invalid events are logged and discarded (FAIL-CLOSED).
    """
    
    # Callback function set by listener
    event_callback = None
    
    def do_POST(self):
        """
        Handle POST request with proxy event.
        
        Flow:
        1. Validate path
        2. Read and parse JSON body
        3. Validate event format (FAIL-CLOSED)
        4. Send 202 Accepted immediately (non-blocking)
        5. Process event via callback
        """
        # Only accept /event path
        if self.path != "/event":
            self.send_error(404, "Not Found")
            return
        
        try:
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self.send_error(400, "Bad Request: No payload")
                logger.warning("Rejected event: empty payload")
                return
            
            body = self.rfile.read(content_length)
            event = json.loads(body.decode("utf-8"))
            
            # Validate event format (FAIL-CLOSED)
            if not self._validate_event(event):
                self.send_error(400, "Bad Request: Invalid event format")
                logger.warning(f"Rejected invalid event")
                return
            
            # Send 202 Accepted immediately (non-blocking)
            self.send_response(202)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "accepted"}).encode("utf-8"))
            
            # Pass to callback for processing (immediate, no queue)
            if self.event_callback:
                self.event_callback(event)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Rejected event: Invalid JSON - {e}")
            self.send_error(400, "Bad Request: Invalid JSON")
        except Exception as e:
            logger.error(f"Error processing event: {e}")
            self.send_error(500, "Internal Server Error")
    
    def _validate_event(self, event: dict) -> bool:
        """
        Validate proxy event format (FAIL-CLOSED).
        
        Required fields:
        - event_type (string)
        - timestamp (int or float)
        - data (dict)
        
        Args:
            event: Event payload to validate
        
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            if not isinstance(event, dict):
                return False
            
            # Check required fields
            required_fields = {
                'event_type': str,
                'timestamp': (int, float),
                'data': dict
            }
            
            for field, expected_type in required_fields.items():
                if field not in event:
                    return False
                
                if not isinstance(event[field], expected_type):
                    return False
            
            return True
        
        except Exception:
            return False
    
    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        # Log at debug level only
        logger.debug(format % args)



class ProxyEventListener:
    """
    HTTP listener for proxy events (STEP-3).
    
    Design decisions:
    - HTTP listener on configurable port (default 9999)
    - Invalid events logged and discarded (FAIL-CLOSED)
    - Immediate processing via callback (no queue)
    - Immediate shutdown (no draining)
    
    The listener runs in a background thread and processes events
    from the MITM proxy via HTTP POST requests.
    
    Example usage:
        listener = ProxyEventListener(port=9999, event_handler_callback=handler)
        listener.start()
        ...
        listener.stop()
    """
    
    def __init__(self, port: int, event_handler_callback: Callable):
        """
        Initialize event listener.
        
        Args:
            port: Local port to listen on (e.g., 9999)
            event_handler_callback: Function to call with valid events
        """
        self.port = port
        self.event_handler_callback = event_handler_callback
        self._server = None
        self._thread = None
        self._running = False
    
    def start(self):
        """
        Start listening for events in background thread.
        
        Immediately returns after starting the listener thread.
        The listener runs in the background.
        """
        if self._running:
            logger.warning("Event listener already running")
            return
        
        try:
            # Set callback for HTTP handler
            ProxyEventHandler.event_callback = self._handle_event
            
            # Create HTTP server (bind to all interfaces)
            self._server = HTTPServer(("0.0.0.0", self.port), ProxyEventHandler)
            self._running = True
            
            # Start in background thread (daemon=True for immediate shutdown)
            self._thread = threading.Thread(
                target=self._server.serve_forever,
                daemon=True
            )
            self._thread.start()
            
            logger.info(f"Proxy event listener started (port={self.port})")
        
        except Exception as e:
            logger.error(f"Failed to start event listener: {e}")
            self._running = False
            raise
    
    def stop(self):
        """
        Stop listening for events immediately (STEP-3).
        
        No draining - immediate shutdown.
        """
        if not self._running:
            return
        
        try:
            self._running = False
            if self._server:
                self._server.shutdown()
                self._server.server_close()
            if self._thread:
                self._thread.join(timeout=1)
            logger.info("Proxy event listener stopped")
        except Exception as e:
            logger.error(f"Error stopping listener: {e}")
    
    def _handle_event(self, event: dict):
        """
        Process valid event from proxy (STEP-3).
        
        Immediate processing via callback (no queue).
        
        Args:
            event: Event payload from proxy (already validated by handler)
        """
        try:
            logger.debug(f"Processing event: {event}")
            
            # Forward to handler callback
            if self.event_handler_callback:
                self.event_handler_callback(event)
        
        except Exception as e:
            logger.error(f"Error in event handler: {e}")


