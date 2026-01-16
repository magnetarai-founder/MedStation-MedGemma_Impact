"""
Compatibility Shim for Undo Service

The implementation now lives in the `api.undo` package:
- api.undo.service: UndoService class

This shim maintains backward compatibility.
"""

from api.undo.service import UndoService

# Re-export types for convenience
from api.undo.types import (
    ActionType,
    UndoAction,
    UndoResult,
)

__all__ = [
    "UndoService",
    "ActionType",
    "UndoAction",
    "UndoResult",
]
