#!/usr/bin/env python3
"""
Enhanced Error Response System for ElohimOS
Provides user-friendly error messages with actionable suggestions
"""

import logging
import uuid
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

# Import from sibling module and config (P3 decomposition)
from api.errors.codes import ErrorCode, get_error_message
from api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AppException(HTTPException):
    """
    Enhanced HTTPException with error codes and user-friendly messages

    This exception automatically formats error responses with:
    - Standardized error codes (ERR-XXXX)
    - User-friendly messages
    - Actionable suggestions
    - Technical details (in dev mode only)
    - Unique error IDs for debugging
    """

    def __init__(
        self,
        status_code: int,
        error_code: ErrorCode,
        context: Optional[Dict[str, Any]] = None,
        technical_detail: Optional[str] = None,
        log_error: bool = True
    ):
        """
        Create an application exception

        Args:
            status_code: HTTP status code (400, 401, 404, 500, etc.)
            error_code: Standardized error code from ErrorCode enum
            context: Context variables for message formatting (e.g., max_size=10, model="llama2")
            technical_detail: Additional technical details (shown only in dev mode)
            log_error: Whether to log this error (default: True)
        """
        self.error_code = error_code
        self.error_id = str(uuid.uuid4())[:8]  # Short error ID for debugging
        self.context = context or {}

        # Get formatted error messages
        error_info = get_error_message(error_code, **self.context)

        # Build response detail
        detail = {
            "error_code": error_code.value,
            "error_id": self.error_id,
            "message": error_info["user_message"],
            "suggestion": error_info["suggestion"],
        }

        # Add technical details only in development
        if settings.debug:
            detail["technical"] = technical_detail or error_info["technical"]
            if context:
                detail["context"] = context

        # Log the error
        if log_error:
            log_level = logging.ERROR if status_code >= 500 else logging.WARNING
            logger.log(
                log_level,
                f"[{self.error_id}] {error_code.value}: {error_info['user_message']} "
                f"| Technical: {technical_detail or error_info['technical']}"
            )

        super().__init__(status_code=status_code, detail=detail)


# Convenience functions for common HTTP status codes

def bad_request(error_code: ErrorCode, **context) -> AppException:
    """400 Bad Request - Client sent invalid data"""
    return AppException(400, error_code, context)


def unauthorized(error_code: ErrorCode, **context) -> AppException:
    """401 Unauthorized - Authentication required or failed"""
    return AppException(401, error_code, context)


def forbidden(error_code: ErrorCode, **context) -> AppException:
    """403 Forbidden - User lacks permissions"""
    return AppException(403, error_code, context)


def not_found(error_code: ErrorCode, **context) -> AppException:
    """404 Not Found - Resource doesn't exist"""
    return AppException(404, error_code, context)


def conflict(error_code: ErrorCode, **context) -> AppException:
    """409 Conflict - Resource already exists or state conflict"""
    return AppException(409, error_code, context)


def unprocessable_entity(error_code: ErrorCode, **context) -> AppException:
    """422 Unprocessable Entity - Validation failed"""
    return AppException(422, error_code, context)


def too_many_requests(error_code: ErrorCode, **context) -> AppException:
    """429 Too Many Requests - Rate limit exceeded"""
    return AppException(429, error_code, context)


def internal_error(error_code: ErrorCode, technical_detail: Optional[str] = None, **context) -> AppException:
    """500 Internal Server Error - Unexpected server error"""
    return AppException(500, error_code, context, technical_detail=technical_detail)


def service_unavailable(error_code: ErrorCode, **context) -> AppException:
    """503 Service Unavailable - Temporary unavailability"""
    return AppException(503, error_code, context)


def gateway_timeout(error_code: ErrorCode, **context) -> AppException:
    """504 Gateway Timeout - Upstream service timeout"""
    return AppException(504, error_code, context)


# Global exception handler for FastAPI
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Global exception handler for AppException

    This ensures consistent error response format across all endpoints
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
        headers=getattr(exc, 'headers', None)
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all exception handler for unexpected errors

    Converts unhandled exceptions to standardized error responses
    """
    error_id = str(uuid.uuid4())[:8]

    # Log the unexpected error
    logger.exception(f"[{error_id}] Unhandled exception: {str(exc)}")

    # Create a generic internal error response
    error_code = ErrorCode.SYSTEM_INTERNAL_ERROR
    error_info = get_error_message(error_code, error_id=error_id)

    detail = {
        "error_code": error_code.value,
        "error_id": error_id,
        "message": error_info["user_message"],
        "suggestion": error_info["suggestion"],
    }

    # Include technical details in dev mode
    if settings.debug:
        detail["technical"] = str(exc)
        detail["type"] = type(exc).__name__

    return JSONResponse(
        status_code=500,
        content=detail
    )


# Utility functions for validating requests

def validate_model_name(model: str) -> None:
    """
    Validate that a model name is well-formed

    Raises:
        AppException: If model name is invalid
    """
    if not model or not isinstance(model, str):
        raise bad_request(ErrorCode.MODEL_INVALID_NAME, model=model)

    # Basic validation - alphanumeric, hyphens, colons, underscores
    import re
    if not re.match(r'^[a-zA-Z0-9_:-]+$', model):
        raise bad_request(ErrorCode.MODEL_INVALID_NAME, model=model)


def validate_file_size(file_size: int, max_size_mb: int = 100) -> None:
    """
    Validate file size doesn't exceed limit

    Args:
        file_size: File size in bytes
        max_size_mb: Maximum allowed size in MB

    Raises:
        AppException: If file is too large
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        raise bad_request(
            ErrorCode.FILE_TOO_LARGE,
            max_size=max_size_mb,
            actual_size=round(file_size / (1024 * 1024), 2)
        )


def validate_file_format(filename: str, allowed_formats: list) -> None:
    """
    Validate file format is in allowed list

    Args:
        filename: Name of the file
        allowed_formats: List of allowed extensions (e.g., ['.pdf', '.txt'])

    Raises:
        AppException: If file format is not allowed
    """
    import os
    ext = os.path.splitext(filename)[1].lower()

    if ext not in allowed_formats:
        raise bad_request(
            ErrorCode.FILE_INVALID_FORMAT,
            filename=filename,
            supported_formats=", ".join(allowed_formats)
        )


def check_resource_exists(resource: Any, error_code: ErrorCode, **context) -> None:
    """
    Check if a resource exists, raise not_found if it doesn't

    Args:
        resource: The resource to check (None/empty means not found)
        error_code: Error code to raise if not found
        **context: Context for error message

    Raises:
        AppException: If resource is None or empty
    """
    if resource is None or (hasattr(resource, '__len__') and len(resource) == 0):
        raise not_found(error_code, **context)


def check_permission(has_permission: bool, action: str = "perform this action") -> None:
    """
    Check if user has permission for an action

    Args:
        has_permission: Whether user has the required permission
        action: Description of the action (for error message)

    Raises:
        AppException: If user lacks permission
    """
    if not has_permission:
        raise forbidden(ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS, action=action)


def handle_rate_limit(exceeded: bool, retry_after: int = 60) -> None:
    """
    Handle rate limit check

    Args:
        exceeded: Whether rate limit is exceeded
        retry_after: Seconds until next allowed request

    Raises:
        AppException: If rate limit is exceeded
    """
    if exceeded:
        raise too_many_requests(ErrorCode.AUTH_RATE_LIMIT_EXCEEDED, retry_after=retry_after)
