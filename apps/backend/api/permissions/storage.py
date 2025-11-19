"""
Permission Storage

Low-level database connection and query primitives for the permission system.
"""

import sqlite3
from pathlib import Path
from typing import Optional


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Get connection to auth database with row factory and optimized settings.

    Args:
        db_path: Optional explicit path. If None, loads from auth_service.

    Returns:
        SQLite connection with row factory
    """
    if db_path is None:
        # Load from auth_service (default behavior)
        try:
            from auth_middleware import auth_service
        except ImportError:
            from ..auth_middleware import auth_service
        db_path = auth_service.db_path

    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row

    # Enable WAL mode for better concurrent access
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")

    return conn
