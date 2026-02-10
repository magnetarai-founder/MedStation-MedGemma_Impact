"""
Main application configuration modules.

This package contains focused configuration modules for the MedStation API:
- state: Global application state and caching
- logging_config: Logging configuration
- app_settings: Application settings models and management
"""

from .app_settings import AppSettings, load_app_settings, save_app_settings, set_medstationos_memory
from .logging_config import configure_logging
from .state import (
    DEDUP_WINDOW_SECONDS,
    MAX_CACHED_RESULTS,
    MAX_CACHE_SIZE_MB,
    MAX_RESULT_SIZE_MB,
    delete_progress_stream,
    get_progress_stream,
    is_duplicate_request,
    list_progress_streams,
    query_results,
    sessions,
    store_query_result,
    update_progress_stream,
)

__all__ = [
    # State
    "sessions",
    "query_results",
    "store_query_result",
    "is_duplicate_request",
    "DEDUP_WINDOW_SECONDS",
    "MAX_RESULT_SIZE_MB",
    "MAX_CACHE_SIZE_MB",
    "MAX_CACHED_RESULTS",
    "get_progress_stream",
    "update_progress_stream",
    "delete_progress_stream",
    "list_progress_streams",
    # Logging
    "configure_logging",
    # Settings
    "AppSettings",
    "load_app_settings",
    "save_app_settings",
    "set_medstationos_memory",
]
