"""Agent configuration from environment variables."""

import os
from pathlib import Path
from pydantic import BaseModel


class Config(BaseModel):
    """Agent configuration."""
    
    # Backend API
    backend_base_url: str = os.getenv("BACKEND_BASE_URL", "http://localhost:8001")
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:8001")
    backend_api_key: str = os.getenv("BACKEND_API_KEY", "")
    
    # Agent identity
    agent_id: str = os.getenv("AGENT_ID", "agent-001")
    agent_name: str = os.getenv("AGENT_NAME", "DDAS-Agent-Local")
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Cache
    cache_path: str = os.getenv("CACHE_PATH", str(Path.home() / ".ddas" / "agent" / "cache.db"))
    
    # Proxy
    proxy_host: str = os.getenv("PROXY_HOST", "localhost")
    proxy_port: int = int(os.getenv("PROXY_PORT", "8080"))
    proxy_event_port: int = int(os.getenv("PROXY_EVENT_PORT", "9999"))
    
    # Feature Extraction (STEP-4)
    feature_partial_hash_bytes: int = int(os.getenv("FEATURE_PARTIAL_HASH_BYTES", "4194304"))  # 4 MB default
    
    # Enforcement and UI (STEP-7)
    ui_notifications_enabled: bool = os.getenv("UI_NOTIFICATIONS_ENABLED", "true").lower() == "true"
    ui_warn_timeout: int = int(os.getenv("UI_WARN_TIMEOUT", "5"))  # Seconds
    ui_block_timeout: int = int(os.getenv("UI_BLOCK_TIMEOUT", "10"))  # Seconds
    ui_allow_timeout: int = int(os.getenv("UI_ALLOW_TIMEOUT", "3"))  # Seconds
    warn_confirmation_timeout: int = int(os.getenv("WARN_CONFIRMATION_TIMEOUT", "10"))  # Seconds
    allow_enforcement: bool = os.getenv("ALLOW_ENFORCEMENT_ENABLED", "false").lower() == "true"
    warn_enforcement: bool = os.getenv("WARN_ENFORCEMENT_ENABLED", "true").lower() == "true"
    block_enforcement: bool = os.getenv("BLOCK_ENFORCEMENT_ENABLED", "true").lower() == "true"
    
    # Permissions
    permissions_validation_enabled: bool = os.getenv("PERMISSIONS_VALIDATION_ENABLED", "true").lower() == "true"
    permissions_fail_closed: bool = os.getenv("PERMISSIONS_FAIL_CLOSED", "true").lower() == "true"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
