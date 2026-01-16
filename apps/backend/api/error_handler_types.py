"""Backward Compatibility Shim - use api.errors instead."""

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
    "ErrorType",
    "ElohimOSError",
    "OllamaError",
    "ValidationError",
    "AuthError",
    "DataEngineError",
    "MeshError",
]
