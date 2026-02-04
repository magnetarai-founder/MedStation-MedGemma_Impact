"""
Message Store for Chat Memory

Handles chat message operations:
- Add messages to sessions
- Retrieve messages (full history, recent, batch)
- Message metadata tracking
"""
import json
import logging
from typing import Any

from .db_manager import DatabaseManager
from .decorators import log_query_performance
from .models import ConversationEvent

logger = logging.getLogger(__name__)


class MessageStore:
    """
    Manages chat message storage and retrieval.

    Messages are associated with sessions and inherit
    user_id/team_id from their parent session.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize message store.

        Args:
            db_manager: Shared database manager instance
        """
        self._db = db_manager

    def add(
        self,
        session_id: str,
        event: ConversationEvent,
        owner_id: str | None = None,
        team_id: str | None = None,
    ):
        """
        Add a message to a session.

        Args:
            session_id: Target session ID
            event: ConversationEvent to store
            owner_id: User ID (inherited from session if not provided)
            team_id: Team ID (inherited from session if not provided)
        """
        files_json = json.dumps(event.files) if event.files else None
        conn = self._db.get_connection()

        with self._db.write_lock:
            conn.execute(
                """
                INSERT INTO chat_messages
                (session_id, timestamp, role, content, model, tokens, files_json, user_id, team_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    event.timestamp,
                    event.role,
                    event.content,
                    event.model,
                    event.tokens,
                    files_json,
                    owner_id,
                    team_id,
                ),
            )
            conn.commit()

    @log_query_performance("get_messages")
    def get_all(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[ConversationEvent]:
        """
        Get all messages for a session.

        Args:
            session_id: Session to retrieve messages from
            limit: Optional maximum number of messages

        Returns:
            List of ConversationEvent objects in chronological order
        """
        conn = self._db.get_connection()
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
            messages.append(
                ConversationEvent(
                    timestamp=row["timestamp"],
                    role=row["role"],
                    content=row["content"],
                    model=row["model"],
                    tokens=row["tokens"],
                    files=files,
                )
            )

        return messages

    @log_query_performance("get_recent_messages")
    def get_recent(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[ConversationEvent]:
        """
        Get recent messages for context window.

        Args:
            session_id: Session to retrieve messages from
            limit: Maximum number of recent messages

        Returns:
            List of ConversationEvent objects in chronological order
        """
        conn = self._db.get_connection()
        cur = conn.execute(
            """
            SELECT timestamp, role, content, model, tokens, files_json
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (session_id, limit),
        )

        messages = []
        for row in cur.fetchall():
            files = json.loads(row["files_json"]) if row["files_json"] else None
            messages.append(
                ConversationEvent(
                    timestamp=row["timestamp"],
                    role=row["role"],
                    content=row["content"],
                    model=row["model"],
                    tokens=row["tokens"],
                    files=files,
                )
            )

        # Reverse to chronological order
        return list(reversed(messages))

    @log_query_performance("get_messages_for_sessions_batch")
    def get_for_sessions(
        self,
        session_ids: list[str],
    ) -> dict[str, list[ConversationEvent]]:
        """
        Batch fetch messages for multiple sessions.

        This prevents N+1 queries when loading multiple sessions.

        Args:
            session_ids: List of session IDs to fetch messages for

        Returns:
            Dictionary mapping session_id -> list of ConversationEvent objects
        """
        if not session_ids:
            return {}

        conn = self._db.get_connection()

        # Create placeholders for IN clause (safe: only integers used for count)
        placeholders = ",".join("?" * len(session_ids))
        query = f"""
            SELECT session_id, timestamp, role, content, model, tokens, files_json
            FROM chat_messages
            WHERE session_id IN ({placeholders})
            ORDER BY session_id, timestamp ASC
        """  # noqa: S608 - placeholders are "?" chars, actual values are parameterized

        cur = conn.execute(query, session_ids)

        # Group messages by session_id
        messages_by_session: dict[str, list[ConversationEvent]] = {
            sid: [] for sid in session_ids
        }

        for row in cur.fetchall():
            files = json.loads(row["files_json"]) if row["files_json"] else None
            event = ConversationEvent(
                timestamp=row["timestamp"],
                role=row["role"],
                content=row["content"],
                model=row["model"],
                tokens=row["tokens"],
                files=files,
            )
            messages_by_session[row["session_id"]].append(event)

        return messages_by_session

    def search_semantic(
        self,
        query: str,
        limit: int = 10,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search across messages using semantic similarity.

        Args:
            query: Search query text
            limit: Maximum results to return
            user_id: Filter by user ID
            team_id: Filter by team ID (takes precedence)

        Returns:
            List of matching messages with similarity scores
        """
        from api.chat_enhancements import SimpleEmbedding

        query_embedding = SimpleEmbedding.create_embedding(query)
        conn = self._db.get_connection()

        if team_id:
            query_sql = """
                SELECT m.id, m.session_id, m.role, m.content, m.timestamp, m.model,
                       s.title, m.team_id
                FROM chat_messages m
                JOIN chat_sessions s ON m.session_id = s.id
                WHERE length(m.content) > 20 AND m.team_id = ?
                ORDER BY m.timestamp DESC
                LIMIT 200
            """
            cur = conn.execute(query_sql, (team_id,))
        else:
            query_sql = """
                SELECT m.id, m.session_id, m.role, m.content, m.timestamp, m.model,
                       s.title, m.team_id
                FROM chat_messages m
                JOIN chat_sessions s ON m.session_id = s.id
                WHERE length(m.content) > 20 AND m.user_id = ? AND m.team_id IS NULL
                ORDER BY m.timestamp DESC
                LIMIT 200
            """
            cur = conn.execute(query_sql, (user_id,))

        results = []
        for row in cur.fetchall():
            # Create embedding for message content
            msg_embedding = SimpleEmbedding.create_embedding(row["content"])
            similarity = SimpleEmbedding.cosine_similarity(query_embedding, msg_embedding)

            if similarity > 0.3:  # Threshold
                results.append(
                    {
                        "session_id": row["session_id"],
                        "session_title": row["title"],
                        "role": row["role"],
                        "content": row["content"][:200],
                        "timestamp": row["timestamp"],
                        "model": row["model"],
                        "similarity": similarity,
                    }
                )

        # Sort by similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]
