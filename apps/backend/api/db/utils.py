"""
Database Utilities

Provides centralized database connection management with WAL mode enabled.

Features:
- Automatic WAL mode enablement for all SQLite connections
- Thread-safe connection handling
- Foreign key constraints enabled by default
- Performance optimizations (synchronous=NORMAL, cache_size)

Usage:
    from db_utils import get_sqlite_connection

    # Old way:
    # conn = sqlite3.connect("path/to/db.db")

    # New way (with WAL mode):
    conn = get_sqlite_connection("path/to/db.db")
"""

import sqlite3
from pathlib import Path
from typing import Union
import logging

logger = logging.getLogger(__name__)


def get_sqlite_connection(
    database: Union[str, Path],
    check_same_thread: bool = True,
    timeout: float = 30.0
) -> sqlite3.Connection:
    """
    Create a SQLite connection with performance optimizations.

    Automatically enables:
    - WAL mode (Write-Ahead Logging) for 5-10x faster concurrent reads
    - Foreign key constraints (data integrity)
    - Optimized cache size and synchronous mode

    Args:
        database: Path to SQLite database file
        check_same_thread: Whether to check same thread (default True for safety)
        timeout: Connection timeout in seconds (default 30)

    Returns:
        Configured SQLite connection

    Example:
        >>> conn = get_sqlite_connection(".neutron_data/vault.db")
        >>> # WAL mode is now enabled automatically
        >>> conn.execute("SELECT * FROM items")
    """
    conn = sqlite3.connect(
        str(database),
        check_same_thread=check_same_thread,
        timeout=timeout
    )

    # Enable WAL mode for concurrent read performance (5-10x faster!)
    # This allows reads to happen while writes are in progress
    conn.execute("PRAGMA journal_mode=WAL")

    # Enable foreign key constraints (data integrity)
    conn.execute("PRAGMA foreign_keys=ON")

    # Performance optimizations
    conn.execute("PRAGMA synchronous=NORMAL")  # Faster than FULL, still safe with WAL
    conn.execute("PRAGMA cache_size=-64000")   # 64MB cache (default is ~2MB)
    conn.execute("PRAGMA temp_store=MEMORY")   # Store temp tables in memory

    # Use Row factory for dict-like access
    conn.row_factory = sqlite3.Row

    logger.debug(f"SQLite connection created for {database} (WAL mode enabled)")

    return conn


def verify_wal_mode(database: Union[str, Path]) -> bool:
    """
    Verify that a database is using WAL mode.

    Args:
        database: Path to SQLite database file

    Returns:
        True if WAL mode is enabled, False otherwise
    """
    try:
        conn = sqlite3.connect(str(database))
        result = conn.execute("PRAGMA journal_mode").fetchone()
        conn.close()
        return result[0].upper() == "WAL"
    except Exception as e:
        logger.error(f"Error checking WAL mode for {database}: {e}")
        return False


def enable_wal_for_existing_db(database: Union[str, Path]) -> bool:
    """
    Enable WAL mode for an existing database.

    This is a one-time operation. Once enabled, the database will
    stay in WAL mode even after closing the connection.

    Args:
        database: Path to SQLite database file

    Returns:
        True if WAL mode was enabled successfully
    """
    try:
        conn = sqlite3.connect(str(database))
        result = conn.execute("PRAGMA journal_mode=WAL").fetchone()
        conn.close()

        success = result[0].upper() == "WAL"
        if success:
            logger.info(f"✅ WAL mode enabled for {database}")
        else:
            logger.warning(f"⚠️ Failed to enable WAL mode for {database}")

        return success
    except Exception as e:
        logger.error(f"❌ Error enabling WAL mode for {database}: {e}")
        return False
