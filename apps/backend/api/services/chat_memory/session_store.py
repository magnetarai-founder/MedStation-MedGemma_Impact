"""
Session Store for Chat Memory

Handles CRUD operations for chat sessions:
- Create, read, update, delete sessions
- User and team scoping
- Admin access methods
"""
import logging
from datetime import datetime
from typing import Any

from .db_manager import DatabaseManager
from .decorators import log_query_performance

logger = logging.getLogger(__name__)


class SessionStore:
    """
    Manages chat session CRUD operations.

    All methods are user/team scoped for security.
    Admin methods are separated for Founder Rights access.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize session store.

        Args:
            db_manager: Shared database manager instance
        """
        self._db = db_manager

    def create(
        self,
        session_id: str,
        title: str,
        model: str,
        user_id: str,
        team_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new chat session.

        Args:
            session_id: Unique session identifier
            title: Session title
            model: Default model for the session
            user_id: Owner user ID
            team_id: Optional team ID for team-scoped sessions

        Returns:
            Created session metadata
        """
        now = datetime.utcnow().isoformat()
        conn = self._db.get_connection()

        with self._db.write_lock:
            conn.execute(
                """
                INSERT INTO chat_sessions
                (id, title, created_at, updated_at, default_model, message_count, models_used, user_id, team_id)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
            """,
                (session_id, title, now, now, model, model, user_id, team_id),
            )
            conn.commit()

        logger.info(f"Created chat session: {session_id} for user: {user_id}")
        return {
            "id": session_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "model": model,
            "message_count": 0,
        }

    def get(
        self,
        session_id: str,
        user_id: str | None = None,
        role: str | None = None,
        team_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Get session metadata with access control.

        Args:
            session_id: Session to retrieve
            user_id: Requesting user ID
            role: User role (god_rights bypasses user filter)
            team_id: Team ID for team-scoped access

        Returns:
            Session metadata or None if not found/not accessible
        """
        conn = self._db.get_connection()

        # Team-scoped access
        if team_id:
            cur = conn.execute(
                """
                SELECT id, title, created_at, updated_at, default_model, message_count,
                       models_used, summary, user_id
                FROM chat_sessions WHERE id = ? AND team_id = ?
                """,
                (session_id, team_id),
            )
        # Founder Rights bypasses user filtering
        elif role == "god_rights":
            cur = conn.execute(
                """
                SELECT id, title, created_at, updated_at, default_model, message_count,
                       models_used, summary, user_id
                FROM chat_sessions WHERE id = ?
                """,
                (session_id,),
            )
        else:
            # Regular users only see their own sessions
            cur = conn.execute(
                """
                SELECT id, title, created_at, updated_at, default_model, message_count,
                       models_used, summary, user_id
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
            "summary": row["summary"],
        }

    @log_query_performance("list_sessions")
    def list(
        self,
        user_id: str | None = None,
        role: str | None = None,
        team_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List chat sessions for a user or team.

        Args:
            user_id: Filter by user ID
            role: User role (not used for listing, admin uses separate methods)
            team_id: Filter by team ID

        Returns:
            List of session metadata dicts
        """
        conn = self._db.get_connection()

        if team_id:
            # Team sessions
            cur = conn.execute(
                """
                SELECT id, title, created_at, updated_at, default_model, message_count,
                       user_id, team_id
                FROM chat_sessions
                WHERE team_id = ?
                ORDER BY updated_at DESC
            """,
                (team_id,),
            )
        else:
            # Personal sessions (team_id IS NULL)
            cur = conn.execute(
                """
                SELECT id, title, created_at, updated_at, default_model, message_count,
                       user_id, team_id
                FROM chat_sessions
                WHERE user_id = ? AND team_id IS NULL
                ORDER BY updated_at DESC
            """,
                (user_id,),
            )

        sessions = []
        for row in cur.fetchall():
            sessions.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "model": row["default_model"],
                    "message_count": row["message_count"],
                    "team_id": row["team_id"],
                }
            )

        return sessions

    def list_all_admin(self) -> list[dict[str, Any]]:
        """
        List ALL sessions across all users (admin only).

        Returns:
            List of all sessions with user_id included
        """
        conn = self._db.get_connection()

        cur = conn.execute(
            """
            SELECT id, title, created_at, updated_at, default_model, message_count, user_id
            FROM chat_sessions
            ORDER BY updated_at DESC
        """
        )

        sessions = []
        for row in cur.fetchall():
            sessions.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "model": row["default_model"],
                    "message_count": row["message_count"],
                    "user_id": row["user_id"],
                }
            )

        return sessions

    def list_user_sessions_admin(self, target_user_id: str) -> list[dict[str, Any]]:
        """
        List a specific user's sessions (admin only).

        Args:
            target_user_id: User whose sessions to retrieve

        Returns:
            List of that user's sessions
        """
        conn = self._db.get_connection()

        cur = conn.execute(
            """
            SELECT id, title, created_at, updated_at, default_model, message_count, user_id
            FROM chat_sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC
        """,
            (target_user_id,),
        )

        sessions = []
        for row in cur.fetchall():
            sessions.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "model": row["default_model"],
                    "message_count": row["message_count"],
                    "user_id": row["user_id"],
                }
            )

        return sessions

    def delete(
        self,
        session_id: str,
        user_id: str | None = None,
        role: str | None = None,
    ) -> bool:
        """
        Delete a session and all related data.

        Args:
            session_id: Session to delete
            user_id: Requesting user ID
            role: User role (god_rights bypasses ownership check)

        Returns:
            True if deleted, False if access denied
        """
        conn = self._db.get_connection()

        with self._db.write_lock:
            # Verify ownership (unless Founder Rights)
            if role != "god_rights":
                cur = conn.execute(
                    "SELECT user_id FROM chat_sessions WHERE id = ?",
                    (session_id,),
                )
                row = cur.fetchone()
                if not row or row["user_id"] != user_id:
                    logger.warning(
                        f"User {user_id} attempted to delete session {session_id} they don't own"
                    )
                    return False

            # Delete session and all related data (cascade)
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM conversation_summaries WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM document_chunks WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            conn.commit()

        logger.info(f"Deleted chat session: {session_id} (user: {user_id}, role: {role})")
        return True

    def update_timestamp(self, session_id: str):
        """Update session's updated_at timestamp."""
        now = datetime.utcnow().isoformat()
        conn = self._db.get_connection()

        with self._db.write_lock:
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )
            conn.commit()

    def increment_message_count(self, session_id: str):
        """Increment the message count for a session."""
        now = datetime.utcnow().isoformat()
        conn = self._db.get_connection()

        with self._db.write_lock:
            conn.execute(
                """
                UPDATE chat_sessions
                SET updated_at = ?, message_count = message_count + 1
                WHERE id = ?
            """,
                (now, session_id),
            )
            conn.commit()

    def update_models_used(self, session_id: str, models: set[str]):
        """Update the models_used field for a session."""
        conn = self._db.get_connection()

        with self._db.write_lock:
            conn.execute(
                "UPDATE chat_sessions SET models_used = ? WHERE id = ?",
                (",".join(sorted(models)), session_id),
            )
            conn.commit()

    def get_owner_and_team(self, session_id: str) -> tuple[str | None, str | None]:
        """
        Get the owner user_id and team_id for a session.

        Returns:
            Tuple of (user_id, team_id), both may be None
        """
        conn = self._db.get_connection()
        cur = conn.execute(
            "SELECT user_id, team_id FROM chat_sessions WHERE id = ?",
            (session_id,),
        )
        row = cur.fetchone()
        if not row:
            return None, None
        return row["user_id"], row["team_id"]
