"""macOS permission validation."""

import logging
import os
import subprocess
from pathlib import Path

from app.permissions.errors import PermissionError, FileAccessDenied, DatabaseAccessDenied

logger = logging.getLogger(__name__)


def check_downloads_access():
    """
    Check read access to macOS Downloads folder.
    
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
        raise FileAccessDenied(f"Cannot read Downloads folder (check Full Disk Access): {e}")
    except FileAccessDenied:
        raise
    except Exception as e:
        raise FileAccessDenied(f"Downloads folder error: {e}")


def check_cache_access():
    """
    Check write access to macOS cache directory.
    
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


def validate_macos_permissions():
    """
    Validate macOS-specific permissions.
    
    Checks:
    1. Downloads folder read access (Full Disk Access)
    2. Cache directory write access
    
    Note: System Extension and Accessibility permissions are
    requested separately through system prompts on first run.
    
    Raises:
        PermissionError: If any validation fails
    """
    logger.info("Validating macOS permissions...")
    
    # Check 1: Downloads access (requires Full Disk Access)
    check_downloads_access()
    logger.debug("Downloads access check (Full Disk Access): PASS")
    
    # Check 2: Cache access
    check_cache_access()
    logger.debug("Cache access check: PASS")
    
    logger.info("All macOS permissions validated")
