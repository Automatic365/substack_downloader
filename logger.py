"""
Logging setup for Substack Downloader
"""
import logging
import sys
import re
from config import LOG_LEVEL, LOG_FORMAT, LOG_FILE


class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive data from logs"""

    def filter(self, record):
        """Redact cookies and other sensitive data from log messages"""
        if hasattr(record, 'msg'):
            msg = str(record.msg)
            # Redact cookie values
            msg = re.sub(
                r'(Cookie|substack\.sid)[=:]\s*[^\s;,\'"]+',
                r'\1=***REDACTED***',
                msg,
                flags=re.IGNORECASE
            )
            # Redact authorization headers
            msg = re.sub(
                r'(Authorization|Bearer)[=:]\s*[^\s;,\'"]+',
                r'\1=***REDACTED***',
                msg,
                flags=re.IGNORECASE
            )
            record.msg = msg
        return True


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

        # Create sensitive data filter
        sensitive_filter = SensitiveDataFilter()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(sensitive_filter)  # Add security filter
        logger.addHandler(console_handler)

        # File handler (if configured)
        if LOG_FILE:
            file_handler = logging.FileHandler(LOG_FILE)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            file_handler.addFilter(sensitive_filter)  # Add security filter
            logger.addHandler(file_handler)

    return logger
