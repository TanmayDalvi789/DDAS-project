"""Permission guidance - Human-readable error messages."""

import logging

logger = logging.getLogger(__name__)

# Error message mappings
ERROR_GUIDANCE = {
    "admin_required": {
        "Windows": "DDAS Agent requires admin privileges.\n"
                   "Please run: Right-click CMD > Run as Administrator > ddas-agent",
        "Linux": "DDAS Agent requires root or CAP_SYS_ADMIN capability.\n"
                 "Please run: sudo ddas-agent",
        "Darwin": "DDAS Agent requires admin to start.\n"
                  "Please run: sudo ddas-agent",
    },
    "download_dir_access": {
        "Windows": "Cannot access download directory.\n"
                   "Check: Downloads folder exists and is readable\n"
                   "Fix: Run as Administrator and ensure folder permissions",
        "Linux": "Cannot access download directory.\n"
                 "Check: sudo ls -la ~/Downloads\n"
                 "Fix: Grant read permissions: chmod +r ~/Downloads",
        "Darwin": "Cannot access Downloads directory.\n"
                  "Check: System Preferences > Security & Privacy > Full Disk Access\n"
                  "Fix: Add Terminal or app to Full Disk Access list",
    },
    "cache_dir_access": {
        "Windows": "Cannot access cache directory (%APPDATA%\\.ddas).\n"
                   "Fix: Run as Administrator and ensure write permissions",
        "Linux": "Cannot access cache directory (~/.ddas).\n"
                 "Fix: Run: mkdir -p ~/.ddas && chmod 700 ~/.ddas",
        "Darwin": "Cannot access cache directory (~/.ddas).\n"
                  "Fix: Run: mkdir -p ~/.ddas && chmod 700 ~/.ddas",
    },
    "network_unreachable": {
        "Windows": "Cannot reach backend API. Check:\n"
                   "1. Backend is running (http://localhost:8001)\n"
                   "2. Network connection is active\n"
                   "3. Firewall allows local connections",
        "Linux": "Cannot reach backend API. Check:\n"
                 "1. Backend is running (http://localhost:8001)\n"
                 "2. Network connection is active\n"
                 "3. Firewall allows local connections",
        "Darwin": "Cannot reach backend API. Check:\n"
                  "1. Backend is running (http://localhost:8001)\n"
                  "2. Network connection is active\n"
                  "3. Firewall allows local connections",
    },
}


def get_guidance(error_type: str, platform: str) -> str:
    """
    Get human-readable guidance for a specific error.
    
    Args:
        error_type: Error category (admin_required, download_dir_access, etc)
        platform: OS name (Windows, Linux, Darwin)
    
    Returns:
        str: Formatted instruction text
    """
    if error_type not in ERROR_GUIDANCE:
        return f"Permission error: {error_type}"
    
    platform_guidance = ERROR_GUIDANCE[error_type].get(
        platform,
        ERROR_GUIDANCE[error_type].get("Linux", "Please check permissions")
    )
    
    return platform_guidance
