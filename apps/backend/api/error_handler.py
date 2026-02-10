"""Backward Compatibility Shim - use api.errors instead."""

from api.errors.handler import ErrorHandler, logger
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
    "ErrorHandler",
    "logger",
    "ErrorType",
    "MedStationError",
    "OllamaError",
    "ValidationError",
    "AuthError",
    "DataEngineError",
    "MeshError",
]
