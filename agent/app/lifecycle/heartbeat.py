"""Agent heartbeat loop - Background thread."""

import logging
import threading
import time
from typing import Optional
import requests

logger = logging.getLogger(__name__)


class HeartbeatLoop:
    """
    Periodic agent heartbeat.
    
    Runs in background thread.
    
    Responsibilities:
    - Report agent status to backend (RUNNING / DEGRADED)
    - Sync configuration from backend
    - Non-blocking on main thread
    """
    
    def __init__(
        self,
        agent_id: str,
        backend_url: str,
        auth_headers: dict,
        interval_seconds: int = 60,
    ):
        """
        Initialize heartbeat loop.
        
        Args:
            agent_id: Agent identifier
            backend_url: Backend API base URL
            auth_headers: Authentication headers
            interval_seconds: Heartbeat interval (default 60s)
        """
        self.agent_id = agent_id
        self.backend_url = backend_url
        self.auth_headers = auth_headers
        self.interval_seconds = interval_seconds
        
        self._running = False
        self._thread = None
    
    def start(self):
        """Start heartbeat loop in background thread."""
        if self._running:
            logger.warning("Heartbeat already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()
        logger.info(f"Heartbeat started (interval={self.interval_seconds}s)\")\n    \n    def stop(self):\n        \"\"\"Stop heartbeat loop gracefully.\"\"\"\n        self._running = False\n        if self._thread:\n            self._thread.join(timeout=5)\n        logger.info(\"Heartbeat stopped\")\n    \n    def _heartbeat_loop(self):\n        \"\"\"Background heartbeat loop (runs in thread).\"\"\"\n        while self._running:\n            try:\n                self._send_heartbeat()\n            except Exception as e:\n                logger.error(f\"Heartbeat error: {e}\")\n            \n            # Sleep for interval or until stop requested\n            for _ in range(self.interval_seconds):\n                if not self._running:\n                    return\n                time.sleep(1)\n    \n    def _send_heartbeat(self) -> bool:\n        \"\"\"\n        Send heartbeat to backend.\n        \n        Returns:\n            bool: True if successful\n        \"\"\"\n        try:\n            url = f\"{self.backend_url}/api/v1/agent/heartbeat\"\n            \n            payload = {\n                \"agent_id\": self.agent_id,\n                \"status\": \"RUNNING\",\n                \"timestamp\": int(time.time()),\n            }\n            \n            response = requests.post(\n                url,\n                json=payload,\n                headers=self.auth_headers,\n                timeout=5,  # Short timeout for non-blocking behavior\n            )\n            response.raise_for_status()\n            \n            logger.debug(f\"Heartbeat sent successfully\")\n            return True\n            \n        except requests.RequestException as e:\n            # Log warning but don't crash — agent continues running\n            logger.warning(f\"Heartbeat failed (will retry): {e}\")\n            return False\n
