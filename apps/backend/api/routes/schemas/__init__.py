"""
API Schemas - Standard Request/Response Models

Provides consistent data structures for all API endpoints.
"""

from .responses import SuccessResponse, ErrorResponse
from .errors import ErrorCode, APIError, NotFoundError, ValidationError, UnauthorizedError, ForbiddenError

__all__ = [
    "SuccessResponse",
    "ErrorResponse",
    "ErrorCode",
    "APIError",
    "NotFoundError",
    "ValidationError",
    "UnauthorizedError",
    "ForbiddenError",
]
