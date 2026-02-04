"""
Database Connection Manager

Provides thread-local SQLite connections with:
- Connection pooling per thread
- WAL mode auto-configuration
- Performance-optimized pragmas
- Thread-safe write operations

Note: S608 warnings are intentionally suppressed - table/column names come from
internal code (not user input) and all user values use parameterized queries.
"""
# ruff: noqa: S608
import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Manages SQLite database connections with thread-local pooling.

    Features:
    - Each thread gets its own connection (safe for asyncio.to_thread())
    - WAL mode for concurrent read/write
    - Optimized pragmas for performance
    - Context manager for transactions
    """

    def __init__(
        self,
        db_path: Path | str,
        timeout: float = 30.0,
        isolation_level: str | None = "DEFERRED",
    ):
        """
        Initialize database connection manager.

        Args:
            db_path: Path to SQLite database file
            timeout: Connection timeout in seconds
            isolation_level: SQLite isolation level (DEFERRED, IMMEDIATE, EXCLUSIVE)
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.timeout = timeout
        self.isolation_level = isolation_level

        # Thread-local storage for connections
        self._local = threading.local()

        # Thread lock for write operations
        self._write_lock = threading.Lock()

        # Ensure database is configured
        self._setup_connection(self.get())

    def get(self) -> sqlite3.Connection:
        """
        Get or create a thread-local database connection.

        Returns:
            Thread-local SQLite connection with row factory set
        """
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = self._create_connection()
            logger.debug(
                f"Created SQLite connection for thread {threading.current_thread().name}"
            )

        return self._local.conn

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection with optimal settings."""
        conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=True,
            timeout=self.timeout,
            isolation_level=self.isolation_level,
        )
        conn.row_factory = sqlite3.Row
        self._setup_connection(conn)
        return conn

    def _setup_connection(self, conn: sqlite3.Connection):
        """Configure connection with WAL mode and performance pragmas."""
        # WAL mode for concurrent reads during writes
        conn.execute("PRAGMA journal_mode=WAL")

        # Synchronous NORMAL for balance of safety and speed
        conn.execute("PRAGMA synchronous=NORMAL")

        # Store temp tables in memory
        conn.execute("PRAGMA temp_store=MEMORY")

        # Use memory-mapped I/O (1GB limit)
        conn.execute("PRAGMA mmap_size=1073741824")

    @property
    def write_lock(self) -> threading.Lock:
        """Get the write lock for thread-safe write operations."""
        return self._write_lock

    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.

        Automatically commits on success, rolls back on exception.

        Usage:
            with db.transaction():
                db.execute("INSERT INTO ...")
                db.execute("UPDATE ...")
        """
        conn = self.get()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    @contextmanager
    def write_transaction(self):
        """
        Context manager for write transactions with locking.

        Acquires write lock, commits on success, rolls back on exception.

        Usage:
            with db.write_transaction() as conn:
                conn.execute("INSERT INTO ...")
        """
        with self._write_lock:
            with self.transaction() as conn:
                yield conn

    def execute(
        self,
        sql: str,
        params: tuple | list | dict | None = None,
    ) -> sqlite3.Cursor:
        """
        Execute a SQL query and return cursor.

        Args:
            sql: SQL query string
            params: Query parameters

        Returns:
            Cursor with results
        """
        conn = self.get()
        if params:
            return conn.execute(sql, params)
        return conn.execute(sql)

    def execute_many(
        self,
        sql: str,
        params_list: list[tuple | list | dict],
    ) -> sqlite3.Cursor:
        """
        Execute a SQL query multiple times with different parameters.

        Args:
            sql: SQL query string
            params_list: List of parameter sets

        Returns:
            Cursor
        """
        conn = self.get()
        return conn.executemany(sql, params_list)

    def fetchone(
        self,
        sql: str,
        params: tuple | list | dict | None = None,
    ) -> sqlite3.Row | None:
        """
        Execute query and fetch one row.

        Args:
            sql: SQL query string
            params: Query parameters

        Returns:
            Row or None
        """
        cursor = self.execute(sql, params)
        return cursor.fetchone()

    def fetchall(
        self,
        sql: str,
        params: tuple | list | dict | None = None,
    ) -> list[sqlite3.Row]:
        """
        Execute query and fetch all rows.

        Args:
            sql: SQL query string
            params: Query parameters

        Returns:
            List of rows
        """
        cursor = self.execute(sql, params)
        return cursor.fetchall()

    def insert(
        self,
        table: str,
        data: dict[str, Any],
    ) -> int:
        """
        Insert a row and return the last row ID.

        Args:
            table: Table name
            data: Column-value dictionary

        Returns:
            Last inserted row ID
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        with self.write_transaction() as conn:
            cursor = conn.execute(sql, tuple(data.values()))
            return cursor.lastrowid

    def update(
        self,
        table: str,
        data: dict[str, Any],
        where: str,
        where_params: tuple | list | None = None,
    ) -> int:
        """
        Update rows and return count of affected rows.

        Args:
            table: Table name
            data: Column-value dictionary
            where: WHERE clause (e.g., "id = ?")
            where_params: Parameters for WHERE clause

        Returns:
            Number of affected rows
        """
        set_clause = ", ".join(f"{k} = ?" for k in data.keys())
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        params = list(data.values()) + list(where_params or [])

        with self.write_transaction() as conn:
            cursor = conn.execute(sql, params)
            return cursor.rowcount

    def delete(
        self,
        table: str,
        where: str,
        where_params: tuple | list | None = None,
    ) -> int:
        """
        Delete rows and return count of deleted rows.

        Args:
            table: Table name
            where: WHERE clause
            where_params: Parameters for WHERE clause

        Returns:
            Number of deleted rows
        """
        sql = f"DELETE FROM {table} WHERE {where}"

        with self.write_transaction() as conn:
            cursor = conn.execute(sql, where_params or ())
            return cursor.rowcount

    def table_exists(self, table: str) -> bool:
        """Check if a table exists."""
        row = self.fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        return row is not None

    def create_index(
        self,
        name: str,
        table: str,
        columns: list[str],
        unique: bool = False,
    ):
        """
        Create an index if it doesn't exist.

        Args:
            name: Index name
            table: Table name
            columns: List of column names
            unique: Whether index should be unique
        """
        unique_str = "UNIQUE " if unique else ""
        columns_str = ", ".join(columns)
        sql = f"CREATE {unique_str}INDEX IF NOT EXISTS {name} ON {table}({columns_str})"
        self.execute(sql)
        self.get().commit()
