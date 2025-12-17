"""
Hot Slots Storage Adapter

Provides unified interface for hot slots storage with:
- Primary: Per-user database storage (user_hot_slots table)
- Fallback: Legacy JSON file (config/model_hot_slots.json) - read-only

This adapter ensures backward compatibility while migrating to per-user hot slots.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class HotSlotsStorage:
    """
    Storage adapter for model hot slots

    Supports:
    - Per-user hot slots in database (primary)
    - Legacy JSON file fallback (read-only migration)
    """

    def __init__(self, db_path: Path, config_dir: Path):
        """
        Initialize hot slots storage

        Args:
            db_path: Path to SQLite database (elohim.db)
            config_dir: Path to config directory (for legacy JSON)
        """
        self.db_path = db_path
        self.json_path = config_dir / "model_hot_slots.json"

    def get_hot_slots(self, user_id: str) -> Dict[int, Optional[str]]:
        """
        Get hot slots for a user

        Args:
            user_id: User ID

        Returns:
            Dictionary mapping slot number (1-4) to model name (or None)
            Example: {1: "qwen2.5-coder:7b", 2: "llama3.1:8b", 3: None, 4: None}
        """
        try:
            # Try database first
            slots = self._get_from_db(user_id)

            if slots:
                return slots

            # Fallback to JSON if DB is empty (first-time access)
            if self.json_path.exists():
                logger.info(f"No hot slots in DB for user {user_id}, checking legacy JSON")
                json_slots = self._get_from_json()

                if json_slots:
                    # Migrate JSON slots to DB for this user
                    logger.info(f"Migrating legacy hot slots to DB for user {user_id}")
                    self.set_hot_slots(user_id, json_slots)
                    return json_slots

            # No slots found - return empty structure
            return {1: None, 2: None, 3: None, 4: None}

        except Exception as e:
            logger.error(f"Failed to get hot slots for user {user_id}: {e}")
            return {1: None, 2: None, 3: None, 4: None}

    def set_hot_slots(self, user_id: str, slots: Dict[int, Optional[str]]) -> bool:
        """
        Set hot slots for a user

        Args:
            user_id: User ID
            slots: Dictionary mapping slot number (1-4) to model name (or None)

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            now = datetime.now(UTC).isoformat()

            # Update or insert each slot
            for slot_num, model_name in slots.items():
                if not (1 <= slot_num <= 4):
                    logger.warning(f"Invalid slot number {slot_num}, skipping")
                    continue

                if model_name:
                    # Insert or update slot
                    cursor.execute("""
                        INSERT INTO user_hot_slots (user_id, slot_number, model_name, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(user_id, slot_number) DO UPDATE SET
                            model_name = excluded.model_name,
                            updated_at = excluded.updated_at
                    """, (user_id, slot_num, model_name, now, now))
                else:
                    # Clear slot
                    cursor.execute("""
                        DELETE FROM user_hot_slots
                        WHERE user_id = ? AND slot_number = ?
                    """, (user_id, slot_num))

            conn.commit()
            conn.close()

            logger.info(f"✓ Hot slots updated for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to set hot slots for user {user_id}: {e}")
            return False

    def clear_hot_slot(self, user_id: str, slot_number: int) -> bool:
        """
        Clear a specific hot slot

        Args:
            user_id: User ID
            slot_number: Slot number (1-4)

        Returns:
            True if successful, False otherwise
        """
        try:
            if not (1 <= slot_number <= 4):
                logger.error(f"Invalid slot number: {slot_number}")
                return False

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM user_hot_slots
                WHERE user_id = ? AND slot_number = ?
            """, (user_id, slot_number))

            conn.commit()
            conn.close()

            logger.info(f"✓ Cleared hot slot {slot_number} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear hot slot {slot_number} for user {user_id}: {e}")
            return False

    def _get_from_db(self, user_id: str) -> Dict[int, Optional[str]]:
        """
        Get hot slots from database

        Args:
            user_id: User ID

        Returns:
            Dictionary mapping slot number to model name, or empty dict if none found
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT slot_number, model_name
                FROM user_hot_slots
                WHERE user_id = ?
                ORDER BY slot_number
            """, (user_id,))

            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return {}

            # Build slots dict (1-4), filling empty slots with None
            slots = {1: None, 2: None, 3: None, 4: None}
            for slot_num, model_name in rows:
                slots[slot_num] = model_name

            return slots

        except Exception as e:
            logger.error(f"Failed to get hot slots from DB for user {user_id}: {e}")
            return {}

    def _get_from_json(self) -> Dict[int, Optional[str]]:
        """
        Get hot slots from legacy JSON file (read-only)

        Returns:
            Dictionary mapping slot number to model name, or empty dict if not found
        """
        try:
            if not self.json_path.exists():
                return {}

            with open(self.json_path, 'r') as f:
                data = json.load(f)

            # Convert string keys to integers
            slots = {}
            for key, value in data.items():
                try:
                    slot_num = int(key)
                    if 1 <= slot_num <= 4:
                        slots[slot_num] = value if value else None
                except (ValueError, TypeError):
                    logger.warning(f"Invalid slot key in JSON: {key}")

            # Fill missing slots with None
            result = {1: None, 2: None, 3: None, 4: None}
            result.update(slots)

            return result

        except Exception as e:
            logger.error(f"Failed to read hot slots from JSON: {e}")
            return {}


# Singleton instance (initialized by app startup)
_hot_slots_storage: Optional[HotSlotsStorage] = None


def init_hot_slots_storage(db_path: Path, config_dir: Path) -> HotSlotsStorage:
    """
    Initialize the global hot slots storage singleton

    Args:
        db_path: Path to SQLite database
        config_dir: Path to config directory

    Returns:
        HotSlotsStorage instance
    """
    global _hot_slots_storage
    _hot_slots_storage = HotSlotsStorage(db_path, config_dir)
    return _hot_slots_storage


def get_hot_slots_storage() -> HotSlotsStorage:
    """
    Get the global hot slots storage instance

    Returns:
        HotSlotsStorage instance

    Raises:
        RuntimeError: If storage not initialized
    """
    if _hot_slots_storage is None:
        raise RuntimeError("Hot slots storage not initialized. Call init_hot_slots_storage() first.")
    return _hot_slots_storage
