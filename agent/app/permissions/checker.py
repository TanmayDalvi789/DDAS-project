"""Permission validation - ENTRY POINT FOR FAIL-CLOSED BEHAVIOR."""

import logging
import platform
import socket

from app.permissions.errors import PermissionError, NetworkUnavailable
from app.permissions.guidance import get_guidance
from app.permissions.platform.windows import validate_windows_permissions
from app.permissions.platform.linux import validate_linux_permissions
from app.permissions.platform.macos import validate_macos_permissions

logger = logging.getLogger(__name__)


class PermissionValidator:
    """
    Validates system permissions BEFORE agent starts.
    
    FAIL-CLOSED: Raises PermissionError if validation fails.
    Agent cannot proceed without valid permissions.
    
    Validations:
    1. OS admin/root privileges
    2. Download directory read access
    3. Cache directory write access
    4. Backend network connectivity
    """
    
    def __init__(self, backend_host: str = "localhost", backend_port: int = 8001):
        """Initialize validator with backend connection info."""
        self.backend_host = backend_host
        self.backend_port = backend_port
        self.platform = platform.system()
    
    def _validate_network(self):
        """
        Check network reachability to backend API.
        
        Raises:
            NetworkUnavailable: If backend is not reachable
        """
        try:
            # Fast socket connection check (no HTTP overhead)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)  # 2 second timeout
            result = sock.connect_ex((self.backend_host, self.backend_port))
            sock.close()
            
            if result != 0:
                raise NetworkUnavailable(
                    f"Cannot reach backend at {self.backend_host}:{self.backend_port}"
                )
            
            logger.info(f"Backend connectivity: OK ({self.backend_host}:{self.backend_port})")
            
        except Exception as e:
            raise NetworkUnavailable(f"Network error: {e}") from e
    
    def validate_all(self):
        """
        Validate all required permissions for current platform.
        
        Execution order:
        1. Platform-specific checks (admin, file access)
        2. Network connectivity
        
        Raises:
            PermissionError: If any required permission is missing
        """
        logger.info(f"Starting permission validation ({self.platform})...")
        
        try:
            # Platform-specific validation
            if self.platform == "Windows":
                validate_windows_permissions()
            elif self.platform == "Linux":
                validate_linux_permissions()
            elif self.platform == "Darwin":
                validate_macos_permissions()
            else:
                raise PermissionError(f"Unsupported platform: {self.platform}")
            
            logger.info("Platform-specific checks: PASS")
            
            # Network validation
            self._validate_network()
            
            logger.info("✓ All permissions validated")
            
        except PermissionError as e:
            # Log full error for debugging
            logger.error(f"Permission validation failed: {e}")
            
            # Extract error type for guidance lookup
            error_msg = str(e)
            if "admin" in error_msg.lower():
                guidance = get_guidance("admin_required", self.platform)
            elif "downloads" in error_msg.lower() or "read" in error_msg.lower():
                guidance = get_guidance("download_dir_access", self.platform)
            elif "cache" in error_msg.lower() or "write" in error_msg.lower():
                guidance = get_guidance("cache_dir_access", self.platform)
            elif "network" in error_msg.lower() or "backend" in error_msg.lower():
                guidance = get_guidance("network_unreachable", self.platform)
            else:
                guidance = str(e)
            
            # Log guidance for user
            logger.error(f"\nPLEASE FIX:\n{guidance}")
            
            # Re-raise original error
            raise
        
        except Exception as e:
            logger.error(f"Permission validation error: {e}", exc_info=True)
            raise PermissionError(f"Unexpected error during validation: {e}") from e
