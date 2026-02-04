"""
Analytics Engine for Chat Memory

Handles analytics queries:
- Session analytics
- User analytics
- Team analytics
- Model usage statistics
"""
import logging
from typing import Any

from .db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """
    Provides analytics for chat memory data.

    Supports session-level, user-level, and team-level analytics
    with model usage statistics.
    """

    def __init__(self, db_manager: DatabaseManager, session_store=None):
        """
        Initialize analytics engine.

        Args:
            db_manager: Shared database manager instance
            session_store: SessionStore for session lookups (optional)
        """
        self._db = db_manager
        self._session_store = session_store

    def get_session_analytics(
        self,
        session_id: str,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Get analytics for a single session.

        Args:
            session_id: Session to analyze
            user_id: User ID for access control
            team_id: Team ID for team-scoped access

        Returns:
            Analytics dict with message count, tokens, models used
        """
        conn = self._db.get_connection()
        cur = conn.execute(
            """
            SELECT COUNT(*) as msg_count, SUM(tokens) as total_tokens
            FROM chat_messages
            WHERE session_id = ?
        """,
            (session_id,),
        )
        row = cur.fetchone()

        # Get models used from session if session_store is available
        models_used = []
        if self._session_store:
            session = self._session_store.get(session_id, user_id=user_id, team_id=team_id)
            if session:
                models_used = session.get("models_used", [])

        return {
            "session_id": session_id,
            "message_count": row["msg_count"],
            "total_tokens": row["total_tokens"] or 0,
            "models_used": models_used,
            "team_id": team_id,
        }

    def get_team_analytics(self, team_id: str) -> dict[str, Any]:
        """
        Get analytics for a team.

        Args:
            team_id: Team to analyze

        Returns:
            Analytics dict with session count, message count, tokens, model usage
        """
        conn = self._db.get_connection()
        cur = conn.execute(
            """
            SELECT
                COUNT(DISTINCT session_id) as total_sessions,
                COUNT(*) as total_messages,
                SUM(tokens) as total_tokens
            FROM chat_messages
            WHERE team_id = ?
        """,
            (team_id,),
        )
        row = cur.fetchone()

        # Get model usage stats for team
        cur = conn.execute(
            """
            SELECT model, COUNT(*) as count
            FROM chat_messages
            WHERE model IS NOT NULL AND team_id = ?
            GROUP BY model
            ORDER BY count DESC
        """,
            (team_id,),
        )
        model_stats = [{"model": r["model"], "count": r["count"]} for r in cur.fetchall()]

        return {
            "total_sessions": row["total_sessions"],
            "total_messages": row["total_messages"],
            "total_tokens": row["total_tokens"] or 0,
            "model_usage": model_stats,
            "team_id": team_id,
        }

    def get_user_analytics(self, user_id: str) -> dict[str, Any]:
        """
        Get analytics for a user (personal sessions only).

        Args:
            user_id: User to analyze

        Returns:
            Analytics dict with session count, message count, tokens, model usage
        """
        conn = self._db.get_connection()
        cur = conn.execute(
            """
            SELECT
                COUNT(DISTINCT session_id) as total_sessions,
                COUNT(*) as total_messages,
                SUM(tokens) as total_tokens
            FROM chat_messages
            WHERE user_id = ? AND team_id IS NULL
        """,
            (user_id,),
        )
        row = cur.fetchone()

        # Get model usage stats for user
        cur = conn.execute(
            """
            SELECT model, COUNT(*) as count
            FROM chat_messages
            WHERE model IS NOT NULL AND user_id = ? AND team_id IS NULL
            GROUP BY model
            ORDER BY count DESC
        """,
            (user_id,),
        )
        model_stats = [{"model": r["model"], "count": r["count"]} for r in cur.fetchall()]

        return {
            "total_sessions": row["total_sessions"],
            "total_messages": row["total_messages"],
            "total_tokens": row["total_tokens"] or 0,
            "model_usage": model_stats,
            "team_id": None,
        }

    def get_analytics(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Get analytics based on scope.

        Priority: session_id > team_id > user_id

        Args:
            session_id: Optional session to analyze
            user_id: User ID for user-level analytics
            team_id: Team ID for team-level analytics

        Returns:
            Appropriate analytics based on provided scope
        """
        if session_id:
            return self.get_session_analytics(session_id, user_id, team_id)
        elif team_id:
            return self.get_team_analytics(team_id)
        else:
            return self.get_user_analytics(user_id or "default")
