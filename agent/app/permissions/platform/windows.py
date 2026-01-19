"""Windows permission validation."""

import logging
import ctypes
import os
from pathlib import Path

from app.permissions.errors import PermissionError, FileAccessDenied, DatabaseAccessDenied

logger = logging.getLogger(__name__)


def is_admin():
    """Check if running with admin privileges."""
    try:
        return ctypes.windll.shell.IsUserAnAdmin()
    except Exception:
        return False


def check_downloads_access():
    """
    Check read access to Windows Downloads folder.
    
    Raises:
        FileAccessDenied: If Downloads folder is not accessible
    """
    downloads_path = Path.home() / "Downloads"
    
    try:
        # Check if directory exists and is readable
        if not downloads_path.exists():
            raise FileAccessDenied(f"Downloads folder not found: {downloads_path}")
        
        # Try to list files (basic read permission test)
        list(downloads_path.iterdir())
        logger.info(f"Downloads access: OK ({downloads_path})")
        
    except PermissionError as e:
        raise FileAccessDenied(f"Cannot read Downloads folder: {e}")
    except Exception as e:
        raise FileAccessDenied(f"Downloads folder error: {e}")


def check_cache_access():
    """
    Check write access to cache directory.
    
    Raises:
        DatabaseAccessDenied: If cache directory is not writable
    """
    cache_dir = Path.home() / "AppData" / "Local" / ".ddas"
    
    try:
        # Create cache directory if needed
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to create a test file
        test_file = cache_dir / ".test_write"
        test_file.touch()
        test_file.unlink()
        
        logger.info(f"Cache access: OK ({cache_dir})")
        
    except PermissionError as e:
        raise DatabaseAccessDenied(f"Cannot write to cache directory: {e}")
    except Exception as e:
        raise DatabaseAccessDenied(f"Cache directory error: {e}")


def validate_windows_permissions():
    """
    Validate Windows-specific permissions.
    
    Checks:
    1. Admin privileges
    2. Downloads folder read access
    3. Cache directory write access
    
    Raises:
        PermissionError: If any validation fails
    """
    logger.info("Validating Windows permissions...")
    
    # Check 1: Admin
    if not is_admin():
        raise PermissionError(
            "Windows: Agent requires admin privileges. "
            "Please run as Administrator."
        )
    logger.debug("Admin check: PASS")
    
    # Check 2: Downloads access
    check_downloads_access()
    logger.debug("Downloads access check: PASS")
    
    # Check 3: Cache access
    check_cache_access()
    logger.debug("Cache access check: PASS")
    
    logger.info("All Windows permissions validated")
