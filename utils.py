"""
Utility functions for Substack Downloader
"""
import re
import hashlib
from typing import Optional
from config import MAX_FILENAME_LENGTH


def sanitize_filename(filename: str, max_length: int = MAX_FILENAME_LENGTH) -> str:
    """
    Sanitize a filename to be safe across platforms.

    Args:
        filename: The filename to sanitize
        max_length: Maximum filename length (default from config)

    Returns:
        Sanitized filename safe for all platforms

    Examples:
        >>> sanitize_filename("Hello/World")
        'Hello_World'
        >>> sanitize_filename("Test<>File")
        'TestFile'
        >>> sanitize_filename("")
        'unnamed'
    """
    if not filename or not filename.strip():
        return "unnamed"

    # Remove or replace path separators
    filename = re.sub(r'[/\\]', '_', filename)

    # Remove dangerous characters for Windows/Unix
    filename = re.sub(r'[<>:"|?*]', '', filename)

    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)

    # Trim whitespace and dots (Windows doesn't like trailing dots)
    filename = filename.strip('. ')

    # Limit length
    if len(filename) > max_length:
        # Keep extension if present
        parts = filename.rsplit('.', 1)
        if len(parts) == 2 and len(parts[1]) <= 10:
            # Has extension
            name, ext = parts
            max_name_len = max_length - len(ext) - 1
            filename = name[:max_name_len] + '.' + ext
        else:
            filename = filename[:max_length]

    return filename or "unnamed"


def get_cache_key(url: str) -> str:
    """
    Generate a cache key from a URL.

    Args:
        url: The URL to hash

    Returns:
        MD5 hash of the URL as hex string
    """
    return hashlib.md5(url.encode()).hexdigest()


def format_size(bytes_size: int) -> str:
    """
    Format bytes into human-readable size.

    Args:
        bytes_size: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"
