"""
Database Query Profiler

Wraps SQLite connections to:
- Detect slow queries (> threshold)
- Log query execution time
- Track query patterns
- Identify missing indexes

Usage:
    from api.db_profiler import get_profiled_connection

    conn = get_profiled_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    # Automatically logs if query is slow
"""

import sqlite3
import time
import logging
from typing import Any, Optional
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Configuration
SLOW_QUERY_THRESHOLD_MS = 50  # Log queries taking > 50ms
VERY_SLOW_QUERY_THRESHOLD_MS = 200  # Warn on queries > 200ms


class ProfiledCursor:
    """Cursor wrapper that profiles query execution."""

    def __init__(self, cursor: sqlite3.Cursor, db_name: str):
        self._cursor = cursor
        self._db_name = db_name

    def execute(self, sql: str, parameters: Any = None) -> sqlite3.Cursor:
        """Execute query with timing."""
        start_time = time.time()

        try:
            if parameters:
                result = self._cursor.execute(sql, parameters)
            else:
                result = self._cursor.execute(sql)

            elapsed_ms = (time.time() - start_time) * 1000

            # Log slow queries
            if elapsed_ms > VERY_SLOW_QUERY_THRESHOLD_MS:
                logger.warning(
                    f"⚠️  VERY SLOW QUERY ({elapsed_ms:.1f}ms) [{self._db_name}]: {sql[:100]}..."
                )
            elif elapsed_ms > SLOW_QUERY_THRESHOLD_MS:
                logger.info(
                    f"🐌 Slow query ({elapsed_ms:.1f}ms) [{self._db_name}]: {sql[:100]}..."
                )

            return result

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(
                f"❌ Query failed ({elapsed_ms:.1f}ms) [{self._db_name}]: {sql[:100]}... - {e}"
            )
            raise

    def executemany(self, sql: str, parameters: Any) -> sqlite3.Cursor:
        """Execute many queries with timing."""
        start_time = time.time()

        try:
            result = self._cursor.executemany(sql, parameters)
            elapsed_ms = (time.time() - start_time) * 1000

            if elapsed_ms > SLOW_QUERY_THRESHOLD_MS:
                logger.info(
                    f"🐌 Slow batch query ({elapsed_ms:.1f}ms) [{self._db_name}]: {sql[:100]}..."
                )

            return result

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(
                f"❌ Batch query failed ({elapsed_ms:.1f}ms) [{self._db_name}]: {sql[:100]}... - {e}"
            )
            raise

    def __getattr__(self, name):
        """Delegate all other methods to underlying cursor."""
        return getattr(self._cursor, name)


class ProfiledConnection:
    """Connection wrapper that provides profiled cursors."""

    def __init__(self, connection: sqlite3.Connection, db_name: str):
        self._connection = connection
        self._db_name = db_name

    def cursor(self) -> ProfiledCursor:
        """Return a profiled cursor."""
        return ProfiledCursor(self._connection.cursor(), self._db_name)

    def execute(self, sql: str, parameters: Any = None) -> sqlite3.Cursor:
        """Execute query directly on connection (with profiling)."""
        cursor = self.cursor()
        return cursor.execute(sql, parameters)

    def __getattr__(self, name):
        """Delegate all other methods to underlying connection."""
        return getattr(self._connection, name)

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self._connection.close()


def get_profiled_connection(
    db_path: str | Path,
    timeout: float = 30.0,
    check_same_thread: bool = True
) -> ProfiledConnection:
    """
    Get a database connection with query profiling enabled.

    Args:
        db_path: Path to SQLite database
        timeout: Connection timeout in seconds
        check_same_thread: SQLite thread safety check

    Returns:
        ProfiledConnection with automatic slow query detection

    Example:
        conn = get_profiled_connection('.neutron_data/teams.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM teams WHERE team_id = ?", (team_id,))
        # Automatically logs if query > 50ms
    """
    db_path = Path(db_path)
    db_name = db_path.name

    # Create standard connection
    conn = sqlite3.connect(
        str(db_path),
        timeout=timeout,
        check_same_thread=check_same_thread
    )

    # Enable row factory for dict-like access
    conn.row_factory = sqlite3.Row

    # Enable WAL mode for performance
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    # Wrap in profiled connection
    return ProfiledConnection(conn, db_name)


@contextmanager
def profiled_connection(
    db_path: str | Path,
    timeout: float = 30.0
):
    """
    Context manager for profiled database connections.
    Ensures connection is properly closed.

    Usage:
        with profiled_connection('.neutron_data/teams.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM teams")
            results = cursor.fetchall()
        # Connection automatically closed
    """
    conn = get_profiled_connection(db_path, timeout=timeout)
    try:
        yield conn
    finally:
        conn.close()


def analyze_query_plan(conn: sqlite3.Connection, query: str, params: tuple = ()) -> None:
    """
    Analyze and log query execution plan.
    Helps identify missing indexes.

    Args:
        conn: Database connection
        query: SQL query to analyze
        params: Query parameters

    Example:
        analyze_query_plan(conn, "SELECT * FROM users WHERE email = ?", ("test@example.com",))
        # Logs query plan, warns if full table scan detected
    """
    cursor = conn.cursor()

    # Get query plan
    explain_query = f"EXPLAIN QUERY PLAN {query}"
    cursor.execute(explain_query, params)
    plan = cursor.fetchall()

    logger.info(f"\n📊 Query Plan Analysis:")
    logger.info(f"Query: {query[:100]}...")

    has_full_scan = False
    for row in plan:
        plan_detail = str(row)
        logger.info(f"  {plan_detail}")

        # Check for full table scans (bad performance)
        if "SCAN TABLE" in plan_detail.upper():
            has_full_scan = True

    if has_full_scan:
        logger.warning(
            f"⚠️  Full table scan detected! Consider adding an index."
        )
    else:
        logger.info("✓ Query uses indexes efficiently")


# Query statistics tracking
class QueryStats:
    """Track query statistics for monitoring."""

    def __init__(self):
        self.total_queries = 0
        self.slow_queries = 0
        self.very_slow_queries = 0
        self.failed_queries = 0
        self.total_time_ms = 0.0

    def record_query(self, elapsed_ms: float, failed: bool = False):
        """Record a query execution."""
        self.total_queries += 1
        self.total_time_ms += elapsed_ms

        if failed:
            self.failed_queries += 1
        elif elapsed_ms > VERY_SLOW_QUERY_THRESHOLD_MS:
            self.very_slow_queries += 1
        elif elapsed_ms > SLOW_QUERY_THRESHOLD_MS:
            self.slow_queries += 1

    def get_stats(self) -> dict:
        """Get query statistics."""
        avg_time = self.total_time_ms / self.total_queries if self.total_queries > 0 else 0

        return {
            "total_queries": self.total_queries,
            "slow_queries": self.slow_queries,
            "very_slow_queries": self.very_slow_queries,
            "failed_queries": self.failed_queries,
            "average_time_ms": round(avg_time, 2),
            "total_time_ms": round(self.total_time_ms, 2)
        }

    def reset(self):
        """Reset statistics."""
        self.total_queries = 0
        self.slow_queries = 0
        self.very_slow_queries = 0
        self.failed_queries = 0
        self.total_time_ms = 0.0


# Global stats instance
_query_stats = QueryStats()


def get_query_stats() -> dict:
    """Get global query statistics."""
    return _query_stats.get_stats()


def reset_query_stats():
    """Reset global query statistics."""
    _query_stats.reset()
