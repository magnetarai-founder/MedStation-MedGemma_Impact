"""
Chat Memory Summary Operations

Rolling conversation summaries.
"""

import json
import logging
from dataclasses import asdict
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any

from .models import ConversationEvent

logger = logging.getLogger(__name__)


class SummaryMixin:
    """Mixin providing summary operations"""

    def update_summary(
        self,
        session_id: str,
        events: Optional[List[ConversationEvent]] = None,
        max_events: int = 30,
        max_summary_chars: int = 1200
    ) -> None:
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


__all__ = ["SummaryMixin"]
