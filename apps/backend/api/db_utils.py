"""Backward Compatibility Shim - use api.db instead."""

from api.db.utils import get_sqlite_connection, logger

__all__ = [
    "get_sqlite_connection",
    "logger",
]
