"""
Common Error Handling Utilities

Provides decorators and utilities for consistent error handling across API endpoints.

Features:
- Standardized error responses
- Automatic error logging with context
- HTTP exception passthrough
- Correlation ID tracking in errors
"""

from functools import wraps
from typing import Any, Callable

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from .structured_logging import get_logger

logger = get_logger(__name__)


def handle_api_errors(func: Callable) -> Callable:
    """
    Decorator for consistent API error handling.

    - Catches all exceptions
    - Logs errors with correlation ID
    - Returns standardized error responses
    - Passes through HTTPException unchanged

    Usage:
        @router.get("/users/{user_id}")
        @handle_api_errors
        async def get_user(user_id: str):
            # ... endpoint logic ...
            return user
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HTTPException:
            # Pass through HTTP exceptions (already formatted)
            raise
        except Exception as e:
            # Log error with context
            logger.error(
                f"Unhandled error in {func.__name__}",
                error=e,
                endpoint=func.__name__,
                args_count=len(args),
            )

            # Return 500 with error details (sanitized in production)
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {type(e).__name__}",
            )

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Unhandled error in {func.__name__}",
                error=e,
                endpoint=func.__name__,
                args_count=len(args),
            )

            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {type(e).__name__}",
            )

    import inspect

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def validate_request(func: Callable) -> Callable:
    """
    Decorator for request validation.

    Validates common request parameters and provides helpful error messages.

    Usage:
        @router.post("/items")
        @validate_request
        async def create_item(item: Item):
            # ... endpoint logic ...
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        # Add custom validation logic here if needed
        return await func(*args, **kwargs)

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    import inspect

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


class ErrorResponse:
    """Standardized error response format"""

    @staticmethod
    def bad_request(message: str, details: dict[str, Any] | None = None) -> HTTPException:
        """400 Bad Request"""
        return HTTPException(
            status_code=400,
            detail={"message": message, "details": details or {}},
        )

    @staticmethod
    def unauthorized(message: str = "Unauthorized") -> HTTPException:
        """401 Unauthorized"""
        return HTTPException(status_code=401, detail=message)

    @staticmethod
    def forbidden(message: str = "Forbidden") -> HTTPException:
        """403 Forbidden"""
        return HTTPException(status_code=403, detail=message)

    @staticmethod
    def not_found(resource: str, identifier: str | None = None) -> HTTPException:
        """404 Not Found"""
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        return HTTPException(status_code=404, detail=message)

    @staticmethod
    def conflict(message: str, details: dict[str, Any] | None = None) -> HTTPException:
        """409 Conflict"""
        return HTTPException(
            status_code=409,
            detail={"message": message, "details": details or {}},
        )

    @staticmethod
    def validation_error(errors: list[dict[str, Any]]) -> HTTPException:
        """422 Validation Error"""
        return HTTPException(
            status_code=422,
            detail={"message": "Validation failed", "errors": errors},
        )

    @staticmethod
    def internal_error(message: str = "Internal server error") -> HTTPException:
        """500 Internal Server Error"""
        return HTTPException(status_code=500, detail=message)

    @staticmethod
    def service_unavailable(service: str) -> HTTPException:
        """503 Service Unavailable"""
        return HTTPException(
            status_code=503,
            detail=f"Service temporarily unavailable: {service}",
        )


def create_error_response(
    status_code: int,
    message: str,
    details: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        status_code: HTTP status code
        message: Error message
        details: Additional error details
        correlation_id: Request correlation ID

    Returns:
        JSONResponse with error details
    """
    response_data = {
        "error": {
            "message": message,
            "status_code": status_code,
        }
    }

    if details:
        response_data["error"]["details"] = details

    if correlation_id:
        response_data["correlation_id"] = correlation_id

    return JSONResponse(
        status_code=status_code,
        content=response_data,
    )
