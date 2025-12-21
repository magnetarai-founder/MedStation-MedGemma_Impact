"""
Error Codes and Custom Exceptions

Provides structured error handling for all API endpoints.
"""

from enum import Enum
from typing import Any, Optional
from fastapi import status


class ErrorCode(str, Enum):
    """
    Standard error codes for API responses.

    Use these codes for consistent client-side error handling.
    """
    # Client errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    BAD_REQUEST = "BAD_REQUEST"
    GONE = "GONE"

    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    GATEWAY_ERROR = "GATEWAY_ERROR"
    TIMEOUT = "TIMEOUT"


class APIError(Exception):
    """
    Base API error class.

    All custom API errors should inherit from this class.

    Attributes:
        code: Machine-readable error code
        message: Human-readable error message
        status_code: HTTP status code
        details: Additional error context (optional)

    Example:
        ```python
        raise APIError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid email format",
            status_code=400,
            details={"field": "email", "value": "invalid"}
        )
        ```
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int,
        details: Optional[dict] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationError(APIError):
    """
    Request validation error (400).

    Raised when request data fails validation.

    Example:
        ```python
        raise ValidationError(
            field="email",
            error="Invalid email format"
        )
        ```
    """

    def __init__(self, field: str, error: str):
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Validation error on field '{field}': {error}",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"field": field, "error": error}
        )


class NotFoundError(APIError):
    """
    Resource not found error (404).

    Raised when a requested resource doesn't exist.

    Example:
        ```python
        raise NotFoundError(
            resource="user",
            resource_id="123"
        )
        ```
    """

    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=f"{resource.capitalize()} with ID '{resource_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "resource_id": resource_id}
        )


class UnauthorizedError(APIError):
    """
    Authentication error (401).

    Raised when authentication is missing or invalid.

    Example:
        ```python
        raise UnauthorizedError(
            reason="Invalid JWT token"
        )
        ```
    """

    def __init__(self, reason: str = "Authentication required"):
        super().__init__(
            code=ErrorCode.UNAUTHORIZED,
            message=reason,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details={"reason": reason}
        )


class ForbiddenError(APIError):
    """
    Authorization error (403).

    Raised when user is authenticated but not authorized.

    Example:
        ```python
        raise ForbiddenError(
            action="delete_user",
            required_permission="users.delete"
        )
        ```
    """

    def __init__(self, action: str, required_permission: Optional[str] = None):
        message = f"You are not authorized to perform action: {action}"
        details = {"action": action}

        if required_permission:
            message += f" (requires permission: {required_permission})"
            details["required_permission"] = required_permission

        super().__init__(
            code=ErrorCode.FORBIDDEN,
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class ConflictError(APIError):
    """
    Resource conflict error (409).

    Raised when resource already exists or conflicts with existing data.

    Example:
        ```python
        raise ConflictError(
            resource="user",
            field="email",
            value="test@example.com"
        )
        ```
    """

    def __init__(self, resource: str, field: str, value: str):
        super().__init__(
            code=ErrorCode.CONFLICT,
            message=f"{resource.capitalize()} with {field}='{value}' already exists",
            status_code=status.HTTP_409_CONFLICT,
            details={"resource": resource, "field": field, "value": value}
        )


class RateLimitError(APIError):
    """
    Rate limit error (429).

    Raised when client exceeds rate limit.

    Example:
        ```python
        raise RateLimitError(
            retry_after=300  # 5 minutes
        )
        ```
    """

    def __init__(self, retry_after: int):
        super().__init__(
            code=ErrorCode.RATE_LIMITED,
            message=f"Rate limit exceeded. Retry after {retry_after} seconds",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after": retry_after}
        )


class ServiceUnavailableError(APIError):
    """
    Service unavailable error (503).

    Raised when an external service is unavailable.

    Example:
        ```python
        raise ServiceUnavailableError(
            service="ollama",
            reason="Connection refused"
        )
        ```
    """

    def __init__(self, service: str, reason: str):
        super().__init__(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message=f"Service '{service}' is unavailable: {reason}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"service": service, "reason": reason}
        )


class GatewayError(APIError):
    """
    Bad gateway error (502).

    Raised when upstream service returns invalid response.

    Example:
        ```python
        raise GatewayError(
            service="ollama",
            reason="Invalid response format"
        )
        ```
    """

    def __init__(self, service: str, reason: str):
        super().__init__(
            code=ErrorCode.GATEWAY_ERROR,
            message=f"Gateway error from '{service}': {reason}",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"service": service, "reason": reason}
        )


class TimeoutError(APIError):
    """
    Request timeout error (504).

    Raised when operation exceeds timeout.

    Example:
        ```python
        raise TimeoutError(
            operation="ollama_generate",
            timeout_seconds=30
        )
        ```
    """

    def __init__(self, operation: str, timeout_seconds: int):
        super().__init__(
            code=ErrorCode.TIMEOUT,
            message=f"Operation '{operation}' timed out after {timeout_seconds} seconds",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            details={"operation": operation, "timeout_seconds": timeout_seconds}
        )


# Helper function to convert APIError to HTTPException
def api_error_to_http_exception(error: APIError) -> Any:
    """
    Convert APIError to FastAPI HTTPException.

    Usage:
        ```python
        try:
            ...
        except APIError as e:
            raise api_error_to_http_exception(e)
        ```
    """
    from fastapi import HTTPException
    from .responses import ErrorResponse

    return HTTPException(
        status_code=error.status_code,
        detail=ErrorResponse(
            error_code=error.code,
            message=error.message,
            details=error.details
        ).model_dump()
    )
