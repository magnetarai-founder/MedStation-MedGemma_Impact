"""Backward Compatibility Shim - use api.db instead."""

from api.db.pool import (
    SQLiteConnectionPool,
    PooledConnection,
    get_connection_pool,
    logger,
)

__all__ = [
    "SQLiteConnectionPool",
    "PooledConnection",
    "get_connection_pool",
    "logger",
]
