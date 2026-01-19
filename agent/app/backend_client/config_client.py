"""Backend config client - Fetch agent configuration."""

import logging
import requests
from typing import Optional

from app.constants import BACKEND_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class ConfigClient:
    \"\"\"\n    Client for fetching agent-specific configuration from backend.\n    \n    Fetches:\n    - Decision thresholds per agent\n    - Feature extraction parameters\n    - Notification settings\n    \n    Config is cached in memory, not persisted.\n    \"\"\"\n    \n    def __init__(self, backend_url: str, auth_headers: dict):\n        \"\"\"Initialize config client.\"\"\"\n        self.backend_url = backend_url\n        self.auth_headers = auth_headers\n        self._config_cache = None  # In-memory cache\n    \n    def fetch_config(self, agent_id: str) -> Optional[dict]:\n        \"\"\"\n        Fetch agent configuration from backend.\n        \n        Args:\n            agent_id: Agent identifier\n        \n        Returns:\n            dict: Configuration or None on failure\n            {\n                \"thresholds\": {\n                    \"allow\": 0.95,\n                    \"warn\": 0.75,\n                    \"block\": 0.50,\n                },\n                \"features_enabled\": [\"exact\", \"fuzzy\", \"semantic\"],\n                \"notification_enabled\": true,\n                \"heartbeat_interval\": 60,\n            }\n        \"\"\"\n        try:\n            url = f\"{self.backend_url}/api/v1/agent/config\"\n            response = requests.get(\n                url,\n                params={\"agent_id\": agent_id},\n                headers=self.auth_headers,\n                timeout=BACKEND_TIMEOUT_SECONDS,\n            )\n            response.raise_for_status()\n            \n            config = response.json()\n            self._config_cache = config  # Cache in memory\n            logger.info(\"Config fetched from backend\")\n            return config\n            \n        except requests.RequestException as e:\n            logger.warning(f\"Failed to fetch config: {e}\")\n            # Return cached config if available\n            if self._config_cache:\n                logger.info(\"Using cached config\")\n                return self._config_cache\n            return None\n    \n    def get_cached_config(self) -> Optional[dict]:\n        \"\"\"Get in-memory cached configuration.\"\"\"\n        return self._config_cache
