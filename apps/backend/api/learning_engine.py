#!/usr/bin/env python3
"""
Adaptive Learning Engine for ElohimOS
Tracks model usage patterns and provides intelligent recommendations

Copyright (c) 2025 MagnetarAI, LLC
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

# Database path for learning data
from api.config_paths import get_config_paths
PATHS = get_config_paths()
LEARNING_DB = PATHS.data_dir / "learning.db"


class LearningEngine:
    """
    Adaptive learning engine that tracks model usage and provides recommendations

    Tracks:
    - Which models are used for which task types (code, writing, reasoning, etc.)
    - Success metrics (message count, session duration)
    - User preferences and patterns

    Provides:
    - Model classification recommendations based on actual usage
    - Optimal model suggestions for specific tasks
    - Usage analytics and insights
    """

    def __init__(self):
        self.conn = sqlite3.connect(str(LEARNING_DB), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_database()

    def _init_database(self) -> None:
        """Initialize learning database tables"""
        cursor = self.conn.cursor()

        # Model usage tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                classification TEXT,
                session_id TEXT,
                message_count INTEGER DEFAULT 1,
                tokens_used INTEGER DEFAULT 0,
                session_duration_seconds INTEGER DEFAULT 0,
                task_detected TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Model classification recommendations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classification_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                current_classification TEXT,
                recommended_classification TEXT NOT NULL,
                confidence REAL NOT NULL,
                reason TEXT,
                usage_count INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accepted BOOLEAN DEFAULT NULL,
                accepted_at TIMESTAMP DEFAULT NULL
            )
        """)

        # User feedback on recommendations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendation_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recommendation_id INTEGER NOT NULL,
                accepted BOOLEAN NOT NULL,
                feedback_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recommendation_id) REFERENCES classification_recommendations (id)
            )
        """)

        self.conn.commit()
        logger.info("Learning engine database initialized")

    def track_usage(
        self,
        model_name: str,
        classification: Optional[str] = None,
        session_id: Optional[str] = None,
        message_count: int = 1,
        tokens_used: int = 0,
        session_duration_seconds: int = 0,
        task_detected: Optional[str] = None
    ) -> None:
        """
        Track model usage for learning

        Args:
            model_name: Name of the model used
            classification: Classification assigned to this usage (chat/code/writing/etc.)
            session_id: Chat session ID
            message_count: Number of messages in session
            tokens_used: Total tokens used
            session_duration_seconds: How long the session lasted
            task_detected: Auto-detected task type (from prompt analysis)
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO model_usage (
                    model_name, classification, session_id, message_count,
                    tokens_used, session_duration_seconds, task_detected
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                model_name, classification, session_id, message_count,
                tokens_used, session_duration_seconds, task_detected
            ))
            self.conn.commit()
            logger.debug(f"Tracked usage: {model_name} for {classification or 'unknown'}")
        except Exception as e:
            logger.error(f"Failed to track usage: {e}")

    def analyze_patterns(self, days: int = 30) -> Dict[str, any]:
        """
        Analyze usage patterns over the past N days

        Returns:
            Dict with pattern insights:
            - model_usage: Usage by model and classification
            - mismatches: Potential classification mismatches
            - recommendations: Suggested re-classifications
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            cursor = self.conn.cursor()

            # Get usage patterns
            cursor.execute("""
                SELECT
                    model_name,
                    classification,
                    task_detected,
                    COUNT(*) as usage_count,
                    SUM(message_count) as total_messages,
                    SUM(tokens_used) as total_tokens
                FROM model_usage
                WHERE created_at >= ?
                GROUP BY model_name, classification, task_detected
                ORDER BY usage_count DESC
            """, (cutoff_date,))

            usage_data = cursor.fetchall()

            # Organize by model
            model_patterns = defaultdict(lambda: defaultdict(int))
            for row in usage_data:
                model_name = row['model_name']
                classification = row['classification'] or 'unknown'
                usage_count = row['usage_count']
                model_patterns[model_name][classification] += usage_count

            # Detect mismatches
            recommendations = []
            for model_name, class_counts in model_patterns.items():
                total_uses = sum(class_counts.values())

                # Find dominant classification
                if total_uses >= 5:  # Minimum usage threshold
                    dominant_class = max(class_counts.items(), key=lambda x: x[1])
                    dominant_classification = dominant_class[0]
                    dominant_count = dominant_class[1]
                    confidence = dominant_count / total_uses

                    # Recommend if confidence > 70% and it's not "intelligent" or "unknown"
                    if confidence > 0.7 and dominant_classification not in ['intelligent', 'unknown']:
                        recommendations.append({
                            'model_name': model_name,
                            'recommended_classification': dominant_classification,
                            'confidence': confidence,
                            'usage_count': total_uses,
                            'reason': f"Used {dominant_count}/{total_uses} times ({confidence*100:.0f}%) for {dominant_classification} tasks"
                        })

            return {
                'model_usage': dict(model_patterns),
                'recommendations': recommendations,
                'total_tracked_sessions': len(usage_data)
            }

        except Exception as e:
            logger.error(f"Failed to analyze patterns: {e}")
            return {'model_usage': {}, 'recommendations': [], 'total_tracked_sessions': 0}

    def get_recommendations(self) -> List[Dict]:
        """
        Get current classification recommendations

        Returns:
            List of pending recommendations
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT
                    id, model_name, current_classification,
                    recommended_classification, confidence, reason,
                    usage_count, created_at
                FROM classification_recommendations
                WHERE accepted IS NULL
                ORDER BY confidence DESC, usage_count DESC
                LIMIT 10
            """)

            recommendations = []
            for row in cursor.fetchall():
                recommendations.append({
                    'id': row['id'],
                    'model_name': row['model_name'],
                    'current_classification': row['current_classification'],
                    'recommended_classification': row['recommended_classification'],
                    'confidence': row['confidence'],
                    'reason': row['reason'],
                    'usage_count': row['usage_count'],
                    'created_at': row['created_at']
                })

            return recommendations

        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
            return []

    def save_recommendation(
        self,
        model_name: str,
        current_classification: Optional[str],
        recommended_classification: str,
        confidence: float,
        reason: str,
        usage_count: int
    ) -> int:
        """Save a new classification recommendation"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO classification_recommendations (
                    model_name, current_classification, recommended_classification,
                    confidence, reason, usage_count
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                model_name, current_classification, recommended_classification,
                confidence, reason, usage_count
            ))
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to save recommendation: {e}")
            return 0

    def accept_recommendation(self, recommendation_id: int, feedback: Optional[str] = None) -> bool:
        """Mark a recommendation as accepted"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE classification_recommendations
                SET accepted = TRUE, accepted_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (recommendation_id,))

            if feedback:
                cursor.execute("""
                    INSERT INTO recommendation_feedback (
                        recommendation_id, accepted, feedback_text
                    ) VALUES (?, TRUE, ?)
                """, (recommendation_id, feedback))

            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to accept recommendation: {e}")
            return False

    def reject_recommendation(self, recommendation_id: int, feedback: Optional[str] = None) -> bool:
        """Mark a recommendation as rejected"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE classification_recommendations
                SET accepted = FALSE, accepted_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (recommendation_id,))

            if feedback:
                cursor.execute("""
                    INSERT INTO recommendation_feedback (
                        recommendation_id, accepted, feedback_text
                    ) VALUES (?, FALSE, ?)
                """, (recommendation_id, feedback))

            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to reject recommendation: {e}")
            return False

    def get_optimal_model_for_task(self, task_type: str, top_n: int = 3) -> List[Tuple[str, float]]:
        """
        Get the most commonly used models for a specific task type

        Args:
            task_type: The task classification (code, writing, reasoning, etc.)
            top_n: Number of top models to return

        Returns:
            List of (model_name, confidence_score) tuples
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT
                    model_name,
                    COUNT(*) as usage_count,
                    SUM(message_count) as total_messages
                FROM model_usage
                WHERE classification = ? OR task_detected = ?
                GROUP BY model_name
                ORDER BY usage_count DESC, total_messages DESC
                LIMIT ?
            """, (task_type, task_type, top_n))

            results = cursor.fetchall()

            if not results:
                return []

            # Calculate confidence scores
            total_uses = sum(row['usage_count'] for row in results)
            model_recommendations = [
                (row['model_name'], row['usage_count'] / total_uses)
                for row in results
            ]

            return model_recommendations

        except Exception as e:
            logger.error(f"Failed to get optimal model for task '{task_type}': {e}")
            return []

    def close(self) -> None:
        """Close database connection"""
        if self.conn:
            self.conn.close()


# Global instance
_learning_engine = LearningEngine()


def get_learning_engine() -> LearningEngine:
    """Get the global learning engine instance"""
    return _learning_engine
