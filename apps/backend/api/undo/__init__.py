"""
Undo Package

Undo/redo action management for ElohimOS:
- Action history tracking with state snapshots
- Automatic timeout cleanup
- State preservation for rollback
"""

from api.undo.types import (
    ActionType,
    UndoAction,
    UndoResult,
)
from api.undo.service import UndoService

__all__ = [
    "ActionType",
    "UndoAction",
    "UndoResult",
    "UndoService",
]
