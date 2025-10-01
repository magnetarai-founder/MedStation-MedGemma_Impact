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
MEMORY_DIR = Path(".neutron_data/memory")
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


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
    """

    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = MEMORY_DIR / "chat_memory.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Use WAL mode for better concurrent access
        self.conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=30.0,
            isolation_level='DEFERRED'
        )
        self.conn.row_factory = sqlite3.Row

        # Enable WAL mode and performance optimizations
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self.conn.execute("PRAGMA mmap_size=30000000000")

        # Thread lock for write operations
        self._write_lock = threading.Lock()

        self._setup_database()

    def _setup_database(self):
        """Create memory tables"""

        # Session metadata
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT,
                updated_at TEXT,
                default_model TEXT,
                message_count INTEGER DEFAULT 0,
                models_used TEXT,
                summary TEXT,
                auto_titled INTEGER DEFAULT 0
            )
        """)

        # Full message history
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TEXT,
                role TEXT,
                content TEXT,
                model TEXT,
                tokens INTEGER,
                files_json TEXT,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
            )
        """)

        # Conversation summaries (rolling window)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                created_at TEXT,
                updated_at TEXT,
                summary TEXT,
                events_json TEXT,
                models_used TEXT,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
            )
        """)

        # Document chunks for RAG
        self.conn.execute("""
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
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
            )
        """)

        # Embeddings for semantic search
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS message_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                session_id TEXT,
                embedding_json TEXT,
                created_at TEXT,
                FOREIGN KEY (message_id) REFERENCES chat_messages(id),
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
            )
        """)

        # Create indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON chat_messages(timestamp)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_summary_session ON conversation_summaries(session_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_session ON document_chunks(session_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_file ON document_chunks(file_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_session ON message_embeddings(session_id)")

        self.conn.commit()

    def create_session(self, session_id: str, title: str, model: str) -> Dict[str, Any]:
        """Create a new chat session"""
        now = datetime.utcnow().isoformat()

        with self._write_lock:
            self.conn.execute("""
                INSERT INTO chat_sessions (id, title, created_at, updated_at, default_model, message_count, models_used)
                VALUES (?, ?, ?, ?, ?, 0, ?)
            """, (session_id, title, now, now, model, model))
            self.conn.commit()

        logger.info(f"Created chat session: {session_id}")
        return {
            "id": session_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "model": model,
            "message_count": 0
        }

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metadata"""
        cur = self.conn.execute("""
            SELECT id, title, created_at, updated_at, default_model, message_count, models_used, summary
            FROM chat_sessions WHERE id = ?
        """, (session_id,))

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

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all chat sessions"""
        cur = self.conn.execute("""
            SELECT id, title, created_at, updated_at, default_model, message_count
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
                "message_count": row["message_count"]
            })

        return sessions

    def delete_session(self, session_id: str):
        """Delete a chat session and all its messages"""
        with self._write_lock:
            self.conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            self.conn.execute("DELETE FROM conversation_summaries WHERE session_id = ?", (session_id,))
            self.conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            self.conn.commit()

        logger.info(f"Deleted chat session: {session_id}")

    def add_message(self, session_id: str, event: ConversationEvent):
        """Add a message to the session"""
        files_json = json.dumps(event.files) if event.files else None

        with self._write_lock:
            # Insert message
            self.conn.execute("""
                INSERT INTO chat_messages (session_id, timestamp, role, content, model, tokens, files_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session_id, event.timestamp, event.role, event.content, event.model, event.tokens, files_json))

            # Update session metadata
            now = datetime.utcnow().isoformat()
            self.conn.execute("""
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
                    self.conn.execute("""
                        UPDATE chat_sessions SET models_used = ? WHERE id = ?
                    """, (",".join(sorted(models_used)), session_id))

            self.conn.commit()

    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[ConversationEvent]:
        """Get messages for a session"""
        query = """
            SELECT timestamp, role, content, model, tokens, files_json
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """

        if limit:
            query += f" LIMIT {limit}"

        cur = self.conn.execute(query, (session_id,))

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
        cur = self.conn.execute("""
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

        now = datetime.utcnow().isoformat()
        events_json = json.dumps([asdict(ev) for ev in trimmed])

        with self._write_lock:
            # Check if summary exists
            cur = self.conn.execute(
                "SELECT id FROM conversation_summaries WHERE session_id = ?",
                (session_id,)
            )
            row = cur.fetchone()

            if row:
                # Update existing summary
                self.conn.execute("""
                    UPDATE conversation_summaries
                    SET updated_at = ?, summary = ?, events_json = ?, models_used = ?
                    WHERE session_id = ?
                """, (now, summary, events_json, ",".join(sorted(models_used)), session_id))
            else:
                # Insert new summary
                self.conn.execute("""
                    INSERT INTO conversation_summaries
                    (session_id, created_at, updated_at, summary, events_json, models_used)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, now, now, summary, events_json, ",".join(sorted(models_used))))

            # Also update session summary
            self.conn.execute("""
                UPDATE chat_sessions SET summary = ? WHERE id = ?
            """, (summary, session_id))

            self.conn.commit()

    def get_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation summary"""
        cur = self.conn.execute("""
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
        with self._write_lock:
            # Check if auto_titled column exists
            try:
                self.conn.execute("""
                    UPDATE chat_sessions
                    SET title = ?, auto_titled = ?
                    WHERE id = ?
                """, (title, 1 if auto_titled else 0, session_id))
            except sqlite3.OperationalError:
                # Column doesn't exist yet, just update title
                self.conn.execute("""
                    UPDATE chat_sessions
                    SET title = ?
                    WHERE id = ?
                """, (title, session_id))
            self.conn.commit()

    def store_document_chunks(self, session_id: str, chunks: List[Dict[str, Any]]):
        """Store document chunks for RAG"""
        now = datetime.utcnow().isoformat()

        with self._write_lock:
            for chunk in chunks:
                embedding_json = json.dumps(chunk.get("embedding", []))

                self.conn.execute("""
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

            self.conn.commit()

    def search_document_chunks(self, session_id: str, query_embedding: List[float], top_k: int = 3) -> List[Dict[str, Any]]:
        """Search for relevant document chunks using semantic similarity"""
        cur = self.conn.execute("""
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

    def search_messages_semantic(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search across all messages using semantic similarity"""
        from api.chat_enhancements import SimpleEmbedding

        query_embedding = SimpleEmbedding.create_embedding(query)

        # Get all messages with content
        cur = self.conn.execute("""
            SELECT m.id, m.session_id, m.role, m.content, m.timestamp, m.model, s.title
            FROM chat_messages m
            JOIN chat_sessions s ON m.session_id = s.id
            WHERE length(m.content) > 20
            ORDER BY m.timestamp DESC
            LIMIT 200
        """)

        results = []
        for row in cur.fetchall():
            # Create embedding for message content
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
        return results[:limit]

    def get_analytics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get analytics for a session or all sessions"""
        if session_id:
            # Single session analytics
            cur = self.conn.execute("""
                SELECT COUNT(*) as msg_count, SUM(tokens) as total_tokens
                FROM chat_messages
                WHERE session_id = ?
            """, (session_id,))
            row = cur.fetchone()

            session = self.get_session(session_id)

            return {
                "session_id": session_id,
                "message_count": row["msg_count"],
                "total_tokens": row["total_tokens"] or 0,
                "models_used": session.get("models_used", []) if session else []
            }
        else:
            # Global analytics
            cur = self.conn.execute("""
                SELECT
                    COUNT(DISTINCT session_id) as total_sessions,
                    COUNT(*) as total_messages,
                    SUM(tokens) as total_tokens
                FROM chat_messages
            """)
            row = cur.fetchone()

            # Get model usage stats
            cur = self.conn.execute("""
                SELECT model, COUNT(*) as count
                FROM chat_messages
                WHERE model IS NOT NULL
                GROUP BY model
                ORDER BY count DESC
            """)

            model_stats = [{"model": r["model"], "count": r["count"]} for r in cur.fetchall()]

            return {
                "total_sessions": row["total_sessions"],
                "total_messages": row["total_messages"],
                "total_tokens": row["total_tokens"] or 0,
                "model_usage": model_stats
            }


# Singleton instance
_memory_instance = None


def get_memory() -> NeutronChatMemory:
    """Get singleton memory instance"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = NeutronChatMemory()
    return _memory_instance
