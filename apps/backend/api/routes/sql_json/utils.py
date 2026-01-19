"""
Shared utilities for SQL/JSON processing.

Provides getter functions, rate limiting, logging, sanitization, and caching utilities.
"""

from typing import Any


# ============================================================================
# Getter Functions - Access shared state and utilities from main.py
# ============================================================================

def get_sessions() -> Any:
    """Get sessions dictionary from main module."""
    from api import main
    return main.sessions


def get_config() -> Any:
    """Get application configuration."""
    from neutron_utils.config import config
    return config


def get_save_upload() -> Any:
    """Get file upload save function."""
    from api.services.files import save_upload
    return save_upload


def get_column_info() -> Any:
    """Get column info helper function."""
    from api.services.sql_helpers import get_column_info as _get_column_info
    return _get_column_info


def get_df_to_jsonsafe_records() -> Any:
    """Get DataFrame to JSON-safe records converter."""
    from api.services.sql_helpers import df_to_jsonsafe_records
    return df_to_jsonsafe_records


def get_rate_limiter() -> Any:
    """Get rate limiter instance."""
    from api import main
    return main.rate_limiter


def get_client_ip() -> Any:
    """Get client IP extraction function."""
    from api import main
    return main.get_client_ip


def get_is_duplicate_request() -> Any:
    """Get duplicate request checker."""
    from api import main
    return main._is_duplicate_request


def get_sanitize_for_log() -> Any:
    """Get log sanitization function."""
    from api import main
    return main.sanitize_for_log


def get_store_query_result() -> Any:
    """Get query result storage function."""
    from api import main
    return main._store_query_result


def get_logger() -> Any:
    """Get logger instance."""
    from api import main
    return main.logger


def get_SQLProcessor() -> Any:
    """Get SQLProcessor class."""
    from neutron_utils.sql_utils import SQLProcessor
    return SQLProcessor


def get_query_results() -> Any:
    """Get query results cache."""
    from api import main
    return main.query_results


def get_current_user() -> Any:
    """Get current user dependency."""
    from api.main import get_current_user
    return get_current_user


def get_require_perm() -> Any:
    """Get permission requirement decorator."""
    from api.main import require_perm
    return require_perm


def get_query_result_sizes() -> Any:
    """Get query result sizes tracking."""
    from api import main
    return main._query_result_sizes


def get_total_cache_size_ref() -> Any:
    """Get reference to main module for cache size tracking."""
    from api import main
    return main


def get_sanitize_filename() -> Any:
    """Get filename sanitization function."""
    from api.main import sanitize_filename
    return sanitize_filename


# ============================================================================
# Session Validation
# ============================================================================

def validate_session_exists(session_id: str, sessions: dict) -> None:
    """
    Validate that a session exists.

    Args:
        session_id: Session ID to validate
        sessions: Sessions dictionary

    Raises:
        AppException: If session not found
    """
    from api.errors import http_404

    if session_id not in sessions:
        raise http_404(f"Session '{session_id}' not found", resource="session")
