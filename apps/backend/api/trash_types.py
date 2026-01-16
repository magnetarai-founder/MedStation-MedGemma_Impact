"""
Compatibility Shim for Trash Types

The implementation now lives in the `api.trash` package:
- api.trash.types: TrashItem and TrashStats models

This shim maintains backward compatibility.
"""

from api.trash.types import (
    TrashItem,
    TrashStats,
)

__all__ = [
    "TrashItem",
    "TrashStats",
]
