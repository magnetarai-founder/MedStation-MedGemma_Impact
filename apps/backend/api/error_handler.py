"""Backward Compatibility Shim - use api.errors instead."""

from api.errors.handler import ErrorHandler, logger
from api.errors.types import (
    ErrorType,
    ElohimOSError,
    OllamaError,
    ValidationError,
    AuthError,
    DataEngineError,
    MeshError,
)

__all__ = [
    "ErrorHandler",
    "logger",
    "ErrorType",
    "ElohimOSError",
    "OllamaError",
    "ValidationError",
    "AuthError",
    "DataEngineError",
    "MeshError",
]
