"""
Summary Manager for Chat Memory

Handles conversation summaries:
- Create/update rolling summaries
- Session title management
- Summary retrieval
"""
import json
import logging
import sqlite3
from dataclasses import asdict
from datetime import datetime
from typing import Any

from .db_manager import DatabaseManager
from .models import ConversationEvent

logger = logging.getLogger(__name__)


class SummaryManager:
    """
    Manages conversation summaries for sessions.

    Creates rolling summaries that capture recent conversation context
    for long-running sessions.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize summary manager.

        Args:
            db_manager: Shared database manager instance
        """
        self._db = db_manager

    def update(
        self,
        session_id: str,
        events: list[ConversationEvent],
        max_events: int = 30,
        max_summary_chars: int = 1200,
    ):
        """
        Create or update a rolling summary of the conversation.

        Args:
            session_id: Session to update summary for
            events: List of conversation events to summarize
            max_events: Maximum events to include
            max_summary_chars: Maximum summary character length
        """
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
            summary = summary[: max_summary_chars - 1] + "…"

        # Get models used
        models_used = set()
        for ev in trimmed:
            if ev.model:
                models_used.add(ev.model)

        now = datetime.utcnow().isoformat()
        events_json = json.dumps([asdict(ev) for ev in trimmed])

        conn = self._db.get_connection()
        with self._db.write_lock:
            # Check if summary exists
            cur = conn.execute(
                "SELECT id FROM conversation_summaries WHERE session_id = ?",
                (session_id,),
            )
            row = cur.fetchone()

            if row:
                # Update existing summary
                conn.execute(
                    """
                    UPDATE conversation_summaries
                    SET updated_at = ?, summary = ?, events_json = ?, models_used = ?
                    WHERE session_id = ?
                """,
                    (now, summary, events_json, ",".join(sorted(models_used)), session_id),
                )
            else:
                # Insert new summary
                conn.execute(
                    """
                    INSERT INTO conversation_summaries
                    (session_id, created_at, updated_at, summary, events_json, models_used)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (session_id, now, now, summary, events_json, ",".join(sorted(models_used))),
                )

            # Also update session summary
            conn.execute(
                "UPDATE chat_sessions SET summary = ? WHERE id = ?",
                (summary, session_id),
            )

            conn.commit()

    def get(self, session_id: str) -> dict[str, Any] | None:
        """
        Get conversation summary for a session.

        Args:
            session_id: Session to get summary for

        Returns:
            Summary dict or None if not found
        """
        conn = self._db.get_connection()
        cur = conn.execute(
            """
            SELECT session_id, created_at, updated_at, summary, models_used
            FROM conversation_summaries
            WHERE session_id = ?
        """,
            (session_id,),
        )

        row = cur.fetchone()
        if not row:
            return None

        return {
            "session_id": row["session_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "summary": row["summary"],
            "models_used": row["models_used"].split(",") if row["models_used"] else [],
        }

    def update_session_title(
        self,
        session_id: str,
        title: str,
        auto_titled: bool = False,
    ):
        """
        Update session title.

        Args:
            session_id: Session to update
            title: New title
            auto_titled: Whether title was auto-generated
        """
        conn = self._db.get_connection()
        with self._db.write_lock:
            try:
                conn.execute(
                    """
                    UPDATE chat_sessions
                    SET title = ?, auto_titled = ?
                    WHERE id = ?
                """,
                    (title, 1 if auto_titled else 0, session_id),
                )
            except sqlite3.OperationalError:
                # auto_titled column doesn't exist yet, just update title
                conn.execute(
                    """
                    UPDATE chat_sessions
                    SET title = ?
                    WHERE id = ?
                """,
                    (title, session_id),
                )
            conn.commit()
