"""Backward Compatibility Shim - use api.db instead."""

from api.db.profiler import (
    ProfiledCursor,
    ProfiledConnection,
    get_profiled_connection,
    get_query_stats,
    reset_query_stats,
    SLOW_QUERY_THRESHOLD_MS,
    VERY_SLOW_QUERY_THRESHOLD_MS,
    logger,
)

__all__ = [
    "ProfiledCursor",
    "ProfiledConnection",
    "get_profiled_connection",
    "get_query_stats",
    "reset_query_stats",
    "SLOW_QUERY_THRESHOLD_MS",
    "VERY_SLOW_QUERY_THRESHOLD_MS",
    "logger",
]
