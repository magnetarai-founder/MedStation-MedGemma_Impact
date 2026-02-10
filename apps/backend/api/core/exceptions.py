"""
Custom exceptions for MedStation API.

Provides structured error handling with consistent error codes and messages.
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class MagnetarException(Exception):
    """Base exception for all MedStation errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_http_exception(self) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        return HTTPException(
            status_code=self.status_code,
            detail={
                "code": self.code,
                "message": self.message,
                "details": self.details
            }
        )


# Authentication & Authorization Exceptions
class AuthenticationError(MagnetarException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class AuthorizationError(MagnetarException):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials are invalid."""

    def __init__(self):
        super().__init__(
            message="Invalid username or password",
            details={"hint": "Check your credentials and try again"}
        )


class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired."""

    def __init__(self):
        super().__init__(
            message="Token has expired",
            details={"hint": "Please log in again"}
        )


# Resource Exceptions
class ResourceNotFoundError(MagnetarException):
    """Raised when a requested resource doesn't exist."""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} not found",
            code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource_type": resource_type, "id": resource_id}
        )


class ResourceAlreadyExistsError(MagnetarException):
    """Raised when attempting to create a duplicate resource."""

    def __init__(self, resource_type: str, identifier: str):
        super().__init__(
            message=f"{resource_type} already exists",
            code="RESOURCE_ALREADY_EXISTS",
            status_code=status.HTTP_409_CONFLICT,
            details={"resource_type": resource_type, "identifier": identifier}
        )


# Validation Exceptions
class ValidationError(MagnetarException):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        error_details = details or {}
        if field:
            error_details["field"] = field

        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=error_details
        )


# Storage Exceptions
class StorageError(MagnetarException):
    """Raised when file storage operations fail."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="STORAGE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class QuotaExceededError(MagnetarException):
    """Raised when storage quota is exceeded."""

    def __init__(self, used: int, limit: int):
        super().__init__(
            message="Storage quota exceeded",
            code="QUOTA_EXCEEDED",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            details={"used_bytes": used, "limit_bytes": limit}
        )


# Database Exceptions
class DatabaseError(MagnetarException):
    """Raised when database operations fail."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


# Rate Limiting
class RateLimitExceededError(MagnetarException):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: int):
        super().__init__(
            message="Rate limit exceeded",
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after_seconds": retry_after}
        )


