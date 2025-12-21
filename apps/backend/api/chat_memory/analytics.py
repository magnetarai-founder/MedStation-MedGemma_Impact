"""
Chat Memory Analytics

Usage analytics and statistics.
"""

import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class AnalyticsMixin:
    """Mixin providing analytics operations"""

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


__all__ = ["AnalyticsMixin"]
