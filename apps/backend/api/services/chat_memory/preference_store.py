"""
Preference Store for Chat Memory

Handles model preferences and session settings:
- Model selection mode (intelligent vs manual)
- Selected model tracking
- Session archival
"""
import logging
from datetime import datetime
from typing import Any

from .db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class PreferenceStore:
    """
    Manages model preferences and session settings.

    Stores per-session model selection preferences for
    the Apple FM orchestration system.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize preference store.

        Args:
            db_manager: Shared database manager instance
        """
        self._db = db_manager

    def update_session_model(self, session_id: str, model: str) -> None:
        """
        Update the default model for a session.

        Args:
            session_id: Session to update
            model: New default model
        """
        now = datetime.utcnow().isoformat()
        conn = self._db.get_connection()

        with self._db.write_lock:
            conn.execute(
                """
                UPDATE chat_sessions
                SET model = ?, updated_at = ?
                WHERE id = ?
            """,
                (model, now, session_id),
            )
            conn.commit()

    def update_model_preferences(
        self,
        session_id: str,
        selected_mode: str,
        selected_model_id: str | None = None,
    ) -> None:
        """
        Update model selection preferences for a session.

        Args:
            session_id: Session to update
            selected_mode: "intelligent" (Apple FM orchestrator) or "manual" (specific model)
            selected_model_id: Model ID when in manual mode, None when in intelligent mode
        """
        now = datetime.utcnow().isoformat()
        conn = self._db.get_connection()

        with self._db.write_lock:
            conn.execute(
                """
                UPDATE chat_sessions
                SET selected_mode = ?, selected_model_id = ?, updated_at = ?
                WHERE id = ?
            """,
                (selected_mode, selected_model_id, now, session_id),
            )
            conn.commit()

    def get_model_preferences(self, session_id: str) -> dict[str, Any]:
        """
        Get model selection preferences for a session.

        Args:
            session_id: Session to query

        Returns:
            Dict with 'selected_mode' and 'selected_model_id' keys
        """
        conn = self._db.get_connection()
        cur = conn.execute(
            """
            SELECT selected_mode, selected_model_id
            FROM chat_sessions
            WHERE id = ?
        """,
            (session_id,),
        )

        row = cur.fetchone()
        if not row:
            # Default to intelligent mode
            return {"selected_mode": "intelligent", "selected_model_id": None}

        return {
            "selected_mode": row["selected_mode"] or "intelligent",
            "selected_model_id": row["selected_model_id"],
        }

    def set_session_archived(self, session_id: str, archived: bool) -> None:
        """
        Archive or unarchive a session.

        Args:
            session_id: Session to update
            archived: True to archive, False to unarchive
        """
        now = datetime.utcnow().isoformat()
        conn = self._db.get_connection()

        with self._db.write_lock:
            conn.execute(
                """
                UPDATE chat_sessions
                SET archived = ?, updated_at = ?
                WHERE id = ?
            """,
                (1 if archived else 0, now, session_id),
            )
            conn.commit()
