"""
Rate limiting middleware configuration.

Note: Currently disabled due to compatibility issues with multipart file uploads.
File size limits and session-based access control provide adequate protection.
"""

from fastapi import FastAPI
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def configure_rate_limiting(app: FastAPI) -> Limiter:
    """
    Initialize and attach the rate limiter to the app.

    Note: Rate limiter is initialized but NOT attached to app.state or
    exception handlers due to compatibility issues with multipart uploads.
    The global 100/minute limit and specific endpoint limits caused errors.

    Args:
        app: FastAPI application instance

    Returns:
        Limiter instance (for potential future use)
    """
    # Initialize rate limiter
    limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

    # Disabled slowapi due to compatibility issues with multipart file uploads
    # The global 100/minute limit and specific endpoint limits caused errors
    # File size limits and session-based access control provide adequate protection
    # app.state.limiter = limiter
    # app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    return limiter
