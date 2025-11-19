"""
Middleware package for FastAPI application.

Centralizes middleware configuration and registration:
- CORS configuration
- Rate limiting
- Error handlers
- Request ID tracking
"""

from .cors import configure_cors
from .rate_limit import configure_rate_limiting
from .error_handlers import register_error_handlers

__all__ = [
    "configure_cors",
    "configure_rate_limiting",
    "register_error_handlers",
]
