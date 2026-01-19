"""Backend API authentication."""

import logging

logger = logging.getLogger(__name__)


class BackendAuth:
    """
    Authentication with backend API.
    
    Handles:
    - API key loading from config
    - Authorization headers
    """
    
    def __init__(self, api_key: str):
        """Initialize with API key."""
        self.api_key = api_key
        if not api_key:
            logger.warning("Backend API key not configured")
    
    def get_headers(self) -> dict:
        """
        Get authentication headers for backend requests.
        
        Returns:
            dict: Headers with Authorization and Content-Type
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

