"""DDAS Agent - Local system service entry point."""

import sys
import logging

from app.config import Config
from app.logging_config import setup_logging
from app.lifecycle.startup import bootstrap_agent
from app.permissions.errors import PermissionError


logger = logging.getLogger(__name__)


def main():
    """
    Main agent entry point.
    
    Flow:
    1. Load configuration
    2. Setup logging
    3. Call bootstrap_agent which:
       - Validates permissions (FAIL-CLOSED at startup)
       - Initializes cache database
       - Connects to backend API
       - Starts event listener
       - Starts heartbeat loop
    """
    try:
        # Load config from environment
        config = Config()
        
        # Setup logging
        setup_logging(config.log_level)
        logger.info("DDAS Agent starting...")
        
        # Bootstrap agent (includes permission validation as STEP 1)
        bootstrap_agent(config)
        
    except PermissionError as e:
        logger.error(f"Agent startup failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Agent startup failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
