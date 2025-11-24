"""
Custom exceptions for MagnetarStudio API.

Provides structured error handling with consistent error codes and messages.
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class MagnetarException(Exception):
    """Base exception for all MagnetarStudio errors."""

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
