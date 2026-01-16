"""
Error Handler Types - Enums and exception classes for error handling

Extracted from error_handler.py during P2 decomposition.
Contains:
- ErrorType enum (standardized error types)
- Exception classes (ElohimOSError and subclasses)
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorType(Enum):
    """Standard error types"""
    # Ollama errors
    OLLAMA_OFFLINE = "ollama_offline"
    OLLAMA_MODEL_NOT_FOUND = "ollama_model_not_found"
    OLLAMA_TIMEOUT = "ollama_timeout"

    # File/upload errors
    FILE_NOT_FOUND = "file_not_found"
    FILE_TOO_LARGE = "file_too_large"
    FILE_UPLOAD_FAILED = "file_upload_failed"
    INVALID_FILE_TYPE = "invalid_file_type"

    # Data/SQL errors
    INVALID_SQL = "invalid_sql"
    SQL_EXECUTION_FAILED = "sql_execution_failed"
    TABLE_NOT_FOUND = "table_not_found"
    UNAUTHORIZED_TABLE_ACCESS = "unauthorized_table_access"

    # Session/auth errors
    SESSION_NOT_FOUND = "session_not_found"
    SESSION_EXPIRED = "session_expired"
    UNAUTHORIZED = "unauthorized"
    AUTH_TOKEN_INVALID = "auth_token_invalid"

    # P2P/mesh errors
    PEER_NOT_FOUND = "peer_not_found"
    PEER_UNREACHABLE = "peer_unreachable"
    SYNC_FAILED = "sync_failed"
    DISCOVERY_FAILED = "discovery_failed"

    # Validation errors
    INVALID_INPUT = "invalid_input"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    VALIDATION_FAILED = "validation_failed"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # Generic
    INTERNAL_ERROR = "internal_error"
    SERVICE_UNAVAILABLE = "service_unavailable"


class ElohimOSError(Exception):
    """Base exception for ElohimOS"""

    def __init__(
        self,
        message: str,
        error_type: ErrorType,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class OllamaError(ElohimOSError):
    """Ollama-specific errors"""

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.OLLAMA_OFFLINE,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_type=error_type,
            status_code=503,  # Service Unavailable
            details=details
        )


class ValidationError(ElohimOSError):
    """Validation errors"""

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.INVALID_INPUT,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_type=error_type,
            status_code=400,  # Bad Request
            details=details
        )


class AuthError(ElohimOSError):
    """Authentication/authorization errors"""

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.UNAUTHORIZED,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_type=error_type,
            status_code=401,  # Unauthorized
            details=details
        )


class DataEngineError(ElohimOSError):
    """Data engine/SQL errors"""

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.SQL_EXECUTION_FAILED,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_type=error_type,
            status_code=400,  # Bad Request
            details=details
        )


class MeshError(ElohimOSError):
    """P2P mesh networking errors"""

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.PEER_NOT_FOUND,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_type=error_type,
            status_code=503,  # Service Unavailable
            details=details
        )


__all__ = [
    # Enum
    "ErrorType",
    # Exception classes
    "ElohimOSError",
    "OllamaError",
    "ValidationError",
    "AuthError",
    "DataEngineError",
    "MeshError",
]
