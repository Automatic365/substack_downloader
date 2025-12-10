"""
Logging setup for Substack Downloader
"""
import logging
import sys
from config import LOG_LEVEL, LOG_FORMAT, LOG_FILE


def setup_logger(name: str) -> logging.Logger:
    """
    Set up and return a logger with consistent formatting.

    Args:
        name: Name of the logger (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

        # Create formatter
        formatter = logging.Formatter(LOG_FORMAT)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler (if configured)
        if LOG_FILE:
            file_handler = logging.FileHandler(LOG_FILE)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger
