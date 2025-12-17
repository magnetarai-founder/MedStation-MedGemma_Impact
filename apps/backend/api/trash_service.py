#!/usr/bin/env python3
"""
Trash Service for ElohimOS
30-day soft delete system for vault items
All deleted items are recoverable for 30 days before permanent deletion
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

# Database path
from config_paths import get_config_paths
PATHS = get_config_paths()
VAULT_DB_PATH = PATHS.data_dir / "vault.db"


# ===== Models =====

class TrashItem(BaseModel):
    """Trash item (soft-deleted document or file)"""
    id: str
    user_id: str
    vault_type: str  # 'real' or 'decoy'
    item_type: str  # 'document', 'file', 'folder'
    item_id: str  # Original item ID
    item_name: str  # Display name
    deleted_at: str
    permanent_delete_at: str  # Auto-delete after 30 days
    original_data: str  # JSON blob with original item data for restoration


class TrashStats(BaseModel):
    """Trash statistics"""
    total_items: int
    document_count: int
    file_count: int
    folder_count: int
    total_size_bytes: int
    oldest_item_date: Optional[str]


# ===== Service =====

class TrashService:
    """
    Trash service for soft deletion

    Features:
    - Soft delete with 30-day retention
    - Restore deleted items
    - Auto-cleanup of expired items
    - Separate trash for real/decoy vaults
    """

    RETENTION_DAYS = 30

    def __init__(self, db_path: Path = VAULT_DB_PATH):
        self.db_path = db_path
        self._init_db()
        logger.info(f"🗑️ Trash service initialized: {db_path}")

    def _init_db(self):
        """Initialize trash table"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vault_trash (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    vault_type TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    deleted_at TEXT NOT NULL,
                    permanent_delete_at TEXT NOT NULL,
                    original_data TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trash_user_vault
                ON vault_trash(user_id, vault_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trash_permanent_delete
                ON vault_trash(permanent_delete_at)
            """)

            conn.commit()

    def move_to_trash(
        self,
        user_id: str,
        vault_type: str,
        item_type: str,
        item_id: str,
        item_name: str,
        original_data: str
    ) -> TrashItem:
        """
        Move item to trash (soft delete)

        Args:
            user_id: User ID
            vault_type: 'real' or 'decoy'
            item_type: 'document', 'file', or 'folder'
            item_id: Original item ID
            item_name: Display name
            original_data: JSON serialized original item data
        """
        deleted_at = datetime.now(UTC)
        permanent_delete_at = deleted_at + timedelta(days=self.RETENTION_DAYS)

        trash_item = TrashItem(
            id=f"trash_{item_id}",
            user_id=user_id,
            vault_type=vault_type,
            item_type=item_type,
            item_id=item_id,
            item_name=item_name,
            deleted_at=deleted_at.isoformat(),
            permanent_delete_at=permanent_delete_at.isoformat(),
            original_data=original_data
        )

        with sqlite3.connect(self.db_path) as conn:
            # Insert into trash
            conn.execute("""
                INSERT INTO vault_trash
                (id, user_id, vault_type, item_type, item_id, item_name,
                 deleted_at, permanent_delete_at, original_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trash_item.id,
                trash_item.user_id,
                trash_item.vault_type,
                trash_item.item_type,
                trash_item.item_id,
                trash_item.item_name,
                trash_item.deleted_at,
                trash_item.permanent_delete_at,
                trash_item.original_data
            ))

            # Mark original item as deleted (add is_deleted flag)
            if item_type == 'document':
                conn.execute("""
                    UPDATE vault_documents
                    SET is_deleted = 1, deleted_at = ?
                    WHERE id = ? AND user_id = ? AND vault_type = ?
                """, (trash_item.deleted_at, item_id, user_id, vault_type))
            elif item_type == 'file':
                conn.execute("""
                    UPDATE vault_files
                    SET is_deleted = 1, deleted_at = ?
                    WHERE id = ? AND user_id = ? AND vault_type = ?
                """, (trash_item.deleted_at, item_id, user_id, vault_type))
            elif item_type == 'folder':
                conn.execute("""
                    UPDATE vault_folders
                    SET is_deleted = 1, deleted_at = ?
                    WHERE id = ? AND user_id = ? AND vault_type = ?
                """, (trash_item.deleted_at, item_id, user_id, vault_type))

            conn.commit()

        logger.info(f"🗑️ Moved to trash: {item_type} {item_id} (expires in {self.RETENTION_DAYS} days)")
        return trash_item

    def restore_from_trash(
        self,
        trash_id: str,
        user_id: str,
        vault_type: str
    ) -> bool:
        """
        Restore item from trash

        Returns True if successful, False if item not found or expired
        """
        with sqlite3.connect(self.db_path) as conn:
            # Get trash item
            row = conn.execute("""
                SELECT item_type, item_id, permanent_delete_at
                FROM vault_trash
                WHERE id = ? AND user_id = ? AND vault_type = ?
            """, (trash_id, user_id, vault_type)).fetchone()

            if not row:
                logger.warning(f"Trash item not found: {trash_id}")
                return False

            item_type, item_id, permanent_delete_at = row

            # Check if expired
            if datetime.fromisoformat(permanent_delete_at) < datetime.now(UTC):
                logger.warning(f"Trash item expired: {trash_id}")
                return False

            # Restore original item (remove is_deleted flag)
            if item_type == 'document':
                conn.execute("""
                    UPDATE vault_documents
                    SET is_deleted = 0, deleted_at = NULL
                    WHERE id = ? AND user_id = ? AND vault_type = ?
                """, (item_id, user_id, vault_type))
            elif item_type == 'file':
                conn.execute("""
                    UPDATE vault_files
                    SET is_deleted = 0, deleted_at = NULL
                    WHERE id = ? AND user_id = ? AND vault_type = ?
                """, (item_id, user_id, vault_type))
            elif item_type == 'folder':
                conn.execute("""
                    UPDATE vault_folders
                    SET is_deleted = 0, deleted_at = NULL
                    WHERE id = ? AND user_id = ? AND vault_type = ?
                """, (item_id, user_id, vault_type))

            # Remove from trash
            conn.execute("""
                DELETE FROM vault_trash
                WHERE id = ? AND user_id = ? AND vault_type = ?
            """, (trash_id, user_id, vault_type))

            conn.commit()

        logger.info(f"♻️ Restored from trash: {item_type} {item_id}")
        return True

    def get_trash_items(
        self,
        user_id: str,
        vault_type: str,
        item_type: Optional[str] = None
    ) -> List[TrashItem]:
        """Get all trash items for user and vault type"""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT id, user_id, vault_type, item_type, item_id, item_name,
                       deleted_at, permanent_delete_at, original_data
                FROM vault_trash
                WHERE user_id = ? AND vault_type = ?
            """
            params = [user_id, vault_type]

            if item_type:
                query += " AND item_type = ?"
                params.append(item_type)

            query += " ORDER BY deleted_at DESC"

            rows = conn.execute(query, params).fetchall()

        return [
            TrashItem(
                id=row[0],
                user_id=row[1],
                vault_type=row[2],
                item_type=row[3],
                item_id=row[4],
                item_name=row[5],
                deleted_at=row[6],
                permanent_delete_at=row[7],
                original_data=row[8]
            )
            for row in rows
        ]

    def permanently_delete(
        self,
        trash_id: str,
        user_id: str,
        vault_type: str
    ) -> bool:
        """
        Permanently delete item from trash (cannot be restored)
        """
        with sqlite3.connect(self.db_path) as conn:
            # Get item info
            row = conn.execute("""
                SELECT item_type, item_id
                FROM vault_trash
                WHERE id = ? AND user_id = ? AND vault_type = ?
            """, (trash_id, user_id, vault_type)).fetchone()

            if not row:
                return False

            item_type, item_id = row

            # Permanently delete from original table
            if item_type == 'document':
                conn.execute("""
                    DELETE FROM vault_documents
                    WHERE id = ? AND user_id = ? AND vault_type = ?
                """, (item_id, user_id, vault_type))
            elif item_type == 'file':
                conn.execute("""
                    DELETE FROM vault_files
                    WHERE id = ? AND user_id = ? AND vault_type = ?
                """, (item_id, user_id, vault_type))
            elif item_type == 'folder':
                conn.execute("""
                    DELETE FROM vault_folders
                    WHERE id = ? AND user_id = ? AND vault_type = ?
                """, (item_id, user_id, vault_type))

            # Remove from trash
            conn.execute("""
                DELETE FROM vault_trash
                WHERE id = ? AND user_id = ? AND vault_type = ?
            """, (trash_id, user_id, vault_type))

            conn.commit()

        logger.info(f"🔥 Permanently deleted: {item_type} {item_id}")
        return True

    def empty_trash(
        self,
        user_id: str,
        vault_type: str
    ) -> int:
        """
        Empty all trash for user and vault type
        Returns number of items deleted
        """
        items = self.get_trash_items(user_id, vault_type)

        for item in items:
            self.permanently_delete(item.id, user_id, vault_type)

        logger.info(f"🗑️ Emptied trash: {len(items)} items deleted")
        return len(items)

    def cleanup_expired(self) -> int:
        """
        Auto-cleanup: Permanently delete items past 30-day retention
        Should be run periodically (e.g., daily cron job)
        Returns number of items deleted
        """
        now = datetime.now(UTC).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            # Get expired items
            rows = conn.execute("""
                SELECT id, user_id, vault_type, item_type, item_id
                FROM vault_trash
                WHERE permanent_delete_at <= ?
            """, (now,)).fetchall()

            count = 0
            for row in rows:
                trash_id, user_id, vault_type, item_type, item_id = row

                # Permanently delete
                if item_type == 'document':
                    conn.execute("""
                        DELETE FROM vault_documents
                        WHERE id = ? AND user_id = ? AND vault_type = ?
                    """, (item_id, user_id, vault_type))
                elif item_type == 'file':
                    conn.execute("""
                        DELETE FROM vault_files
                        WHERE id = ? AND user_id = ? AND vault_type = ?
                    """, (item_id, user_id, vault_type))
                elif item_type == 'folder':
                    conn.execute("""
                        DELETE FROM vault_folders
                        WHERE id = ? AND user_id = ? AND vault_type = ?
                    """, (item_id, user_id, vault_type))

                # Remove from trash
                conn.execute("""
                    DELETE FROM vault_trash WHERE id = ?
                """, (trash_id,))

                count += 1

            conn.commit()

        logger.info(f"🧹 Auto-cleanup: {count} expired items permanently deleted")
        return count

    def get_stats(
        self,
        user_id: str,
        vault_type: str
    ) -> TrashStats:
        """Get trash statistics"""
        with sqlite3.connect(self.db_path) as conn:
            # Count by type
            counts = conn.execute("""
                SELECT item_type, COUNT(*) as count
                FROM vault_trash
                WHERE user_id = ? AND vault_type = ?
                GROUP BY item_type
            """, (user_id, vault_type)).fetchall()

            count_map = {row[0]: row[1] for row in counts}

            # Get oldest item
            oldest = conn.execute("""
                SELECT deleted_at
                FROM vault_trash
                WHERE user_id = ? AND vault_type = ?
                ORDER BY deleted_at ASC
                LIMIT 1
            """, (user_id, vault_type)).fetchone()

            # TODO: Calculate total size (would need size field in trash table)

            return TrashStats(
                total_items=sum(count_map.values()),
                document_count=count_map.get('document', 0),
                file_count=count_map.get('file', 0),
                folder_count=count_map.get('folder', 0),
                total_size_bytes=0,  # TODO: implement
                oldest_item_date=oldest[0] if oldest else None
            )


# Singleton instance
_trash_service = None


def get_trash_service() -> TrashService:
    """Get singleton trash service instance"""
    global _trash_service
    if _trash_service is None:
        _trash_service = TrashService()
        logger.info("🗑️ Trash service ready")
    return _trash_service
