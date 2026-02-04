"""
Standardized error handling utilities for API endpoints.

Provides custom exceptions and helper functions to eliminate duplication
in error handling across API routers.
"""

from typing import Any

from fastapi import HTTPException

# ===== Custom Exception Classes =====


class NotFoundError(HTTPException):
    """Resource not found (404)."""

    def __init__(self, resource: str, identifier: str | None = None):
        if identifier:
            detail = f"{resource} not found: {identifier}"
        else:
            detail = f"{resource} not found"
        super().__init__(status_code=404, detail=detail)


class ValidationError(HTTPException):
    """Validation error (400)."""

    def __init__(self, message: str, field: str | None = None):
        if field:
            detail = f"Validation error for '{field}': {message}"
        else:
            detail = f"Validation error: {message}"
        super().__init__(status_code=400, detail=detail)


class UnauthorizedError(HTTPException):
    """Unauthorized access (401)."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(status_code=401, detail=message)


class ForbiddenError(HTTPException):
    """Forbidden access (403)."""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(status_code=403, detail=message)


class ConflictError(HTTPException):
    """Resource conflict (409)."""

    def __init__(self, message: str):
        super().__init__(status_code=409, detail=message)


class ServiceUnavailableError(HTTPException):
    """Service unavailable (503)."""

    def __init__(self, service: str, reason: str | None = None):
        detail = f"Service '{service}' is unavailable"
        if reason:
            detail += f": {reason}"
        super().__init__(status_code=503, detail=detail)


# ===== Helper Functions (for backwards compatibility) =====


def raise_not_found(resource: str, identifier: str | None = None) -> None:
    """Raise a 404 Not Found error."""
    raise NotFoundError(resource, identifier)


def raise_validation_error(message: str, field: str | None = None) -> None:
    """Raise a 400 Validation error."""
    raise ValidationError(message, field)


def raise_unauthorized(message: str = "Unauthorized") -> None:
    """Raise a 401 Unauthorized error."""
    raise UnauthorizedError(message)


def raise_forbidden(message: str = "Forbidden") -> None:
    """Raise a 403 Forbidden error."""
    raise ForbiddenError(message)


def raise_conflict(message: str) -> None:
    """Raise a 409 Conflict error."""
    raise ConflictError(message)


def raise_service_unavailable(service: str, reason: str | None = None) -> None:
    """Raise a 503 Service Unavailable error."""
    raise ServiceUnavailableError(service, reason)


# ===== Error Response Builders =====


def build_error_response(
    status_code: int, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build standardized error response."""
    response = {"error": True, "status_code": status_code, "message": message}
    if details:
        response["details"] = details
    return response


def build_validation_error_response(errors: dict[str, str]) -> dict[str, Any]:
    """Build validation error response with field-specific errors."""
    return {"error": True, "status_code": 400, "message": "Validation failed", "errors": errors}
