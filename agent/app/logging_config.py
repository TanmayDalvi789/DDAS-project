"""Logging configuration."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_level: str = "INFO"):
    """Setup logging for agent."""
    
    # Create logs directory
    logs_dir = Path.home() / ".ddas" / "agent" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s] %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    file_handler = RotatingFileHandler(
        logs_dir / "agent.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s] %(funcName)s:%(lineno)d %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
