"""
Chat Memory Message Operations

Add, retrieve, and manage chat messages.
"""

import json
import logging
from datetime import datetime, UTC
from typing import List, Optional

from .models import ConversationEvent

logger = logging.getLogger(__name__)


class MessageMixin:
    """Mixin providing message operations"""

    def add_message(self, session_id: str, event: ConversationEvent) -> None:
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
                    try:
                        from api.chat_enhancements import SimpleEmbedding
                    except ImportError:
                        from chat_enhancements import SimpleEmbedding
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

    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ConversationEvent]:
        """Get recent messages for context window with pagination

        Args:
            session_id: Chat session ID
            limit: Maximum number of messages to return
            offset: Number of messages to skip (for pagination)

        Returns:
            Messages in chronological order (oldest first within the page)
        """
        conn = self._get_connection()
        cur = conn.execute("""
            SELECT timestamp, role, content, model, tokens, files_json
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """, (session_id, limit, offset))

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

    def count_messages(self, session_id: str) -> int:
        """Count total messages in a session (for pagination)"""
        conn = self._get_connection()
        cur = conn.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE session_id = ?",
            (session_id,)
        )
        return cur.fetchone()[0]


__all__ = ["MessageMixin"]
