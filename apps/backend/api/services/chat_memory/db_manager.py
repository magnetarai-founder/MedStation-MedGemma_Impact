"""
Database Manager for Chat Memory

Handles all database infrastructure:
- Thread-local connection management
- WAL mode and performance settings
- Schema creation and migrations
"""
import logging
import sqlite3
import threading
from pathlib import Path

from .config import MEMORY_DIR

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages SQLite database connections and schema for chat memory.

    Features:
    - Thread-local connections (safe for asyncio.to_thread())
    - WAL mode for concurrent read/write
    - Performance-optimized pragmas
    - Centralized schema management
    """

    def __init__(self, db_path: Path | None = None):
        """
        Initialize the database manager.

        Args:
            db_path: Path to SQLite database file. Defaults to MEMORY_DIR/chat_memory.db
        """
        if db_path is None:
            db_path = MEMORY_DIR / "chat_memory.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread-local storage for connections
        self._local = threading.local()

        # Thread lock for write operations
        self._write_lock = threading.Lock()

        # Initialize database schema
        self._setup_database()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get or create a thread-local database connection.

        This ensures each thread gets its own connection, preventing
        SQLite threading errors when using asyncio.to_thread().

        Returns:
            Thread-local SQLite connection
        """
        if not hasattr(self._local, "conn") or self._local.conn is None:
            # Create new connection for this thread
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=True,  # Enforce single-thread usage per connection
                timeout=30.0,
                isolation_level="DEFERRED",
            )
            self._local.conn.row_factory = sqlite3.Row

            # Enable WAL mode and performance optimizations
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA temp_store=MEMORY")
            self._local.conn.execute("PRAGMA mmap_size=1073741824")  # 1GB

            logger.debug(
                f"Created new SQLite connection for thread {threading.current_thread().name}"
            )

        return self._local.conn

    def _setup_database(self):
        """Create all memory tables and indexes."""
        conn = self._get_connection()

        # Session metadata
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT,
                updated_at TEXT,
                default_model TEXT,
                message_count INTEGER DEFAULT 0,
                models_used TEXT,
                summary TEXT,
                auto_titled INTEGER DEFAULT 0,
                user_id TEXT,
                team_id TEXT
            )
        """
        )

        # Schema migrations for existing databases
        self._run_migrations(conn)

        # Full message history
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TEXT,
                role TEXT,
                content TEXT,
                model TEXT,
                tokens INTEGER,
                files_json TEXT,
                user_id TEXT,
                team_id TEXT,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
            )
        """
        )

        # Conversation summaries (rolling window)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                created_at TEXT,
                updated_at TEXT,
                summary TEXT,
                events_json TEXT,
                models_used TEXT,
                user_id TEXT,
                team_id TEXT,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
            )
        """
        )

        # Document chunks for RAG
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS document_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                file_id TEXT,
                filename TEXT,
                chunk_index INTEGER,
                total_chunks INTEGER,
                content TEXT,
                embedding_json TEXT,
                created_at TEXT,
                user_id TEXT,
                team_id TEXT,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
            )
        """
        )

        # Embeddings for semantic search
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS message_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                session_id TEXT,
                embedding_json TEXT,
                created_at TEXT,
                team_id TEXT,
                FOREIGN KEY (message_id) REFERENCES chat_messages(id),
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
            )
        """
        )

        # Create all indexes
        self._create_indexes(conn)

        conn.commit()

    def _run_migrations(self, conn: sqlite3.Connection):
        """Run schema migrations for existing databases."""
        # Each migration is idempotent (uses try/except for "column exists")
        migrations = [
            # Phase 5: Add team_id to sessions
            "ALTER TABLE chat_sessions ADD COLUMN team_id TEXT",
            # Sprint 3: Add archived column
            "ALTER TABLE chat_sessions ADD COLUMN archived INTEGER DEFAULT 0",
            # Phase 1: Model orchestration columns
            "ALTER TABLE chat_sessions ADD COLUMN selected_mode TEXT DEFAULT 'intelligent'",
            "ALTER TABLE chat_sessions ADD COLUMN selected_model_id TEXT",
            # Phase 5: Add team_id to messages
            "ALTER TABLE chat_messages ADD COLUMN team_id TEXT",
            # Phase 5: Add team_id to summaries
            "ALTER TABLE conversation_summaries ADD COLUMN team_id TEXT",
            # Phase 5: Add team_id to document chunks
            "ALTER TABLE document_chunks ADD COLUMN team_id TEXT",
            # Phase 5: Add team_id to embeddings
            "ALTER TABLE message_embeddings ADD COLUMN team_id TEXT",
        ]

        for migration in migrations:
            try:
                conn.execute(migration)
            except sqlite3.OperationalError:
                pass  # Column already exists

    def _create_indexes(self, conn: sqlite3.Connection):
        """Create all database indexes."""
        indexes = [
            # Basic indexes
            "CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON chat_messages(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_summary_session ON conversation_summaries(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_chunks_session ON document_chunks(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_chunks_file ON document_chunks(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_embeddings_session ON message_embeddings(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_embeddings_message ON message_embeddings(message_id)",
            # Phase 5: Team isolation indexes
            "CREATE INDEX IF NOT EXISTS idx_sessions_team ON chat_sessions(team_id)",
            "CREATE INDEX IF NOT EXISTS idx_messages_team ON chat_messages(team_id)",
            "CREATE INDEX IF NOT EXISTS idx_summaries_team ON conversation_summaries(team_id)",
            "CREATE INDEX IF NOT EXISTS idx_chunks_team ON document_chunks(team_id)",
            "CREATE INDEX IF NOT EXISTS idx_embeddings_team ON message_embeddings(team_id)",
            # Phase 2: Composite indexes for common queries
            "CREATE INDEX IF NOT EXISTS idx_messages_session_timestamp ON chat_messages(session_id, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_messages_session_role ON chat_messages(session_id, role)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_user_updated ON chat_sessions(user_id, updated_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_team_updated ON chat_sessions(team_id, updated_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_chunks_session_file ON document_chunks(session_id, file_id)",
            # Phase 2: Analytics indexes
            "CREATE INDEX IF NOT EXISTS idx_messages_model ON chat_messages(model)",
            "CREATE INDEX IF NOT EXISTS idx_messages_user_team ON chat_messages(user_id, team_id)",
        ]

        for index_sql in indexes:
            conn.execute(index_sql)

    @property
    def write_lock(self) -> threading.Lock:
        """Get the write lock for thread-safe write operations."""
        return self._write_lock

    def get_connection(self) -> sqlite3.Connection:
        """Public access to thread-local connection."""
        return self._get_connection()
