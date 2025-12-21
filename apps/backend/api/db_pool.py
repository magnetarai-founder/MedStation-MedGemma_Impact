"""
SQLite Connection Pool

Implements a thread-safe connection pool for SQLite databases to improve
performance and resource management.

Features:
- Configurable pool size (min/max connections)
- Automatic connection recycling after max_lifetime
- Thread-safe connection checkout/checkin
- WAL mode enabled on all connections
- Connection health checks
- Graceful shutdown with connection cleanup

Based on Sprint 1 (RACE-04) requirements for proper connection pooling.
"""

import sqlite3
import threading
import time
import logging
from pathlib import Path
from typing import Union, Optional, Any
from contextlib import contextmanager
from queue import Queue, Empty
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PooledConnection:
    """Wrapper for a connection in the pool"""
    connection: sqlite3.Connection
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    checkout_count: int = 0

    def is_expired(self, max_lifetime: float) -> bool:
        """Check if connection has exceeded max lifetime"""
        age = time.time() - self.created_at
        return age > max_lifetime

    def is_healthy(self) -> bool:
        """Check if connection is still healthy"""
        try:
            # Execute a simple query to verify connection
            self.connection.execute("SELECT 1").fetchone()
            return True
        except Exception as e:
            logger.warning(f"Connection health check failed: {e}")
            return False


class SQLiteConnectionPool:
    """
    Thread-safe connection pool for SQLite databases

    Usage:
        pool = SQLiteConnectionPool("app.db", min_size=2, max_size=10)

        # Context manager (recommended)
        with pool.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM users")

        # Or manual checkout/checkin
        conn = pool.checkout()
        try:
            cursor = conn.execute("SELECT * FROM users")
        finally:
            pool.checkin(conn)

        # Shutdown
        pool.close()
    """

    def __init__(
        self,
        database: Union[str, Path],
        min_size: int = 2,
        max_size: int = 10,
        max_lifetime: float = 3600.0,  # 1 hour
        timeout: float = 30.0,
        check_same_thread: bool = False  # Pool manages thread safety
    ):
        """
        Initialize connection pool

        Args:
            database: Path to SQLite database
            min_size: Minimum number of connections to maintain
            max_size: Maximum number of connections allowed
            max_lifetime: Max lifetime of a connection in seconds
            timeout: Timeout for acquiring a connection
            check_same_thread: SQLite same-thread check (should be False for pooling)
        """
        self.database = str(database)
        self.min_size = min_size
        self.max_size = max_size
        self.max_lifetime = max_lifetime
        self.timeout = timeout
        self.check_same_thread = check_same_thread

        # Connection pool (queue of available connections)
        self._pool: Queue[PooledConnection] = Queue(maxsize=max_size)

        # Track all connections (available + checked out)
        self._all_connections: list[PooledConnection] = []
        self._lock = threading.Lock()
        self._active_count = 0
        self._closed = False

        # Pre-create minimum connections
        self._initialize_pool()

        logger.info(
            f"SQLite connection pool initialized for {database}: "
            f"min={min_size}, max={max_size}, lifetime={max_lifetime}s"
        )

    def _initialize_pool(self) -> None:
        """Create minimum number of connections on startup"""
        for _ in range(self.min_size):
            pooled_conn = self._create_connection()
            self._all_connections.append(pooled_conn)
            self._pool.put(pooled_conn)

    def _create_connection(self) -> PooledConnection:
        """
        Create a new pooled connection with optimizations

        Returns:
            PooledConnection instance
        """
        conn = sqlite3.connect(
            self.database,
            check_same_thread=self.check_same_thread,
            timeout=self.timeout
        )

        # Enable WAL mode (Write-Ahead Logging)
        conn.execute("PRAGMA journal_mode=WAL")

        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys=ON")

        # Performance optimizations
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        conn.execute("PRAGMA temp_store=MEMORY")

        # Row factory for dict-like access
        conn.row_factory = sqlite3.Row

        logger.debug(f"Created new pooled connection to {self.database}")

        return PooledConnection(connection=conn)

    def checkout(self) -> sqlite3.Connection:
        """
        Checkout a connection from the pool

        Returns:
            SQLite connection

        Raises:
            RuntimeError: If pool is closed or timeout reached
        """
        if self._closed:
            raise RuntimeError("Connection pool is closed")

        start_time = time.time()

        while True:
            # Try to get an available connection from pool
            try:
                pooled_conn = self._pool.get(timeout=1.0)

                # Check if connection is healthy and not expired
                if pooled_conn.is_expired(self.max_lifetime):
                    logger.debug("Connection expired, creating new one")
                    self._close_connection(pooled_conn)
                    pooled_conn = self._create_connection()
                    with self._lock:
                        self._all_connections.append(pooled_conn)
                elif not pooled_conn.is_healthy():
                    logger.warning("Unhealthy connection detected, creating new one")
                    self._close_connection(pooled_conn)
                    pooled_conn = self._create_connection()
                    with self._lock:
                        self._all_connections.append(pooled_conn)

                # Update usage stats
                pooled_conn.last_used = time.time()
                pooled_conn.checkout_count += 1

                with self._lock:
                    self._active_count += 1

                return pooled_conn.connection

            except Empty:
                # No available connections, try to create one if under max_size
                with self._lock:
                    total_connections = len(self._all_connections)

                    if total_connections < self.max_size:
                        # Create new connection
                        pooled_conn = self._create_connection()
                        self._all_connections.append(pooled_conn)
                        pooled_conn.last_used = time.time()
                        pooled_conn.checkout_count += 1
                        self._active_count += 1
                        return pooled_conn.connection

            # Check timeout
            if time.time() - start_time > self.timeout:
                raise RuntimeError(
                    f"Timeout acquiring connection from pool after {self.timeout}s"
                )

    def checkin(self, conn: sqlite3.Connection) -> None:
        """
        Return a connection to the pool

        Args:
            conn: SQLite connection to return
        """
        if self._closed:
            logger.warning("Attempted to checkin connection to closed pool")
            try:
                conn.close()
            except (sqlite3.Error, OSError):
                pass  # Connection may already be closed
            return

        # Find the pooled connection wrapper
        with self._lock:
            for pooled_conn in self._all_connections:
                if pooled_conn.connection is conn:
                    # Rollback any uncommitted transaction
                    try:
                        conn.rollback()
                    except sqlite3.Error:
                        pass  # Connection may be in bad state

                    # Return to pool
                    self._pool.put(pooled_conn)
                    self._active_count -= 1
                    logger.debug(f"Connection returned to pool (active: {self._active_count})")
                    return

            # Connection not found in pool (unexpected)
            logger.error("Attempted to checkin unknown connection")
            try:
                conn.close()
            except (sqlite3.Error, OSError):
                pass  # Connection may already be closed

    @contextmanager
    def get_connection(self):
        """
        Context manager for getting a connection

        Usage:
            with pool.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM users")

        Yields:
            SQLite connection
        """
        conn = self.checkout()
        try:
            yield conn
        finally:
            self.checkin(conn)

    def _close_connection(self, pooled_conn: PooledConnection) -> None:
        """
        Close a pooled connection and remove from tracking

        Args:
            pooled_conn: PooledConnection to close
        """
        try:
            pooled_conn.connection.close()
        except Exception as e:
            logger.error(f"Error closing connection: {e}")

        with self._lock:
            if pooled_conn in self._all_connections:
                self._all_connections.remove(pooled_conn)

    def close(self) -> None:
        """
        Close all connections in the pool

        Should be called on application shutdown.
        """
        if self._closed:
            return

        logger.info(f"Closing connection pool for {self.database}")

        self._closed = True

        # Close all connections
        with self._lock:
            for pooled_conn in self._all_connections:
                try:
                    pooled_conn.connection.close()
                except Exception as e:
                    logger.error(f"Error closing pooled connection: {e}")

            self._all_connections.clear()

        # Clear the queue
        while not self._pool.empty():
            try:
                self._pool.get_nowait()
            except Empty:
                break

        logger.info("Connection pool closed")

    def stats(self) -> dict[str, Any]:
        """
        Get pool statistics

        Returns:
            Dictionary with pool stats
        """
        with self._lock:
            return {
                "database": self.database,
                "total_connections": len(self._all_connections),
                "available_connections": self._pool.qsize(),
                "active_connections": self._active_count,
                "min_size": self.min_size,
                "max_size": self.max_size,
                "closed": self._closed
            }


