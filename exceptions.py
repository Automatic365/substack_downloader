"""Custom exceptions for Substack Downloader."""


class SubstackError(Exception):
    """Base error for Substack downloader."""


class AuthenticationError(SubstackError):
    """Authentication failed or required."""


class RateLimitError(SubstackError):
    """Rate limit encountered."""


class NetworkError(SubstackError):
    """Network or server error."""
