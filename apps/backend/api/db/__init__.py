"""
Database Package

Provides database utilities and connection management:
- SQLiteConnectionPool for connection pooling
- Database profiler for slow query detection
- WAL mode utilities
- Database consolidation migration
"""

from api.db.pool import SQLiteConnectionPool, PooledConnection
from api.db.profiler import (
    ProfiledCursor,
    ProfiledConnection,
    get_profiled_connection,
    SLOW_QUERY_THRESHOLD_MS,
    VERY_SLOW_QUERY_THRESHOLD_MS,
)
from api.db.utils import get_sqlite_connection

__all__ = [
    # Pool
    "SQLiteConnectionPool",
    "PooledConnection",
    # Profiler
    "ProfiledCursor",
    "ProfiledConnection",
    "get_profiled_connection",
    "SLOW_QUERY_THRESHOLD_MS",
    "VERY_SLOW_QUERY_THRESHOLD_MS",
    # Utils
    "get_sqlite_connection",
]
