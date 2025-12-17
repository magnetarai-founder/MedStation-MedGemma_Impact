"""
Vault Tags Management

Handles file tagging functionality for organization and filtering.
"""

import sqlite3
import uuid
import logging
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from api.config_paths import get_config_paths

logger = logging.getLogger(__name__)

# Configuration paths
PATHS = get_config_paths()
VAULT_DB_PATH = PATHS.data_dir / "vault.db"


def add_tag_to_file(
    vault_service,
    user_id: str,
    vault_type: str,
    file_id: str,
    tag_name: str,
    tag_color: str = "#3B82F6"
) -> Dict[str, Any]:
    """
    Add a tag to a file.

    Args:
        vault_service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID to tag
        tag_name: Tag name
        tag_color: Hex color code for tag (default: blue)

    Returns:
        Tag dictionary with id, file_id, tag_name, tag_color, created_at

    Security:
        - Tags are vault-type scoped
        - User isolation enforced
    """
    conn = sqlite3.connect(str(vault_service.db_path))
    cursor = conn.cursor()
    now = datetime.now(UTC).isoformat()
    tag_id = str(uuid.uuid4())

    try:
        cursor.execute("""
            INSERT OR IGNORE INTO vault_file_tags (id, file_id, user_id, vault_type, tag_name, tag_color, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tag_id, file_id, user_id, vault_type, tag_name, tag_color, now))

        conn.commit()
        return {
            "id": tag_id,
            "file_id": file_id,
            "tag_name": tag_name,
            "tag_color": tag_color,
            "created_at": now
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to add tag: {e}")
        raise
    finally:
        conn.close()


def remove_tag_from_file(
    vault_service,
    user_id: str,
    vault_type: str,
    file_id: str,
    tag_name: str
) -> bool:
    """
    Remove a tag from a file.

    Args:
        vault_service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID
        tag_name: Tag name to remove

    Returns:
        True if tag was removed, False if not found

    Security:
        - User can only remove their own tags
        - Vault-type scoped
    """
    conn = sqlite3.connect(str(vault_service.db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM vault_file_tags
            WHERE file_id = ? AND user_id = ? AND vault_type = ? AND tag_name = ?
        """, (file_id, user_id, vault_type, tag_name))

        conn.commit()
        return cursor.rowcount > 0

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to remove tag: {e}")
        raise
    finally:
        conn.close()


def get_file_tags(
    vault_service,
    user_id: str,
    vault_type: str,
    file_id: str
) -> List[Dict[str, Any]]:
    """
    Get all tags for a file.

    Args:
        vault_service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID

    Returns:
        List of tag dictionaries with id, tag_name, tag_color, created_at

    Security:
        - Returns only tags for user's vault
        - Vault-type scoped
    """
    conn = sqlite3.connect(str(vault_service.db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, tag_name, tag_color, created_at
            FROM vault_file_tags
            WHERE file_id = ? AND user_id = ? AND vault_type = ?
            ORDER BY created_at DESC
        """, (file_id, user_id, vault_type))

        return [dict(row) for row in cursor.fetchall()]

    finally:
        conn.close()
