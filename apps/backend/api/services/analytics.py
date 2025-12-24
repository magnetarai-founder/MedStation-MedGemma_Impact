"""
Analytics Service - Sprint 6 Theme A

Handles event recording, aggregation, and querying for usage analytics.
"""

import logging
import sqlite3
import json
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any, List
from uuid import uuid4

logger = logging.getLogger(__name__)

try:
    from config_paths import PATHS
except ImportError:
    from ..config_paths import PATHS

DB_PATH = str(PATHS.app_db)

class AnalyticsService:
    """Service for recording and querying analytics data"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def record_event(
        self,
        user_id: str,
        event_type: str,
        session_id: Optional[str] = None,
        team_id: Optional[str] = None,
        model_name: Optional[str] = None,
        tokens_used: Optional[int] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record an analytics event

        Args:
            user_id: User performing the action
            event_type: Type of event (e.g., 'message.sent', 'session.created')
            session_id: Associated session ID
            team_id: Associated team ID
            model_name: Model used (if applicable)
            tokens_used: Token count (if applicable)
            duration_ms: Duration in milliseconds
            metadata: Additional event data as JSON

        Returns:
            Event ID
        """
        event_id = str(uuid4())
        ts = datetime.now(UTC).isoformat()

        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO analytics_events (
                    id, ts, user_id, team_id, session_id,
                    event_type, model_name, tokens_used, duration_ms, metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, ts, user_id, team_id, session_id,
                event_type, model_name, tokens_used, duration_ms,
                json.dumps(metadata) if metadata else None
            ))

            conn.commit()
            return event_id

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to record analytics event: {e}")
            raise
        finally:
            conn.close()

    def record_error(
        self,
        user_id: str,
        error_code: str,
        session_id: Optional[str] = None,
        team_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record an error event

        Args:
            user_id: User experiencing the error
            error_code: Error code/type
            session_id: Associated session ID
            team_id: Associated team ID
            metadata: Additional error context

        Returns:
            Event ID
        """
        event_id = str(uuid4())
        ts = datetime.now(UTC).isoformat()

        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO analytics_events (
                    id, ts, user_id, team_id, session_id,
                    event_type, error_code, metadata
                )
                VALUES (?, ?, ?, ?, ?, 'error', ?, ?)
            """, (
                event_id, ts, user_id, team_id, session_id,
                error_code, json.dumps(metadata) if metadata else None
            ))

            conn.commit()
            return event_id

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to record error event: {e}")
            raise
        finally:
            conn.close()

    def aggregate_hour(self, start_time: datetime) -> None:
        """
        Aggregate analytics for a specific hour (idempotent)

        This is called by the background job to pre-aggregate data
        """
        # Not implemented yet - will be added in Ticket A2
        pass

    def aggregate_daily(self, date: str) -> None:
        """
        Aggregate analytics for a specific day (YYYY-MM-DD format)

        Rolls up events into analytics_daily table by:
        - date, team_id, user_id, model_name

        Sprint 6 Theme C: Now includes model performance KPIs:
        - response_time_avg, response_time_p95: Latency metrics
        - satisfaction_score: Average feedback (-1 to +1)
        - message_count: Total assistant messages

        Args:
            date: Date to aggregate in YYYY-MM-DD format
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            # Delete existing aggregates for this date (idempotent)
            cursor.execute("DELETE FROM analytics_daily WHERE date = ?", (date,))

            # Aggregate by user, team, model
            # Use a CTE to avoid correlated subquery issues with GROUP BY
            cursor.execute("""
                WITH daily_groups AS (
                    SELECT
                        DATE(ts) as date,
                        team_id,
                        user_id,
                        model_name,
                        COUNT(DISTINCT session_id) as sessions_count,
                        COALESCE(SUM(tokens_used), 0) as tokens_total,
                        COUNT(*) as api_calls,
                        SUM(CASE WHEN event_type = 'error' THEN 1 ELSE 0 END) as errors
                    FROM analytics_events
                    WHERE DATE(ts) = ?
                    GROUP BY DATE(ts), team_id, user_id, model_name
                ),
                latency_stats AS (
                    SELECT
                        DATE(ts) as date,
                        team_id,
                        user_id,
                        model_name,
                        AVG(duration_ms) as avg_latency,
                        COUNT(*) as msg_count
                    FROM analytics_events
                    WHERE event_type = 'assistant_latency' AND DATE(ts) = ?
                    GROUP BY DATE(ts), team_id, user_id, model_name
                ),
                feedback_stats AS (
                    SELECT
                        DATE(ts) as date,
                        team_id,
                        user_id,
                        AVG(CAST(json_extract(metadata, '$.score') AS REAL)) as avg_score
                    FROM analytics_events
                    WHERE event_type = 'message_feedback' AND DATE(ts) = ?
                    GROUP BY DATE(ts), team_id, user_id
                )
                INSERT INTO analytics_daily (
                    date, team_id, user_id, model_name,
                    sessions_count, tokens_total, api_calls, errors,
                    response_time_avg, response_time_p95, satisfaction_score, message_count
                )
                SELECT
                    dg.date,
                    dg.team_id,
                    dg.user_id,
                    dg.model_name,
                    dg.sessions_count,
                    dg.tokens_total,
                    dg.api_calls,
                    dg.errors,
                    ls.avg_latency as response_time_avg,
                    NULL as response_time_p95,  -- P95 calculation requires more complex query
                    fs.avg_score as satisfaction_score,
                    ls.msg_count as message_count
                FROM daily_groups dg
                LEFT JOIN latency_stats ls ON
                    dg.date = ls.date AND
                    dg.model_name = ls.model_name AND
                    (dg.team_id = ls.team_id OR (dg.team_id IS NULL AND ls.team_id IS NULL)) AND
                    (dg.user_id = ls.user_id OR (dg.user_id IS NULL AND ls.user_id IS NULL))
                LEFT JOIN feedback_stats fs ON
                    dg.date = fs.date AND
                    (dg.team_id = fs.team_id OR (dg.team_id IS NULL AND fs.team_id IS NULL)) AND
                    (dg.user_id = fs.user_id OR (dg.user_id IS NULL AND fs.user_id IS NULL))
            """, (date, date, date))

            conn.commit()
            logger.info(f"Aggregated analytics for {date} (with model KPIs)")

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to aggregate daily analytics: {e}")
            raise
        finally:
            conn.close()

    def get_usage_summary(
        self,
        days: int = 7,
        team_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get usage summary for dashboard

        Args:
            days: Number of days to look back
            team_id: Filter by team
            user_id: Filter by user

        Returns:
            Dictionary with model_usage, tokens_trend, sessions_trend, errors_trend, top_users, top_teams
        """
        start_date = (datetime.now(UTC) - timedelta(days=days)).strftime('%Y-%m-%d')
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            # Build WHERE clause for filters
            where_parts = ["date >= ?"]
            params = [start_date]

            if team_id:
                where_parts.append("team_id = ?")
                params.append(team_id)
            if user_id:
                where_parts.append("user_id = ?")
                params.append(user_id)

            where_clause = " AND ".join(where_parts)

            # Model usage distribution (top 5 models)
            cursor.execute(f"""
                SELECT model_name, SUM(tokens_total) as total_tokens, SUM(api_calls) as calls
                FROM analytics_daily
                WHERE {where_clause} AND model_name IS NOT NULL
                GROUP BY model_name
                ORDER BY total_tokens DESC
                LIMIT 5
            """, params)
            model_usage = [dict(row) for row in cursor.fetchall()]

            # Daily tokens trend
            cursor.execute(f"""
                SELECT date, SUM(tokens_total) as tokens
                FROM analytics_daily
                WHERE {where_clause}
                GROUP BY date
                ORDER BY date ASC
            """, params)
            tokens_trend = [dict(row) for row in cursor.fetchall()]

            # Daily sessions trend
            cursor.execute(f"""
                SELECT date, SUM(sessions_count) as sessions
                FROM analytics_daily
                WHERE {where_clause}
                GROUP BY date
                ORDER BY date ASC
            """, params)
            sessions_trend = [dict(row) for row in cursor.fetchall()]

            # Daily errors trend
            cursor.execute(f"""
                SELECT date, SUM(errors) as errors
                FROM analytics_daily
                WHERE {where_clause}
                GROUP BY date
                ORDER BY date ASC
            """, params)
            errors_trend = [dict(row) for row in cursor.fetchall()]

            # Top users (only if not filtered by user)
            top_users = []
            if not user_id:
                cursor.execute(f"""
                    SELECT user_id, SUM(api_calls) as calls, SUM(tokens_total) as tokens
                    FROM analytics_daily
                    WHERE {where_clause} AND user_id IS NOT NULL
                    GROUP BY user_id
                    ORDER BY calls DESC
                    LIMIT 10
                """, params)
                top_users = [dict(row) for row in cursor.fetchall()]

            # Top teams (only if not filtered by team)
            top_teams = []
            if not team_id:
                cursor.execute(f"""
                    SELECT team_id, SUM(api_calls) as calls, SUM(tokens_total) as tokens
                    FROM analytics_daily
                    WHERE {where_clause} AND team_id IS NOT NULL
                    GROUP BY team_id
                    ORDER BY calls DESC
                    LIMIT 10
                """, params)
                top_teams = [dict(row) for row in cursor.fetchall()]

            return {
                "model_usage": model_usage,
                "tokens_trend": tokens_trend,
                "sessions_trend": sessions_trend,
                "errors_trend": errors_trend,
                "top_users": top_users,
                "top_teams": top_teams
            }

        finally:
            conn.close()

    def export_data(
        self,
        format: str,
        days: int = 30,
        team_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export analytics data in specified format

        Args:
            format: 'csv' or 'json'
            days: Number of days to export
            team_id: Filter by team
            user_id: Filter by user

        Returns:
            Dictionary with data and filename
        """
        summary = self.get_usage_summary(days, team_id, user_id)

        if format == 'json':
            return {
                "data": json.dumps(summary, indent=2),
                "filename": f"analytics-{datetime.now(UTC).strftime('%Y%m%d')}.json",
                "content_type": "application/json"
            }
        elif format == 'csv':
            # Simple CSV export of daily aggregates
            start_date = (datetime.now(UTC) - timedelta(days=days)).strftime('%Y-%m-%d')
            conn = self._get_conn()
            cursor = conn.cursor()

            try:
                where_parts = ["date >= ?"]
                params = [start_date]

                if team_id:
                    where_parts.append("team_id = ?")
                    params.append(team_id)
                if user_id:
                    where_parts.append("user_id = ?")
                    params.append(user_id)

                where_clause = " AND ".join(where_parts)

                cursor.execute(f"""
                    SELECT date, team_id, user_id, model_name,
                           sessions_count, tokens_total, api_calls, errors
                    FROM analytics_daily
                    WHERE {where_clause}
                    ORDER BY date DESC
                """, params)

                rows = cursor.fetchall()
                csv_lines = ["date,team_id,user_id,model_name,sessions_count,tokens_total,api_calls,errors"]

                for row in rows:
                    csv_lines.append(",".join([
                        str(row['date'] or ''),
                        str(row['team_id'] or ''),
                        str(row['user_id'] or ''),
                        str(row['model_name'] or ''),
                        str(row['sessions_count']),
                        str(row['tokens_total']),
                        str(row['api_calls']),
                        str(row['errors'])
                    ]))

                return {
                    "data": "\n".join(csv_lines),
                    "filename": f"analytics-{datetime.now(UTC).strftime('%Y%m%d')}.csv",
                    "content_type": "text/csv"
                }

            finally:
                conn.close()
        else:
            raise ValueError(f"Unsupported format: {format}")

    def get_events_by_type(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        team_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query events by type with optional user/team filtering

        Args:
            event_type: Type of event to query
            user_id: Filter by user ID
            team_id: Filter by team ID
            limit: Maximum number of events to return

        Returns:
            List of event dictionaries
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            where_clauses = ["event_type = ?"]
            params = [event_type]

            if user_id:
                where_clauses.append("user_id = ?")
                params.append(user_id)

            if team_id:
                where_clauses.append("team_id = ?")
                params.append(team_id)

            where_clause = " AND ".join(where_clauses)

            cursor.execute(f"""
                SELECT id, ts, user_id, team_id, session_id, event_type,
                       model_name, tokens_used, duration_ms, metadata
                FROM analytics_events
                WHERE {where_clause}
                ORDER BY ts DESC
                LIMIT ?
            """, params + [limit])

            rows = cursor.fetchall()

            events = []
            for row in rows:
                event = {
                    "id": row["id"],
                    "ts": row["ts"],
                    "user_id": row["user_id"],
                    "team_id": row["team_id"],
                    "session_id": row["session_id"],
                    "event_type": row["event_type"],
                    "model_name": row["model_name"],
                    "tokens_used": row["tokens_used"],
                    "duration_ms": row["duration_ms"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None
                }
                events.append(event)

            return events

        finally:
            conn.close()


# Singleton instance
_analytics_service = None

def get_analytics_service() -> AnalyticsService:
    """Get singleton analytics service instance"""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service
