"""Backend agent registration client."""

import logging
import requests
import socket
import platform
import uuid
from typing import Optional

from app import __version__
from app.constants import BACKEND_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class RegistrationClient:
    """
    Client for agent registration with backend.
    
    Registration happens once on first startup.
    Backend confirms agent_id and provides initial config.
    """
    
    def __init__(self, backend_url: str, auth_headers: dict):
        """Initialize registration client."""
        self.backend_url = backend_url
        self.auth_headers = auth_headers
    
    def register_agent(self, agent_id: str, agent_name: str) -> Optional[dict]:
        """
        Register agent with backend.
        
        Args:
            agent_id: Agent identifier (UUID or custom)
            agent_name: Human-readable agent name
        
        Returns:
            dict: Registration response or None on failure
            {
                "agent_id": "uuid-xxx",
                "status": "registered",
                "config": {...},
            }
        """
        try:
            url = f"{self.backend_url}/api/v1/agent/register"
            
            payload = {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "hostname": socket.gethostname(),
                "os_type": platform.system(),
                "os_version": platform.release(),
                "agent_version": __version__,
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=self.auth_headers,
                timeout=BACKEND_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Agent registered: {agent_id}")
            return result
            
        except requests.RequestException as e:
            logger.error(f"Agent registration failed: {e}")
            return None