class ServiceUnavailableError(MagnetarException):
    """Raised when service is temporarily unavailable."""

    def __init__(self, message: str = "Service temporarily unavailable", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="SERVICE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class TimeoutError(MagnetarException):
    """Raised when an operation times out."""

    def __init__(self, message: str = "Operation timed out", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="TIMEOUT",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            details=details
        )


# ===== Exception Handler Utilities =====

import functools
import logging
import sqlite3
import asyncio
from pydantic import ValidationError as PydanticValidationError

_handler_logger = logging.getLogger(__name__)


def handle_exceptions(
    operation_name: str,
    *,
    resource_type: Optional[str] = None,
    reraise_http: bool = True
):
    """
    Decorator that maps standard Python exceptions to appropriate HTTP responses.

    This decorator provides consistent exception handling across API endpoints by:
    1. Letting HTTPException and MagnetarException pass through (already HTTP-aware)
    2. Mapping standard Python exceptions to appropriate HTTP status codes
    3. Logging all errors with full context

    Args:
        operation_name: Human-readable name for logging (e.g., "get profile")
        resource_type: Optional resource type for 404 errors (e.g., "Profile")
        reraise_http: Whether to re-raise HTTPException as-is (default True)

    Exception Mapping:
        - ValueError, TypeError, PydanticValidationError -> 422 Unprocessable Entity
        - KeyError, LookupError -> 404 Not Found (if resource_type given) or 422
        - PermissionError -> 403 Forbidden
        - sqlite3.Error -> 500 Database Error
        - asyncio.TimeoutError -> 504 Gateway Timeout
        - MemoryError, OSError -> 503 Service Unavailable
        - Exception -> 500 Internal Server Error

    Usage:
        @router.get("/profiles/{profile_id}")
        @handle_exceptions("get profile", resource_type="Profile")
        async def get_profile(profile_id: str):
            return await service.get_profile(profile_id)

    Note:
        Apply AFTER route decorator but BEFORE the function definition.
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                if reraise_http:
                    raise
                # Convert to MagnetarException format if not reraising
                raise
            except MagnetarException:
                # Already well-typed, just re-raise
                raise
            except PydanticValidationError as e:
                _handler_logger.warning(f"Validation error in {operation_name}: {e}")
                raise ValidationError(
                    message="Invalid input data",
                    details={"errors": e.errors()}
                ).to_http_exception()
            except (ValueError, TypeError) as e:
                _handler_logger.warning(f"Validation error in {operation_name}: {e}")
                raise ValidationError(
                    message=str(e) if str(e) else "Invalid input"
                ).to_http_exception()
            except (KeyError, LookupError) as e:
                if resource_type:
                    _handler_logger.warning(f"Resource not found in {operation_name}: {e}")
                    raise ResourceNotFoundError(
                        resource_type=resource_type,
                        resource_id=str(e)
                    ).to_http_exception()
                else:
                    _handler_logger.warning(f"Lookup error in {operation_name}: {e}")
                    raise ValidationError(
                        message=f"Required key not found: {e}"
                    ).to_http_exception()
            except PermissionError as e:
                _handler_logger.warning(f"Permission denied in {operation_name}: {e}")
                raise AuthorizationError(
                    message=str(e) if str(e) else "Permission denied"
                ).to_http_exception()
            except sqlite3.Error as e:
                _handler_logger.error(f"Database error in {operation_name}: {e}", exc_info=True)
                raise DatabaseError(
                    message="Database operation failed"
                ).to_http_exception()
            except asyncio.TimeoutError as e:
                _handler_logger.error(f"Timeout in {operation_name}: {e}")
                raise TimeoutError(
                    message=f"Operation timed out: {operation_name}"
                ).to_http_exception()
            except (MemoryError, OSError) as e:
                _handler_logger.error(f"Resource error in {operation_name}: {e}", exc_info=True)
                raise ServiceUnavailableError(
                    message="Insufficient system resources"
                ).to_http_exception()
            except Exception as e:
                # Catch-all for unexpected errors - log full traceback
                _handler_logger.error(
                    f"Unexpected error in {operation_name}: {type(e).__name__}: {e}",
                    exc_info=True
                )
                raise MagnetarException(
                    message=f"An unexpected error occurred during {operation_name}",
                    code="INTERNAL_ERROR"
                ).to_http_exception()

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except HTTPException:
                if reraise_http:
                    raise
                raise
            except MagnetarException:
                raise
            except PydanticValidationError as e:
                _handler_logger.warning(f"Validation error in {operation_name}: {e}")
                raise ValidationError(
                    message="Invalid input data",
                    details={"errors": e.errors()}
                ).to_http_exception()
            except (ValueError, TypeError) as e:
                _handler_logger.warning(f"Validation error in {operation_name}: {e}")
                raise ValidationError(
                    message=str(e) if str(e) else "Invalid input"
                ).to_http_exception()
            except (KeyError, LookupError) as e:
                if resource_type:
                    _handler_logger.warning(f"Resource not found in {operation_name}: {e}")
                    raise ResourceNotFoundError(
                        resource_type=resource_type,
                        resource_id=str(e)
                    ).to_http_exception()
                else:
                    _handler_logger.warning(f"Lookup error in {operation_name}: {e}")
                    raise ValidationError(
                        message=f"Required key not found: {e}"
                    ).to_http_exception()
            except PermissionError as e:
                _handler_logger.warning(f"Permission denied in {operation_name}: {e}")
                raise AuthorizationError(
                    message=str(e) if str(e) else "Permission denied"
                ).to_http_exception()
            except sqlite3.Error as e:
                _handler_logger.error(f"Database error in {operation_name}: {e}", exc_info=True)
                raise DatabaseError(
                    message="Database operation failed"
                ).to_http_exception()
            except (MemoryError, OSError) as e:
                _handler_logger.error(f"Resource error in {operation_name}: {e}", exc_info=True)
                raise ServiceUnavailableError(
                    message="Insufficient system resources"
                ).to_http_exception()
            except Exception as e:
                _handler_logger.error(
                    f"Unexpected error in {operation_name}: {type(e).__name__}: {e}",
                    exc_info=True
                )
                raise MagnetarException(
                    message=f"An unexpected error occurred during {operation_name}",
                    code="INTERNAL_ERROR"
                ).to_http_exception()

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
