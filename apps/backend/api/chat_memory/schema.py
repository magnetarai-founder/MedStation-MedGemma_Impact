"""
Chat Memory Database Schema

Schema definitions and migration logic.
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)


def setup_schema(conn: sqlite3.Connection) -> None:
    """Create memory tables and run migrations"""

    # Session metadata
    conn.execute("""
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
    """)

    # Phase 5: Add team_id column if it doesn't exist (migration for existing DBs)
    try:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN team_id TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Sprint 3: Add archived column for session management
    try:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN archived INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Phase 1: Model Orchestration - Add model preference columns
    try:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN selected_mode TEXT DEFAULT 'intelligent'")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN selected_model_id TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Full message history
    conn.execute("""
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
    """)

    # Phase 5: Add team_id column if it doesn't exist
    try:
        conn.execute("ALTER TABLE chat_messages ADD COLUMN team_id TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Conversation summaries (rolling window)
    conn.execute("""
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
    """)

    # Phase 5: Add team_id column if it doesn't exist
    try:
        conn.execute("ALTER TABLE conversation_summaries ADD COLUMN team_id TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Document chunks for RAG
    conn.execute("""
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
    """)

    # Phase 5: Add team_id column if it doesn't exist
    try:
        conn.execute("ALTER TABLE document_chunks ADD COLUMN team_id TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Embeddings for semantic search
    conn.execute("""
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
    """)

    # Phase 5: Add team_id column if it doesn't exist
    try:
        conn.execute("ALTER TABLE message_embeddings ADD COLUMN team_id TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Create indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON chat_messages(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_summary_session ON conversation_summaries(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_session ON document_chunks(session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_file ON document_chunks(file_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_session ON message_embeddings(session_id)")

    # Phase 5: Team isolation indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_team ON chat_sessions(team_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_team ON chat_messages(team_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_summaries_team ON conversation_summaries(team_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_team ON document_chunks(team_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_team ON message_embeddings(team_id)")

    conn.commit()


__all__ = ["setup_schema"]
