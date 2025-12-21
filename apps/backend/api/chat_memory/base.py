"""
Chat Memory Base Class

Connection management and shared infrastructure.
"""

import sqlite3
import threading
import logging
from pathlib import Path

from .schema import setup_schema

logger = logging.getLogger(__name__)


class ChatMemoryBase:
    """
    Base class for chat memory with connection management.

    Provides thread-safe SQLite connections using the connection-per-thread pattern.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread-local storage for connections
        self._local = threading.local()

        # Thread lock for write operations
        self._write_lock = threading.Lock()

        # Initialize main connection for setup
        self._setup_database()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get or create a thread-local database connection.
        This ensures each thread gets its own connection, preventing
        SQLite threading errors when using asyncio.to_thread().
        """
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            # Create new connection for this thread
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=True,  # Enforce single-thread usage per connection
                timeout=30.0,
                isolation_level='DEFERRED'
            )
            self._local.conn.row_factory = sqlite3.Row

            # Enable WAL mode and performance optimizations
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA temp_store=MEMORY")
            self._local.conn.execute("PRAGMA mmap_size=30000000000")

            logger.debug(f"Created new SQLite connection for thread {threading.current_thread().name}")

        return self._local.conn

    def _setup_database(self) -> None:
        """Create memory tables"""
        conn = self._get_connection()
        setup_schema(conn)


__all__ = ["ChatMemoryBase"]