# Global pool registry
_connection_pools: dict[str, SQLiteConnectionPool] = {}
_pool_lock = threading.Lock()


def get_connection_pool(
    database: Union[str, Path],
    min_size: int = 2,
    max_size: int = 10,
    **kwargs
) -> SQLiteConnectionPool:
    """
    Get or create a connection pool for a database

    Singleton pattern - returns the same pool for the same database path.

    Args:
        database: Path to SQLite database
        min_size: Minimum pool size
        max_size: Maximum pool size
        **kwargs: Additional args for SQLiteConnectionPool

    Returns:
        SQLiteConnectionPool instance

    Example:
        >>> pool = get_connection_pool("app.db")
        >>> with pool.get_connection() as conn:
        ...     cursor = conn.execute("SELECT * FROM users")
    """
    db_path = str(Path(database).resolve())

    with _pool_lock:
        if db_path not in _connection_pools:
            pool = SQLiteConnectionPool(
                db_path,
                min_size=min_size,
                max_size=max_size,
                **kwargs
            )
            _connection_pools[db_path] = pool

        return _connection_pools[db_path]


def close_all_pools() -> None:
    """
    Close all connection pools

    Should be called on application shutdown.
    """
    with _pool_lock:
        for db_path, pool in _connection_pools.items():
            logger.info(f"Closing pool for {db_path}")
            pool.close()

        _connection_pools.clear()

    logger.info("All connection pools closed")
