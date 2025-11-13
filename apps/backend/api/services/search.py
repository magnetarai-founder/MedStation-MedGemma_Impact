"""
Search Service - Sprint 6 Theme B

Full-text search over session messages with filtering and highlighting.
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = "data/elohimos.db"

class SearchService:
    """Service for searching session messages"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def search_sessions(
        self,
        query: str,
        user_id: str,
        user_role: str,
        team_id: Optional[str] = None,
        model: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        min_tokens: Optional[int] = None,
        max_tokens: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search sessions with filters

        Args:
            query: Search query text
            user_id: Current user ID
            user_role: Current user role (founder/admin can search team-wide)
            team_id: Filter by team
            model: Filter by model name
            from_date: Filter messages after this date (ISO format)
            to_date: Filter messages before this date (ISO format)
            min_tokens: Minimum token count
            max_tokens: Maximum token count
            limit: Max results to return

        Returns:
            List of matching sessions with highlights
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            # Build WHERE clauses
            where_clauses = []
            params = []

            # Security: Non-admin users can only search their own sessions
            if user_role not in ['founder', 'admin']:
                where_clauses.append("fts.user_id = ?")
                params.append(user_id)
            elif team_id:
                # Admin filtering by team
                where_clauses.append("cm.team_id = ?")
                params.append(team_id)

            # Date filters
            if from_date:
                where_clauses.append("fts.ts >= ?")
                params.append(from_date)
            if to_date:
                where_clauses.append("fts.ts <= ?")
                params.append(to_date)

            # Build WHERE clause
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            # FTS5 search with snippet highlighting
            # We'll get matching messages, then group by session
            search_sql = f"""
                SELECT
                    fts.session_id,
                    fts.content,
                    fts.ts,
                    fts.role,
                    snippet(messages_fts, 0, '<mark>', '</mark>', '...', 64) as snippet,
                    rank as score
                FROM messages_fts fts
                WHERE messages_fts MATCH ? AND {where_sql}
                ORDER BY rank
                LIMIT ?
            """

            params_search = [query] + params + [limit * 3]  # Get more results for grouping
            cursor.execute(search_sql, params_search)
            raw_results = cursor.fetchall()

            # Group by session and get session details
            sessions_dict = {}
            for row in raw_results:
                session_id = row['session_id']

                if session_id not in sessions_dict:
                    # Get session details
                    cursor.execute("""
                        SELECT title, model, user_id, team_id, created_at
                        FROM chat_memory
                        WHERE session_id = ?
                    """, (session_id,))

                    session_row = cursor.fetchone()
                    if not session_row:
                        continue

                    # Apply additional filters
                    session_model = session_row['model']

                    # Model filter
                    if model and session_model != model:
                        continue

                    # Token filters (we'd need to get token count from session or analytics)
                    # Skip for now - can add later with analytics integration

                    sessions_dict[session_id] = {
                        "session_id": session_id,
                        "title": session_row['title'] or 'Untitled Session',
                        "model_name": session_model,
                        "user_id": session_row['user_id'],
                        "team_id": session_row['team_id'],
                        "created_at": session_row['created_at'],
                        "snippet": row['snippet'],
                        "ts": row['ts'],
                        "score": row['score'],
                        "match_count": 1
                    }
                else:
                    # Increment match count for this session
                    sessions_dict[session_id]["match_count"] += 1
                    # Use the highest-ranked snippet
                    if row['score'] > sessions_dict[session_id]["score"]:
                        sessions_dict[session_id]["snippet"] = row['snippet']
                        sessions_dict[session_id]["score"] = row['score']

            # Convert to list and sort by score
            results = list(sessions_dict.values())
            results.sort(key=lambda x: x['score'], reverse=True)

            # Limit final results
            return results[:limit]

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            raise
        finally:
            conn.close()


# Singleton instance
_search_service = None

def get_search_service() -> SearchService:
    """Get singleton search service instance"""
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service
