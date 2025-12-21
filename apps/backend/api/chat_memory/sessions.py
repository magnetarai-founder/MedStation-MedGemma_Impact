"""
Chat Memory Session Operations

CRUD operations for chat sessions.
"""

import sqlite3
import logging
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class SessionMixin:
    """Mixin providing session CRUD operations"""

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


__all__ = ["SessionMixin"]
