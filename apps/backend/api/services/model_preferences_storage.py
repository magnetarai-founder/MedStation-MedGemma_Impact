"""
Model Preferences Storage Service

Manages per-user model visibility preferences and display order.

Architecture:
- System may have 10 models installed globally
- User A sees 3 models (their choice)
- User B sees 5 models (their choice)
- Each user can reorder their visible models
"""

import logging
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ModelPreference:
    """Model preference data class"""

    def __init__(
        self,
        model_name: str,
        visible: bool = True,
        preferred: bool = False,
        display_order: Optional[int] = None
    ):
        self.model_name = model_name
        self.visible = visible
        self.preferred = preferred
        self.display_order = display_order

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "model_name": self.model_name,
            "visible": self.visible,
            "preferred": self.preferred,
            "display_order": self.display_order
        }


class ModelPreferencesStorage:
    """
    Storage service for per-user model preferences

    Manages:
    - Model visibility (which models user wants to see)
    - Display order (how models are sorted in UI)
    - Preferred flag (for special highlighting)
    """

    def __init__(self, db_path: Path):
        """
        Initialize model preferences storage

        Args:
            db_path: Path to SQLite database (elohim.db)
        """
        self.db_path = db_path

    def get_preferences(self, user_id: str) -> List[ModelPreference]:
        """
        Get all model preferences for a user

        Args:
            user_id: User ID

        Returns:
            List of ModelPreference objects, ordered by display_order
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT model_name, visible, preferred, display_order
                FROM user_model_preferences
                WHERE user_id = ?
                ORDER BY display_order ASC NULLS LAST, model_name ASC
            """, (user_id,))

            rows = cursor.fetchall()
            conn.close()

            preferences = []
            for row in rows:
                preferences.append(ModelPreference(
                    model_name=row[0],
                    visible=bool(row[1]),
                    preferred=bool(row[2]),
                    display_order=row[3]
                ))

            return preferences

        except Exception as e:
            logger.error(f"Failed to get model preferences for user {user_id}: {e}")
            return []

    def get_visible_models(self, user_id: str) -> List[str]:
        """
        Get list of visible model names for a user

        Args:
            user_id: User ID

        Returns:
            List of model names that are marked as visible, ordered by display_order
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT model_name
                FROM user_model_preferences
                WHERE user_id = ? AND visible = 1
                ORDER BY display_order ASC NULLS LAST, model_name ASC
            """, (user_id,))

            rows = cursor.fetchall()
            conn.close()

            return [row[0] for row in rows]

        except Exception as e:
            logger.error(f"Failed to get visible models for user {user_id}: {e}")
            return []

    def set_preference(
        self,
        user_id: str,
        model_name: str,
        visible: Optional[bool] = None,
        preferred: Optional[bool] = None,
        display_order: Optional[int] = None
    ) -> bool:
        """
        Set or update model preference for a user

        Args:
            user_id: User ID
            model_name: Model name
            visible: Optional visibility flag
            preferred: Optional preferred flag
            display_order: Optional display order

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            now = datetime.now(UTC).isoformat()

            # Check if preference exists
            cursor.execute("""
                SELECT id FROM user_model_preferences
                WHERE user_id = ? AND model_name = ?
            """, (user_id, model_name))

            exists = cursor.fetchone() is not None

            if exists:
                # Update existing preference
                updates = []
                params = []

                if visible is not None:
                    updates.append("visible = ?")
                    params.append(1 if visible else 0)

                if preferred is not None:
                    updates.append("preferred = ?")
                    params.append(1 if preferred else 0)

                if display_order is not None:
                    updates.append("display_order = ?")
                    params.append(display_order)

                if updates:
                    updates.append("updated_at = ?")
                    params.append(now)
                    params.extend([user_id, model_name])

                    sql = f"""
                        UPDATE user_model_preferences
                        SET {', '.join(updates)}
                        WHERE user_id = ? AND model_name = ?
                    """

                    cursor.execute(sql, params)
            else:
                # Insert new preference
                cursor.execute("""
                    INSERT INTO user_model_preferences
                    (user_id, model_name, visible, preferred, display_order, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    model_name,
                    1 if visible else 0,
                    1 if preferred else 0,
                    display_order,
                    now,
                    now
                ))

            conn.commit()
            conn.close()

            logger.debug(f"✓ Model preference updated: {user_id} / {model_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to set model preference for {user_id} / {model_name}: {e}")
            return False

    def set_preferences_bulk(self, user_id: str, preferences: List[Dict[str, Any]]) -> bool:
        """
        Set multiple model preferences at once

        Args:
            user_id: User ID
            preferences: List of preference dictionaries with keys:
                        - model_name (required)
                        - visible (optional, default True)
                        - preferred (optional, default False)
                        - display_order (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            now = datetime.now(UTC).isoformat()

            for pref in preferences:
                model_name = pref.get("model_name")
                if not model_name:
                    logger.warning("Skipping preference without model_name")
                    continue

                visible = pref.get("visible", True)
                preferred = pref.get("preferred", False)
                display_order = pref.get("display_order")

                cursor.execute("""
                    INSERT INTO user_model_preferences
                    (user_id, model_name, visible, preferred, display_order, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, model_name) DO UPDATE SET
                        visible = excluded.visible,
                        preferred = excluded.preferred,
                        display_order = excluded.display_order,
                        updated_at = excluded.updated_at
                """, (
                    user_id,
                    model_name,
                    1 if visible else 0,
                    1 if preferred else 0,
                    display_order,
                    now,
                    now
                ))

            conn.commit()
            conn.close()

            logger.info(f"✓ Bulk updated {len(preferences)} model preferences for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to bulk set model preferences for {user_id}: {e}")
            return False

    def initialize_default_preferences(self, user_id: str, installed_models: List[str]) -> bool:
        """
        Initialize default preferences for a new user

        Sets all installed models as visible by default.

        Args:
            user_id: User ID
            installed_models: List of installed model names

        Returns:
            True if successful, False otherwise
        """
        try:
            preferences = []
            for i, model_name in enumerate(installed_models):
                preferences.append({
                    "model_name": model_name,
                    "visible": True,
                    "preferred": False,
                    "display_order": i + 1
                })

            return self.set_preferences_bulk(user_id, preferences)

        except Exception as e:
            logger.error(f"Failed to initialize default preferences for {user_id}: {e}")
            return False

    def clear_preference(self, user_id: str, model_name: str) -> bool:
        """
        Remove a model preference

        Args:
            user_id: User ID
            model_name: Model name

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM user_model_preferences
                WHERE user_id = ? AND model_name = ?
            """, (user_id, model_name))

            conn.commit()
            conn.close()

            logger.debug(f"✓ Cleared model preference: {user_id} / {model_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear model preference for {user_id} / {model_name}: {e}")
            return False


# Singleton instance (initialized by app startup)
_model_prefs_storage: Optional[ModelPreferencesStorage] = None


def init_model_preferences_storage(db_path: Path) -> ModelPreferencesStorage:
    """
    Initialize the global model preferences storage singleton

    Args:
        db_path: Path to SQLite database

    Returns:
        ModelPreferencesStorage instance
    """
    global _model_prefs_storage
    _model_prefs_storage = ModelPreferencesStorage(db_path)
    return _model_prefs_storage


def get_model_preferences_storage() -> ModelPreferencesStorage:
    """
    Get the global model preferences storage instance

    Returns:
        ModelPreferencesStorage instance

    Raises:
        RuntimeError: If storage not initialized
    """
    if _model_prefs_storage is None:
        raise RuntimeError("Model preferences storage not initialized. Call init_model_preferences_storage() first.")
    return _model_prefs_storage
