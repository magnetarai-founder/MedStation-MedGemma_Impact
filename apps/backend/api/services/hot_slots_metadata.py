"""
Hot Slots Metadata Storage - Enhanced with Pinning & Timestamps

Adds pinned status, loaded_at, and last_used tracking to hot slots.
Enables LRU eviction that respects pinned models.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime, UTC
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HotSlotMetadata:
    """Metadata for a single hot slot"""
    slot_number: int
    model_name: Optional[str]
    is_pinned: bool
    loaded_at: Optional[datetime]
    last_used: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class HotSlotsMetadataStorage:
    """
    Enhanced hot slots storage with pinning and timestamps

    Schema:
        user_hot_slots_v2 (
            user_id TEXT,
            slot_number INTEGER,
            model_name TEXT,
            is_pinned INTEGER DEFAULT 0,
            loaded_at TEXT,
            last_used TEXT,
            created_at TEXT,
            updated_at TEXT,
            PRIMARY KEY (user_id, slot_number)
        )
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        """Create table if it doesn't exist"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_hot_slots_v2 (
                    user_id TEXT NOT NULL,
                    slot_number INTEGER NOT NULL,
                    model_name TEXT,
                    is_pinned INTEGER DEFAULT 0,
                    loaded_at TEXT,
                    last_used TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, slot_number)
                )
            """)

            # Create index on last_used for LRU queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hot_slots_last_used
                ON user_hot_slots_v2(user_id, last_used)
            """)

            conn.commit()
            conn.close()

            logger.info("✓ Hot slots metadata schema ready")

        except Exception as e:
            logger.error(f"Failed to create hot slots metadata schema: {e}")

    def get_slot_metadata(self, user_id: str, slot_number: int) -> Optional[HotSlotMetadata]:
        """Get metadata for a specific slot"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT slot_number, model_name, is_pinned, loaded_at, last_used, created_at, updated_at
                FROM user_hot_slots_v2
                WHERE user_id = ? AND slot_number = ?
            """, (user_id, slot_number))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            return HotSlotMetadata(
                slot_number=row[0],
                model_name=row[1],
                is_pinned=bool(row[2]),
                loaded_at=datetime.fromisoformat(row[3]) if row[3] else None,
                last_used=datetime.fromisoformat(row[4]) if row[4] else None,
                created_at=datetime.fromisoformat(row[5]),
                updated_at=datetime.fromisoformat(row[6])
            )

        except Exception as e:
            logger.error(f"Failed to get slot metadata: {e}")
            return None

    def get_all_slots(self, user_id: str) -> List[HotSlotMetadata]:
        """Get metadata for all slots (1-4)"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT slot_number, model_name, is_pinned, loaded_at, last_used, created_at, updated_at
                FROM user_hot_slots_v2
                WHERE user_id = ?
                ORDER BY slot_number
            """, (user_id,))

            rows = cursor.fetchall()
            conn.close()

            # Build full slot list (1-4), filling empty slots
            slots_dict = {}
            for row in rows:
                slots_dict[row[0]] = HotSlotMetadata(
                    slot_number=row[0],
                    model_name=row[1],
                    is_pinned=bool(row[2]),
                    loaded_at=datetime.fromisoformat(row[3]) if row[3] else None,
                    last_used=datetime.fromisoformat(row[4]) if row[4] else None,
                    created_at=datetime.fromisoformat(row[5]),
                    updated_at=datetime.fromisoformat(row[6])
                )

            # Fill empty slots
            now = datetime.now(UTC)
            result = []
            for slot_num in range(1, 5):
                if slot_num in slots_dict:
                    result.append(slots_dict[slot_num])
                else:
                    result.append(HotSlotMetadata(
                        slot_number=slot_num,
                        model_name=None,
                        is_pinned=False,
                        loaded_at=None,
                        last_used=None,
                        created_at=now,
                        updated_at=now
                    ))

            return result

        except Exception as e:
            logger.error(f"Failed to get all slots: {e}")
            # Return empty slots on error
            now = datetime.now(UTC)
            return [
                HotSlotMetadata(i, None, False, None, None, now, now)
                for i in range(1, 5)
            ]

    def load_model_to_slot(
        self,
        user_id: str,
        slot_number: int,
        model_name: str,
        pin: bool = False
    ) -> bool:
        """Load a model to a slot"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            now = datetime.now(UTC).isoformat()

            cursor.execute("""
                INSERT INTO user_hot_slots_v2
                (user_id, slot_number, model_name, is_pinned, loaded_at, last_used, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, slot_number) DO UPDATE SET
                    model_name = excluded.model_name,
                    is_pinned = excluded.is_pinned,
                    loaded_at = excluded.loaded_at,
                    last_used = excluded.last_used,
                    updated_at = excluded.updated_at
            """, (user_id, slot_number, model_name, int(pin), now, now, now, now))

            conn.commit()
            conn.close()

            logger.info(f"✓ Loaded {model_name} to slot {slot_number} (pinned={pin})")
            return True

        except Exception as e:
            logger.error(f"Failed to load model to slot: {e}")
            return False

    def unload_slot(self, user_id: str, slot_number: int) -> bool:
        """Unload a model from a slot"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM user_hot_slots_v2
                WHERE user_id = ? AND slot_number = ?
            """, (user_id, slot_number))

            conn.commit()
            conn.close()

            logger.info(f"✓ Unloaded slot {slot_number}")
            return True

        except Exception as e:
            logger.error(f"Failed to unload slot: {e}")
            return False

    def toggle_pin(self, user_id: str, slot_number: int) -> Optional[bool]:
        """
        Toggle pin status for a slot

        Returns:
            New pin status (True/False), or None if slot is empty
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Get current pin status
            cursor.execute("""
                SELECT is_pinned FROM user_hot_slots_v2
                WHERE user_id = ? AND slot_number = ?
            """, (user_id, slot_number))

            row = cursor.fetchone()
            if not row:
                conn.close()
                return None  # Slot is empty

            current_pin = bool(row[0])
            new_pin = not current_pin

            # Update
            now = datetime.now(UTC).isoformat()
            cursor.execute("""
                UPDATE user_hot_slots_v2
                SET is_pinned = ?, updated_at = ?
                WHERE user_id = ? AND slot_number = ?
            """, (int(new_pin), now, user_id, slot_number))

            conn.commit()
            conn.close()

            logger.info(f"✓ Toggled pin for slot {slot_number}: {current_pin} -> {new_pin}")
            return new_pin

        except Exception as e:
            logger.error(f"Failed to toggle pin: {e}")
            return None

    def update_last_used(self, user_id: str, slot_number: int) -> bool:
        """Update last_used timestamp (for LRU tracking)"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            now = datetime.now(UTC).isoformat()
            cursor.execute("""
                UPDATE user_hot_slots_v2
                SET last_used = ?, updated_at = ?
                WHERE user_id = ? AND slot_number = ?
            """, (now, now, user_id, slot_number))

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"Failed to update last_used: {e}")
            return False

    def find_lru_slot(self, user_id: str) -> Optional[int]:
        """
        Find least recently used slot (excluding pinned)

        Returns:
            Slot number (1-4) of LRU unpinned slot, or None if all pinned
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Find unpinned slots ordered by last_used (oldest first)
            cursor.execute("""
                SELECT slot_number, last_used
                FROM user_hot_slots_v2
                WHERE user_id = ? AND is_pinned = 0 AND model_name IS NOT NULL
                ORDER BY last_used ASC NULLS FIRST
                LIMIT 1
            """, (user_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return row[0]

            return None

        except Exception as e:
            logger.error(f"Failed to find LRU slot: {e}")
            return None


# Singleton
_metadata_storage: Optional[HotSlotsMetadataStorage] = None


def get_metadata_storage(db_path: Optional[Path] = None) -> HotSlotsMetadataStorage:
    """Get or create metadata storage singleton"""
    global _metadata_storage

    if _metadata_storage is None:
        if db_path is None:
            # Default path
            from pathlib import Path
            db_path = Path.home() / ".magnetar" / "magnetar.db"

        _metadata_storage = HotSlotsMetadataStorage(db_path)

    return _metadata_storage
