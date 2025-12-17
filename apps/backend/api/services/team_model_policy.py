"""
Team Model Policy Service

Manages team-level model access control.
Sprint 5 Theme A: Team-Level Model Policies
"""

import json
import logging
import sqlite3
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class TeamModelPolicyService:
    """Service for managing team model policies"""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        return sqlite3.connect(str(self.db_path))

    def get_policy(self, team_id: str) -> Optional[Dict[str, Any]]:
        """
        Get model policy for a team

        Args:
            team_id: Team ID

        Returns:
            Policy dict or None if no policy set
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT team_id, allowed_models, default_model, updated_at
                FROM team_model_policies
                WHERE team_id = ?
            """, (team_id,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            return {
                "team_id": row[0],
                "allowed_models": json.loads(row[1]) if row[1] else [],
                "default_model": row[2],
                "updated_at": row[3]
            }

        except Exception as e:
            logger.error(f"Failed to get team model policy: {e}", exc_info=True)
            return None

    def set_policy(
        self,
        team_id: str,
        allowed_models: List[str],
        default_model: Optional[str] = None
    ) -> bool:
        """
        Set model policy for a team

        Args:
            team_id: Team ID
            allowed_models: List of allowed model names
            default_model: Optional default model (must be in allowed_models)

        Returns:
            True if successful

        Raises:
            ValueError: If default_model not in allowed_models
        """
        if default_model and default_model not in allowed_models:
            raise ValueError(f"Default model '{default_model}' must be in allowed_models")

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            now = datetime.now(UTC).isoformat()
            allowed_models_json = json.dumps(allowed_models)

            cursor.execute("""
                INSERT INTO team_model_policies (team_id, allowed_models, default_model, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(team_id) DO UPDATE SET
                    allowed_models = excluded.allowed_models,
                    default_model = excluded.default_model,
                    updated_at = excluded.updated_at
            """, (team_id, allowed_models_json, default_model, now))

            conn.commit()
            conn.close()

            logger.info(f"Team model policy updated for team {team_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to set team model policy: {e}", exc_info=True)
            return False

    def is_model_allowed(self, team_id: str, model_name: str) -> bool:
        """
        Check if a model is allowed for a team

        Args:
            team_id: Team ID
            model_name: Model name to check

        Returns:
            True if allowed (or no policy set), False otherwise
        """
        policy = self.get_policy(team_id)

        # If no policy set, allow all models
        if not policy:
            return True

        # Check if model is in allowed list
        return model_name in policy.get("allowed_models", [])

    def delete_policy(self, team_id: str) -> bool:
        """
        Delete model policy for a team

        Args:
            team_id: Team ID

        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM team_model_policies WHERE team_id = ?", (team_id,))

            conn.commit()
            conn.close()

            logger.info(f"Team model policy deleted for team {team_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete team model policy: {e}", exc_info=True)
            return False


# Global service instance
_policy_service: Optional[TeamModelPolicyService] = None


def get_policy_service() -> TeamModelPolicyService:
    """
    Get or create global policy service instance

    Returns:
        TeamModelPolicyService instance
    """
    global _policy_service

    if _policy_service is None:
        from config_paths import get_data_dir
        data_dir = get_data_dir()
        db_path = data_dir / "elohim.db"
        _policy_service = TeamModelPolicyService(db_path)

    return _policy_service
