"""
Compatibility Shim for Trash Service

The implementation now lives in the `api.trash` package:
- api.trash.service: TrashService class

This shim maintains backward compatibility.
"""

from api.trash.service import TrashService
from api.trash.types import (
    TrashItem,
    TrashStats,
)

__all__ = [
    "TrashService",
    "TrashItem",
    "TrashStats",
]
