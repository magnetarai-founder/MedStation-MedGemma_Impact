"""
Errors Package

Provides standardized error handling for MedStation:
- ErrorCode enum with standardized error codes (ERR-XXXX)
- ErrorType enum for error categories
- Exception classes (MedStationError and subclasses)
- ErrorHandler for converting errors to standardized format
- AppException and helper functions for HTTP error responses
"""

# Error codes and messages
from api.errors.codes_data import ErrorCode, ERROR_MESSAGES
from api.errors.codes import get_error_message

# Error types and exception classes
from api.errors.types import (
    ErrorType,
    MedStationError,
    OllamaError,
    ValidationError,
    AuthError,
    DataEngineError,
    MeshError,
)

# Error handler
from api.errors.handler import ErrorHandler

# HTTP error responses
from api.errors.responses import (
    AppException,
    app_exception_handler,
    generic_exception_handler,
    # Typed helpers (use with specific ErrorCode for best client handling)
    bad_request,
    unauthorized,
    forbidden,
    not_found,
    conflict,
    unprocessable_entity,
    too_many_requests,
    internal_error,
    service_unavailable,
    gateway_timeout,
    # Quick helpers (drop-in replacements for raw HTTPException)
    http_400,
    http_401,
    http_403,
    http_404,
    http_409,
    http_429,
    http_500,
    http_503,
    # Validation utilities
    validate_model_name,
    validate_file_size,
    validate_file_format,
    check_resource_exists,
    check_permission,
    handle_rate_limit,
)

__all__ = [
    # Error codes
    "ErrorCode",
    "ERROR_MESSAGES",
    "get_error_message",
    # Error types
    "ErrorType",
    "MedStationError",
    "OllamaError",
    "ValidationError",
    "AuthError",
    "DataEngineError",
    "MeshError",
    # Handler
    "ErrorHandler",
    # HTTP responses
    "AppException",
    "app_exception_handler",
    "generic_exception_handler",
    # Typed helpers
    "bad_request",
    "unauthorized",
    "forbidden",
    "not_found",
    "conflict",
    "unprocessable_entity",
    "too_many_requests",
    "internal_error",
    "service_unavailable",
    "gateway_timeout",
    # Quick helpers (drop-in for HTTPException)
    "http_400",
    "http_401",
    "http_403",
    "http_404",
    "http_409",
    "http_429",
    "http_500",
    "http_503",
    # Validation utilities
    "validate_model_name",
    "validate_file_size",
    "validate_file_format",
    "check_resource_exists",
    "check_permission",
    "handle_rate_limit",
]
