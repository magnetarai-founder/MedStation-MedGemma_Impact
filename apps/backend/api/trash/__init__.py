"""
Trash Package

Soft-delete trash system for MedStation:
- 30-day retention period
- Restore deleted items
- Auto-cleanup of expired items
"""

from api.trash.types import (
    TrashItem,
    TrashStats,
)
from api.trash.service import TrashService

__all__ = [
    "TrashItem",
    "TrashStats",
    "TrashService",
]
