"""Backward Compatibility Shim - use api.errors instead."""

from api.errors.types import (
    ErrorType,
    MedStationError,
    OllamaError,
    ValidationError,
    AuthError,
    DataEngineError,
    MeshError,
)

__all__ = [
    "ErrorType",
    "MedStationError",
    "OllamaError",
    "ValidationError",
    "AuthError",
    "DataEngineError",
    "MeshError",
]
