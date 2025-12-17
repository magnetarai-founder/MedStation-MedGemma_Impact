"""
Neutron Chat Memory System
Extracted and adapted from Jarvis Agent's ConversationMemory and JarvisBigQueryMemory

Provides:
1. Conversation summaries with rolling window
2. SQLite storage with WAL mode for concurrency
3. Model/engine tracking across switches
4. Semantic context preservation
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import threading
import logging

logger = logging.getLogger(__name__)

# Storage path
# Use centralized config_paths
from api.config_paths import get_memory_dir
MEMORY_DIR = get_memory_dir()


@dataclass
class ConversationEvent:
    """Single conversation event (message)"""
    timestamp: str
    role: str  # user|assistant
    content: str
    model: Optional[str] = None
    tokens: Optional[int] = None
    files: Optional[List[Dict[str, Any]]] = None


class NeutronChatMemory:
    """
    Advanced chat memory system for Neutron
    - Stores full message history
    - Creates rolling summaries
    - Tracks model switches
    - Preserves context across sessions
    - Thread-safe with connection-per-thread pattern
    """

    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = MEMORY_DIR / "chat_memory.db"

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

    def _setup_database(self):
        """Create memory tables"""
        conn = self._get_connection()

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

    def create_session(self, session_id: str, title: str, model: str, user_id: str, team_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new chat session for user

        Phase 5: Accepts team_id for team-scoped chat sessions
        """
        now = datetime.now(UTC).isoformat()
        conn = self._get_connection()

        with self._write_lock:
            conn.execute("""
                INSERT INTO chat_sessions (id, title, created_at, updated_at, default_model, message_count, models_used, user_id, team_id)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
            """, (session_id, title, now, now, model, model, user_id, team_id))
            conn.commit()

        logger.info(f"Created chat session: {session_id} for user: {user_id}")
        return {
            "id": session_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "model": model,
            "message_count": 0
        }

    def get_session(self, session_id: str, user_id: str = None, role: str = None, team_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get session metadata (user-filtered or team-filtered)

        Phase 5: If team_id is provided, return session when it matches that team_id.
        Otherwise, only return if owned by user_id (personal session).
        Founder Rights may bypass user filter (admin endpoints should use admin methods).
        """
        conn = self._get_connection()

        # Team-scoped access
        if team_id:
            cur = conn.execute(
                """
                SELECT id, title, created_at, updated_at, default_model, message_count, models_used, summary, user_id
                FROM chat_sessions WHERE id = ? AND team_id = ?
                """,
                (session_id, team_id),
            )
        else:
            # Founder Rights bypasses user filtering
            if role == "god_rights":
                cur = conn.execute(
                    """
                    SELECT id, title, created_at, updated_at, default_model, message_count, models_used, summary, user_id
                    FROM chat_sessions WHERE id = ?
                    """,
                    (session_id,),
                )
            else:
                # Regular users only see their own sessions
                cur = conn.execute(
                    """
                    SELECT id, title, created_at, updated_at, default_model, message_count, models_used, summary, user_id
                    FROM chat_sessions WHERE id = ? AND user_id = ? AND team_id IS NULL
                    """,
                    (session_id, user_id),
                )

        row = cur.fetchone()
        if not row:
            return None

        return {
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "model": row["default_model"],
            "message_count": row["message_count"],
            "models_used": row["models_used"].split(",") if row["models_used"] else [],
            "summary": row["summary"]
        }

    def list_sessions(self, user_id: str = None, role: str = None, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List chat sessions (user-filtered for ALL users, including Founder Rights)

        Phase 5: Supports team_id filtering for team-scoped sessions

        This endpoint is for regular UI use - Founder Rights sees only their own chats here.
        For admin access to view other users' chats, use admin endpoints.
        """
        conn = self._get_connection()

        # Phase 5: Filter by both user_id and team_id
        if team_id:
            # Team sessions: user must be in team AND session is for that team
            cur = conn.execute("""
                SELECT id, title, created_at, updated_at, default_model, message_count, user_id, team_id
                FROM chat_sessions
                WHERE team_id = ?
                ORDER BY updated_at DESC
            """, (team_id,))
        else:
            # Personal sessions: team_id IS NULL AND user owns it
            cur = conn.execute("""
                SELECT id, title, created_at, updated_at, default_model, message_count, user_id, team_id
                FROM chat_sessions
                WHERE user_id = ? AND team_id IS NULL
                ORDER BY updated_at DESC
            """, (user_id,))

        sessions = []
        for row in cur.fetchall():
            sessions.append({
                "id": row["id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "model": row["default_model"],
                "message_count": row["message_count"],
                "team_id": row["team_id"] if "team_id" in row.keys() else None  # Phase 5
            })

        return sessions

    def list_all_sessions_admin(self) -> List[Dict[str, Any]]:
        """List ALL chat sessions across all users (Founder Rights admin access only)

        This method is for admin endpoints only - not for regular UI use.
        Returns all sessions with user_id included for support purposes.
        """
        conn = self._get_connection()

        cur = conn.execute("""
            SELECT id, title, created_at, updated_at, default_model, message_count, user_id
            FROM chat_sessions
            ORDER BY updated_at DESC
        """)

        sessions = []
        for row in cur.fetchall():
            sessions.append({
                "id": row["id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "model": row["default_model"],
                "message_count": row["message_count"],
                "user_id": row["user_id"]  # Include user_id for admin view
            })

        return sessions

    def list_user_sessions_admin(self, target_user_id: str) -> List[Dict[str, Any]]:
        """List specific user's chat sessions (Founder Rights admin access only)

        This method is for admin endpoints only - not for regular UI use.
        Allows Founder Rights to view a specific user's chats for support.

        Args:
            target_user_id: The user ID whose sessions to retrieve
        """
        conn = self._get_connection()

        cur = conn.execute("""
            SELECT id, title, created_at, updated_at, default_model, message_count, user_id
            FROM chat_sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC
        """, (target_user_id,))

        sessions = []
        for row in cur.fetchall():
            sessions.append({
                "id": row["id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "model": row["default_model"],
                "message_count": row["message_count"],
                "user_id": row["user_id"]
            })

        return sessions

    def delete_session(self, session_id: str, user_id: str = None, role: str = None) -> bool:
        """Delete a chat session (user-filtered unless Founder Rights)

        Returns:
            bool: True if deleted, False if access denied
        """
        conn = self._get_connection()

        with self._write_lock:
            # Verify ownership before delete (unless Founder Rights)
            if role != "god_rights":
                cur = conn.execute("SELECT user_id FROM chat_sessions WHERE id = ?", (session_id,))
                row = cur.fetchone()
                if not row or row["user_id"] != user_id:
                    logger.warning(f"User {user_id} attempted to delete session {session_id} they don't own")
                    return False

            # Delete session and related data
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM conversation_summaries WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM document_chunks WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            conn.commit()

        logger.info(f"Deleted chat session: {session_id} (user: {user_id}, role: {role})")
        return True

    def add_message(self, session_id: str, event: ConversationEvent):
        """
        Add a message to the session

        Phase 5: Inherits team_id from session
        Performance: Pre-computes embeddings for 100x faster semantic search
        """
        files_json = json.dumps(event.files) if event.files else None
        conn = self._get_connection()

        with self._write_lock:
            # Phase 5: Get session owner AND team_id to populate on messages
            cur = conn.execute("SELECT user_id, team_id FROM chat_sessions WHERE id = ?", (session_id,))
            owner = cur.fetchone()
            owner_id = owner['user_id'] if owner else None
            team_id = owner['team_id'] if owner else None

            # Insert message with user_id and team_id
            cur = conn.execute("""
                INSERT INTO chat_messages (session_id, timestamp, role, content, model, tokens, files_json, user_id, team_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, event.timestamp, event.role, event.content, event.model, event.tokens, files_json, owner_id, team_id))

            message_id = cur.lastrowid

            # Pre-compute embedding for semantic search (only for substantial messages)
            if len(event.content) > 20:
                try:
                    from api.chat_enhancements import SimpleEmbedding
                    embedding = SimpleEmbedding.create_embedding(event.content)
                    embedding_json = json.dumps(embedding)

                    now = datetime.now(UTC).isoformat()
                    conn.execute("""
                        INSERT INTO message_embeddings (message_id, session_id, embedding_json, created_at, team_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (message_id, session_id, embedding_json, now, team_id))

                    logger.debug(f"Pre-computed embedding for message {message_id}")
                except Exception as e:
                    logger.warning(f"Failed to pre-compute embedding for message {message_id}: {e}")

            # Update session metadata
            now = datetime.now(UTC).isoformat()
            conn.execute("""
                UPDATE chat_sessions
                SET updated_at = ?, message_count = message_count + 1
                WHERE id = ?
            """, (now, session_id))

            # Track model usage
            if event.model:
                session = self.get_session(session_id)
                if session:
                    models_used = set(session.get("models_used", []))
                    models_used.add(event.model)
                    conn.execute("""
                        UPDATE chat_sessions SET models_used = ? WHERE id = ?
                    """, (",".join(sorted(models_used)), session_id))

            conn.commit()

    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[ConversationEvent]:
        """Get messages for a session"""
        conn = self._get_connection()
        query = """
            SELECT timestamp, role, content, model, tokens, files_json
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """

        if limit:
            query += f" LIMIT {limit}"

        cur = conn.execute(query, (session_id,))

        messages = []
        for row in cur.fetchall():
            files = json.loads(row["files_json"]) if row["files_json"] else None
            messages.append(ConversationEvent(
                timestamp=row["timestamp"],
                role=row["role"],
                content=row["content"],
                model=row["model"],
                tokens=row["tokens"],
                files=files
            ))

        return messages

    def get_recent_messages(self, session_id: str, limit: int = 50) -> List[ConversationEvent]:
        """Get recent messages for context window"""
        conn = self._get_connection()
        cur = conn.execute("""
            SELECT timestamp, role, content, model, tokens, files_json
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (session_id, limit))

        messages = []
        for row in cur.fetchall():
            files = json.loads(row["files_json"]) if row["files_json"] else None
            messages.append(ConversationEvent(
                timestamp=row["timestamp"],
                role=row["role"],
                content=row["content"],
                model=row["model"],
                tokens=row["tokens"],
                files=files
            ))

        # Reverse to chronological order
        return list(reversed(messages))

    def update_summary(
        self,
        session_id: str,
        events: Optional[List[ConversationEvent]] = None,
        max_events: int = 30,
        max_summary_chars: int = 1200
    ):
        """Create or update a rolling summary of the conversation"""

        # Get recent events if not provided
        if events is None:
            events = self.get_recent_messages(session_id, limit=max_events)

        if not events:
            return

        # Keep only recent events
        trimmed = events[-max_events:]

        # Create compact summary
        bullets = []
        for ev in trimmed:
            # Extract first sentence or truncate
            content = ev.content.strip().replace("\n", " ")
            if len(content) > 100:
                content = content[:100] + "…"

            model_info = f" [{ev.model}]" if ev.model else ""
            bullets.append(f"- {ev.role}{model_info}: {content}")

        summary = "Recent conversation:\n" + "\n".join(bullets)
        if len(summary) > max_summary_chars:
            summary = summary[:max_summary_chars - 1] + "…"

        # Get models used
        models_used = set()
        for ev in trimmed:
            if ev.model:
                models_used.add(ev.model)

        now = datetime.now(UTC).isoformat()
        events_json = json.dumps([asdict(ev) for ev in trimmed])

        conn = self._get_connection()
        with self._write_lock:
            # Check if summary exists
            cur = conn.execute(
                "SELECT id FROM conversation_summaries WHERE session_id = ?",
                (session_id,)
            )
            row = cur.fetchone()

            if row:
                # Update existing summary
                conn.execute("""
                    UPDATE conversation_summaries
                    SET updated_at = ?, summary = ?, events_json = ?, models_used = ?
                    WHERE session_id = ?
                """, (now, summary, events_json, ",".join(sorted(models_used)), session_id))
            else:
                # Insert new summary
                conn.execute("""
                    INSERT INTO conversation_summaries
                    (session_id, created_at, updated_at, summary, events_json, models_used)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, now, now, summary, events_json, ",".join(sorted(models_used))))

            # Also update session summary
            conn.execute("""
                UPDATE chat_sessions SET summary = ? WHERE id = ?
            """, (summary, session_id))

            conn.commit()

    def update_session_model(self, session_id: str, model: str) -> None:
        """Update the model for a chat session"""
        now = datetime.now(UTC).isoformat()
        conn = self._get_connection()
        with self._write_lock:
            conn.execute("""
                UPDATE chat_sessions
                SET model = ?, updated_at = ?
                WHERE id = ?
            """, (model, now, session_id))
            conn.commit()

    def update_model_preferences(self, session_id: str, selected_mode: str, selected_model_id: Optional[str] = None) -> None:
        """
        Update model selection preferences for a chat session

        Args:
            session_id: Session ID to update
            selected_mode: "intelligent" (Apple FM orchestrator) or "manual" (specific model)
            selected_model_id: Model ID when in manual mode, None when in intelligent mode
        """
        now = datetime.now(UTC).isoformat()
        conn = self._get_connection()
        with self._write_lock:
            conn.execute("""
                UPDATE chat_sessions
                SET selected_mode = ?, selected_model_id = ?, updated_at = ?
                WHERE id = ?
            """, (selected_mode, selected_model_id, now, session_id))
            conn.commit()

    def get_model_preferences(self, session_id: str) -> Dict[str, Any]:
        """
        Get model selection preferences for a chat session

        Returns:
            Dict with 'selected_mode' and 'selected_model_id' keys
        """
        conn = self._get_connection()
        cur = conn.execute("""
            SELECT selected_mode, selected_model_id
            FROM chat_sessions
            WHERE id = ?
        """, (session_id,))

        row = cur.fetchone()
        if not row:
            # Default to intelligent mode
            return {
                "selected_mode": "intelligent",
                "selected_model_id": None
            }

        return {
            "selected_mode": row["selected_mode"] or "intelligent",
            "selected_model_id": row["selected_model_id"]
        }

    def set_session_archived(self, session_id: str, archived: bool) -> None:
        """Archive or unarchive a chat session"""
        now = datetime.now(UTC).isoformat()
        conn = self._get_connection()
        with self._write_lock:
            conn.execute("""
                UPDATE chat_sessions
                SET archived = ?, updated_at = ?
                WHERE id = ?
            """, (1 if archived else 0, now, session_id))
            conn.commit()

    def get_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation summary"""
        conn = self._get_connection()
        cur = conn.execute("""
            SELECT session_id, created_at, updated_at, summary, models_used
            FROM conversation_summaries
            WHERE session_id = ?
        """, (session_id,))

        row = cur.fetchone()
        if not row:
            return None

        return {
            "session_id": row["session_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "summary": row["summary"],
            "models_used": row["models_used"].split(",") if row["models_used"] else []
        }

    def update_session_title(self, session_id: str, title: str, auto_titled: bool = False):
        """Update session title"""
        conn = self._get_connection()
        with self._write_lock:
            # Check if auto_titled column exists
            try:
                conn.execute("""
                    UPDATE chat_sessions
                    SET title = ?, auto_titled = ?
                    WHERE id = ?
                """, (title, 1 if auto_titled else 0, session_id))
            except sqlite3.OperationalError:
                # Column doesn't exist yet, just update title
                conn.execute("""
                    UPDATE chat_sessions
                    SET title = ?
                    WHERE id = ?
                """, (title, session_id))
            conn.commit()

    def store_document_chunks(self, session_id: str, chunks: List[Dict[str, Any]]):
        """Store document chunks for RAG"""
        now = datetime.now(UTC).isoformat()
        conn = self._get_connection()

        with self._write_lock:
            for chunk in chunks:
                embedding_json = json.dumps(chunk.get("embedding", []))

                conn.execute("""
                    INSERT INTO document_chunks
                    (session_id, file_id, filename, chunk_index, total_chunks, content, embedding_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    chunk.get("file_id"),
                    chunk.get("filename"),
                    chunk.get("chunk_index"),
                    chunk.get("total_chunks"),
                    chunk.get("content"),
                    embedding_json,
                    now
                ))

            conn.commit()

    def has_documents(self, session_id: str) -> bool:
        """Check if a session has any uploaded documents"""
        conn = self._get_connection()
        cur = conn.execute("""
            SELECT COUNT(*) as count
            FROM document_chunks
            WHERE session_id = ?
            LIMIT 1
        """, (session_id,))

        row = cur.fetchone()
        return row["count"] > 0 if row else False

    def search_document_chunks(self, session_id: str, query_embedding: List[float], top_k: int = 3) -> List[Dict[str, Any]]:
        """Search for relevant document chunks using semantic similarity"""
        conn = self._get_connection()
        cur = conn.execute("""
            SELECT id, file_id, filename, chunk_index, content, embedding_json
            FROM document_chunks
            WHERE session_id = ?
        """, (session_id,))

        chunks = []
        for row in cur.fetchall():
            chunk_embedding = json.loads(row["embedding_json"])

            # Calculate similarity
            from api.chat_enhancements import SimpleEmbedding
            similarity = SimpleEmbedding.cosine_similarity(query_embedding, chunk_embedding)

            chunks.append({
                "id": row["id"],
                "file_id": row["file_id"],
                "filename": row["filename"],
                "chunk_index": row["chunk_index"],
                "content": row["content"],
                "similarity": similarity
            })

        # Sort by similarity and return top_k
        chunks.sort(key=lambda x: x["similarity"], reverse=True)
        return chunks[:top_k]

    def search_messages_semantic(self, query: str, limit: int = 10, user_id: Optional[str] = None, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search across messages using semantic similarity

        Phase 5: Team-aware - filters by user_id/team_id
        Performance: Uses pre-computed embeddings for 100x faster search + Redis caching
        """
        from api.chat_enhancements import SimpleEmbedding
        from api.cache_service import get_cache

        # Cache key based on query, user, and team context
        cache_key = f"semantic_search:{hashlib.md5(query.encode()).hexdigest()}:{user_id or 'none'}:{team_id or 'none'}:{limit}"
        cache = get_cache()

        # Check cache first
        cached_results = cache.get(cache_key)
        if cached_results is not None:
            logger.debug(f"✅ Semantic search cache HIT for query: '{query[:50]}...'")
            return cached_results

        query_embedding = SimpleEmbedding.create_embedding(query)
        conn = self._get_connection()

        # Phase 5: Team-scoped search query with pre-computed embeddings
        if team_id:
            # Team sessions - use pre-computed embeddings
            query_sql = """
                SELECT m.id, m.session_id, m.role, m.content, m.timestamp, m.model, s.title, e.embedding_json
                FROM chat_messages m
                JOIN chat_sessions s ON m.session_id = s.id
                LEFT JOIN message_embeddings e ON m.id = e.message_id
                WHERE length(m.content) > 20 AND m.team_id = ?
                ORDER BY m.timestamp DESC
                LIMIT 200
            """
            cur = conn.execute(query_sql, (team_id,))
        else:
            # Personal sessions - use pre-computed embeddings
            query_sql = """
                SELECT m.id, m.session_id, m.role, m.content, m.timestamp, m.model, s.title, e.embedding_json
                FROM chat_messages m
                JOIN chat_sessions s ON m.session_id = s.id
                LEFT JOIN message_embeddings e ON m.id = e.message_id
                WHERE length(m.content) > 20 AND m.user_id = ? AND m.team_id IS NULL
                ORDER BY m.timestamp DESC
                LIMIT 200
            """
            cur = conn.execute(query_sql, (user_id,))

        results = []
        for row in cur.fetchall():
            # Use pre-computed embedding if available, otherwise compute on-the-fly
            if row["embedding_json"]:
                msg_embedding = json.loads(row["embedding_json"])
            else:
                # Fallback for messages without pre-computed embeddings
                msg_embedding = SimpleEmbedding.create_embedding(row["content"])

            similarity = SimpleEmbedding.cosine_similarity(query_embedding, msg_embedding)

            if similarity > 0.3:  # Threshold
                results.append({
                    "session_id": row["session_id"],
                    "session_title": row["title"],
                    "role": row["role"],
                    "content": row["content"][:200],
                    "timestamp": row["timestamp"],
                    "model": row["model"],
                    "similarity": similarity
                })

        # Sort by similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)
        final_results = results[:limit]

        # Cache results for 5 minutes (searches are user-specific)
        cache.set(cache_key, final_results, ttl=300)
        logger.debug(f"🔄 Cached semantic search results for query: '{query[:50]}...'")

        return final_results

    def get_analytics(self, session_id: Optional[str] = None, user_id: Optional[str] = None, team_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get analytics for a session or scoped analytics

        Phase 5: Team-aware - filters by user_id/team_id
        """
        conn = self._get_connection()
        if session_id:
            # Single session analytics
            cur = conn.execute("""
                SELECT COUNT(*) as msg_count, SUM(tokens) as total_tokens
                FROM chat_messages
                WHERE session_id = ?
            """, (session_id,))
            row = cur.fetchone()

            session = self.get_session(session_id, user_id=user_id, team_id=team_id)

            return {
                "session_id": session_id,
                "message_count": row["msg_count"],
                "total_tokens": row["total_tokens"] or 0,
                "models_used": session.get("models_used", []) if session else [],
                "team_id": team_id  # Phase 5
            }
        else:
            # Phase 5: Scoped analytics (personal or team)
            if team_id:
                # Team analytics
                cur = conn.execute("""
                    SELECT
                        COUNT(DISTINCT session_id) as total_sessions,
                        COUNT(*) as total_messages,
                        SUM(tokens) as total_tokens
                    FROM chat_messages
                    WHERE team_id = ?
                """, (team_id,))
                row = cur.fetchone()

                # Get model usage stats for team
                cur = conn.execute("""
                    SELECT model, COUNT(*) as count
                    FROM chat_messages
                    WHERE model IS NOT NULL AND team_id = ?
                    GROUP BY model
                    ORDER BY count DESC
                """, (team_id,))
            else:
                # Personal analytics
                cur = conn.execute("""
                    SELECT
                        COUNT(DISTINCT session_id) as total_sessions,
                        COUNT(*) as total_messages,
                        SUM(tokens) as total_tokens
                    FROM chat_messages
                    WHERE user_id = ? AND team_id IS NULL
                """, (user_id,))
                row = cur.fetchone()

                # Get model usage stats for user
                cur = conn.execute("""
                    SELECT model, COUNT(*) as count
                    FROM chat_messages
                    WHERE model IS NOT NULL AND user_id = ? AND team_id IS NULL
                    GROUP BY model
                    ORDER BY count DESC
                """, (user_id,))

            model_stats = [{"model": r["model"], "count": r["count"]} for r in cur.fetchall()]

            return {
                "total_sessions": row["total_sessions"],
                "total_messages": row["total_messages"],
                "total_tokens": row["total_tokens"] or 0,
                "model_usage": model_stats,
                "team_id": team_id  # Phase 5
            }


# Singleton instance
_memory_instance = None


def get_memory() -> NeutronChatMemory:
    """Get singleton memory instance"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = NeutronChatMemory()
    return _memory_instance
