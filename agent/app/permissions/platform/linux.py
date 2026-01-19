"""Linux permission validation."""

import logging
import os
from pathlib import Path

from app.permissions.errors import PermissionError, FileAccessDenied, DatabaseAccessDenied

logger = logging.getLogger(__name__)


def is_root():
    """Check if running as root."""
    return os.geteuid() == 0 if hasattr(os, "geteuid") else False


def check_downloads_access():
    """
    Check read access to Downloads folder.
    
    Raises:
        FileAccessDenied: If Downloads folder is not accessible
    """
    downloads_path = Path.home() / "Downloads"
    
    try:
        # Check if directory exists and is readable
        if not downloads_path.exists():
            # Downloads folder optional on Linux
            logger.warning(f"Downloads folder not found: {downloads_path}")
            return
        
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
    cache_dir = Path.home() / ".ddas"
    
    try:
        # Create cache directory if needed
        cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        # Try to create a test file
        test_file = cache_dir / ".test_write"
        test_file.touch(mode=0o600)
        test_file.unlink()
        
        logger.info(f"Cache access: OK ({cache_dir})")
        
    except PermissionError as e:
        raise DatabaseAccessDenied(f"Cannot write to cache directory: {e}")
    except Exception as e:
        raise DatabaseAccessDenied(f"Cache directory error: {e}")


def validate_linux_permissions():
    """
    Validate Linux-specific permissions.
    
    Checks:
    1. Root privileges
    2. Downloads folder read access
    3. Cache directory write access
    
    Raises:
        PermissionError: If any validation fails
    """
    logger.info("Validating Linux permissions...")
    
    # Check 1: Root
    if not is_root():
        raise PermissionError(
            "Linux: Agent requires root privileges or CAP_SYS_ADMIN. "
            "Please run with: sudo ddas-agent"
        )
    logger.debug("Root check: PASS")
    
    # Check 2: Downloads access (best-effort)
    try:
        check_downloads_access()
        logger.debug("Downloads access check: PASS")
    except FileAccessDenied as e:
        logger.warning(f"Downloads check failed (non-fatal): {e}")
    
    # Check 3: Cache access
    check_cache_access()
    logger.debug("Cache access check: PASS")
    
    logger.info("All Linux permissions validated")
