"""
Centralized logging configuration for the EVE Online App.
"""
import logging
import sys
from typing import Optional

# Configure logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(
    name: str,
    level: int = logging.INFO,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """
    Set up and configure a logger.

    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: INFO)
        format_string: Custom format string (optional)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Formatter
    formatter = logging.Formatter(
        format_string or LOG_FORMAT,
        datefmt=DATE_FORMAT
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    return logger


# Default application logger
logger = setup_logger("eve-app", level=logging.INFO)
