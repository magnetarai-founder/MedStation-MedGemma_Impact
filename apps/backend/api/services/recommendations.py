"""
Model Recommendations Service - Sprint 6 Theme C (Ticket C3)

Provides intelligent model recommendations based on:
- Performance metrics (latency, satisfaction, efficiency)
- Team policies (allowed_models)
- Task type (code, chat, analysis)
- Installation status
"""

import sqlite3
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, timedelta

DB_PATH = "data/elohimos.db"

TaskType = Literal["code", "chat", "analysis", "general"]


class RecommendationsService:
    """Service for model recommendations"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

        # Task-specific weights for scoring
        # Format: {task: (w_latency, w_satisfaction, w_efficiency)}
        self.task_weights = {
            "code": (0.3, 0.5, 0.2),      # Prioritize quality (satisfaction) and speed
            "chat": (0.4, 0.4, 0.2),      # Balance speed and quality
            "analysis": (0.2, 0.5, 0.3),  # Prioritize quality and efficiency
            "general": (0.3, 0.4, 0.3)    # Balanced
        }

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_recommendations(
        self,
        task: TaskType = "general",
        team_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 3,
        days_lookback: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get model recommendations based on performance and task type

        Args:
            task: Type of task (code, chat, analysis, general)
            team_id: Team ID for policy filtering
            user_id: User ID for personalized recommendations
            limit: Maximum number of recommendations
            days_lookback: Days of historical data to consider

        Returns:
            List of recommended models with scores and reasons
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            # Get team policy (allowed_models)
            allowed_models = self._get_allowed_models(cursor, team_id)

            # Get model performance metrics from analytics_daily
            start_date = (datetime.utcnow() - timedelta(days=days_lookback)).strftime('%Y-%m-%d')

            where_parts = ["date >= ?", "model_name IS NOT NULL"]
            params = [start_date]

            if team_id:
                where_parts.append("team_id = ?")
                params.append(team_id)
            if user_id:
                where_parts.append("user_id = ?")
                params.append(user_id)

            where_clause = " AND ".join(where_parts)

            cursor.execute(f"""
                SELECT
                    model_name,
                    AVG(response_time_avg) as avg_latency,
                    AVG(response_time_p95) as p95_latency,
                    AVG(satisfaction_score) as avg_satisfaction,
                    AVG(CAST(tokens_total AS REAL) / NULLIF(message_count, 0)) as tokens_per_message,
                    SUM(message_count) as total_messages,
                    COUNT(DISTINCT date) as days_used
                FROM analytics_daily
                WHERE {where_clause}
                  AND message_count > 0
                GROUP BY model_name
                HAVING total_messages >= 5  -- Minimum sample size
                ORDER BY total_messages DESC
            """, params)

            models = cursor.fetchall()

            if not models:
                # No performance data available, return empty
                return []

            # Calculate scores based on task weights
            w_latency, w_satisfaction, w_efficiency = self.task_weights[task]

            scored_models = []
            for model in models:
                model_name = model["model_name"]

                # Check if model is allowed by policy
                if allowed_models and model_name not in allowed_models:
                    continue

                # Normalize metrics (0-1 scale, higher is better)
                latency_score = self._normalize_latency(model["avg_latency"], models)
                satisfaction_score = self._normalize_satisfaction(model["avg_satisfaction"])
                efficiency_score = self._normalize_efficiency(model["tokens_per_message"], models)

                # Weighted score
                final_score = (
                    w_latency * latency_score +
                    w_satisfaction * satisfaction_score +
                    w_efficiency * efficiency_score
                )

                # Generate reason
                reason = self._generate_reason(
                    model,
                    latency_score,
                    satisfaction_score,
                    efficiency_score,
                    task
                )

                scored_models.append({
                    "model_name": model_name,
                    "score": round(final_score, 3),
                    "reason": reason,
                    "metrics": {
                        "avg_latency_ms": round(model["avg_latency"]) if model["avg_latency"] else None,
                        "p95_latency_ms": round(model["p95_latency"]) if model["p95_latency"] else None,
                        "satisfaction": round(model["avg_satisfaction"], 2) if model["avg_satisfaction"] else None,
                        "tokens_per_message": round(model["tokens_per_message"]) if model["tokens_per_message"] else None,
                        "total_messages": model["total_messages"]
                    }
                })

            # Sort by score and return top N
            scored_models.sort(key=lambda x: x["score"], reverse=True)
            return scored_models[:limit]

        finally:
            conn.close()

    def _get_allowed_models(self, cursor, team_id: Optional[str]) -> Optional[List[str]]:
        """Get allowed models from team policy"""
        if not team_id:
            return None

        # Check if team_policies table exists and has allowed_models
        try:
            cursor.execute("""
                SELECT allowed_models FROM team_policies
                WHERE team_id = ?
            """, (team_id,))
            row = cursor.fetchone()

            if row and row["allowed_models"]:
                import json
                return json.loads(row["allowed_models"])
        except Exception:
            # Table might not exist yet
            pass

        return None

    def _normalize_latency(self, latency: Optional[float], all_models) -> float:
        """Normalize latency (lower is better, inverted to 0-1 scale)"""
        if latency is None:
            return 0.5  # Neutral score if no data

        latencies = [m["avg_latency"] for m in all_models if m["avg_latency"] is not None]
        if not latencies:
            return 0.5

        min_latency = min(latencies)
        max_latency = max(latencies)

        if max_latency == min_latency:
            return 0.75  # All same, slightly positive

        # Invert: lower latency = higher score
        normalized = 1.0 - ((latency - min_latency) / (max_latency - min_latency))
        return max(0.0, min(1.0, normalized))

    def _normalize_satisfaction(self, satisfaction: Optional[float]) -> float:
        """Normalize satisfaction score (-1 to +1 → 0 to 1 scale)"""
        if satisfaction is None:
            return 0.5  # Neutral if no feedback

        # Map [-1, 1] to [0, 1]
        return (satisfaction + 1.0) / 2.0

    def _normalize_efficiency(self, tokens_per_msg: Optional[float], all_models) -> float:
        """Normalize tokens per message (lower is more efficient)"""
        if tokens_per_msg is None:
            return 0.5

        efficiencies = [m["tokens_per_message"] for m in all_models if m["tokens_per_message"] is not None]
        if not efficiencies:
            return 0.5

        min_tokens = min(efficiencies)
        max_tokens = max(efficiencies)

        if max_tokens == min_tokens:
            return 0.75

        # Invert: fewer tokens = higher efficiency score
        normalized = 1.0 - ((tokens_per_msg - min_tokens) / (max_tokens - min_tokens))
        return max(0.0, min(1.0, normalized))

    def _generate_reason(
        self,
        model,
        latency_score: float,
        satisfaction_score: float,
        efficiency_score: float,
        task: TaskType
    ) -> str:
        """Generate human-readable reason for recommendation"""
        reasons = []

        # Highlight best attribute
        if latency_score > 0.75:
            reasons.append("fast response times")
        if satisfaction_score > 0.75:
            reasons.append("high user satisfaction")
        if efficiency_score > 0.75:
            reasons.append("efficient token usage")

        # Task-specific context
        task_context = {
            "code": "coding tasks",
            "chat": "conversations",
            "analysis": "analytical work",
            "general": "general use"
        }

        if reasons:
            return f"Best for {task_context[task]} — {', '.join(reasons)}"
        else:
            return f"Balanced performance for {task_context[task]}"


# Singleton instance
_recommendations_service = None


def get_recommendations_service() -> RecommendationsService:
    """Get singleton recommendations service instance"""
    global _recommendations_service
    if _recommendations_service is None:
        _recommendations_service = RecommendationsService()
    return _recommendations_service
