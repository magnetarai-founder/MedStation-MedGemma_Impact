"""
Compatibility Shim for Undo Types

The implementation now lives in the `api.undo` package:
- api.undo.types: ActionType enum and Pydantic models

This shim maintains backward compatibility.
"""

from api.undo.types import (
    ActionType,
    UndoAction,
    UndoResult,
)

__all__ = [
    "ActionType",
    "UndoAction",
    "UndoResult",
]
