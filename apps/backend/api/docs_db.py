"""
Docs Database - Database utilities for Documents service

Provides connection pool management, schema initialization, and safe SQL utilities
for the Documents database.

Extracted from docs_service.py during P2 decomposition.
"""

from __future__ import annotations

import sqlite3
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from config_paths import get_config_paths
except ImportError:
    from api.config_paths import get_config_paths

try:
    from db_pool import SQLiteConnectionPool
except ImportError:
    from api.db_pool import SQLiteConnectionPool

try:
    from api.security.sql_safety import quote_identifier
except ImportError:
    from security.sql_safety import quote_identifier

logger = logging.getLogger(__name__)

# Storage paths - use centralized config_paths
PATHS = get_config_paths()
DOCS_DB_PATH = PATHS.data_dir / "docs.db"
DOCS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Connection pool for docs database (replaces per-request connections)
_docs_pool: Optional[SQLiteConnectionPool] = None

# Whitelisted columns for SQL UPDATE to prevent injection
DOCUMENT_UPDATE_COLUMNS = frozenset({
    "title", "content", "is_private", "security_level", "shared_with", "updated_at"
})


def build_safe_update(updates_dict: Dict[str, Any], allowed_columns: frozenset) -> Tuple[List[str], List[Any]]:
    """
    Build safe SQL UPDATE clause with whitelist validation and identifier quoting.

    Args:
        updates_dict: Dict of column_name -> value pairs
        allowed_columns: Frozenset of allowed column names

    Returns:
        Tuple of (update_clauses, params) for use in SQL query

    Raises:
        ValueError: If any column is not in the whitelist
    """
    clauses = []
    params = []

    for column, value in updates_dict.items():
        if column not in allowed_columns:
            raise ValueError(f"Invalid column for update: {column}")
        # quote_identifier adds defense-in-depth even with whitelist
        clauses.append(f"{quote_identifier(column)} = ?")
        params.append(value)

    return clauses, params


def init_db() -> None:
    """Initialize the documents database"""
    conn = sqlite3.connect(DOCS_DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            is_private INTEGER DEFAULT 0,
            security_level TEXT,
            shared_with TEXT DEFAULT '[]',
            team_id TEXT
        )
    """)

    # Indexes for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_updated_at ON documents(updated_at)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_created_by ON documents(created_by)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_created_by_updated ON documents(created_by, updated_at)
    """)

    # Index for team documents (Phase 3)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_team_id ON documents(team_id)
    """)

    conn.commit()
    conn.close()
    logger.info("Documents database initialized")


def _get_pool() -> SQLiteConnectionPool:
    """Get or create the connection pool"""
    global _docs_pool
    if _docs_pool is None:
        _docs_pool = SQLiteConnectionPool(
            database=DOCS_DB_PATH,
            min_size=2,
            max_size=10,
            max_lifetime=3600.0  # 1 hour
        )
        logger.info("Docs connection pool initialized (min=2, max=10)")
    return _docs_pool


def get_db() -> sqlite3.Connection:
    """Get database connection from pool"""
    pool = _get_pool()
    conn = pool.checkout()
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn


def release_db(conn: sqlite3.Connection) -> None:
    """Return connection to pool"""
    pool = _get_pool()
    pool.checkin(conn)


# Initialize on module load (safe, idempotent)
init_db()


__all__ = [
    "PATHS",
    "DOCS_DB_PATH",
    "DOCUMENT_UPDATE_COLUMNS",
    "build_safe_update",
    "init_db",
    "get_db",
    "release_db",
]
