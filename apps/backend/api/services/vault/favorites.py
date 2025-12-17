"""
Vault Favorites Management

Handles file favorite/bookmark functionality for quick access.
"""

import sqlite3
import uuid
import logging
from typing import Dict, Any, List
from datetime import datetime, UTC
from pathlib import Path

from api.config_paths import get_config_paths

logger = logging.getLogger(__name__)

# Configuration paths
PATHS = get_config_paths()
VAULT_DB_PATH = PATHS.data_dir / "vault.db"


def add_favorite(
    vault_service,
    user_id: str,
    vault_type: str,
    file_id: str
) -> Dict[str, Any]:
    """
    Add file to favorites.

    Args:
        vault_service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID to favorite

    Returns:
        Favorite dictionary with id, file_id, created_at

    Security:
        - Favorites are user-specific
        - Vault-type scoped
        - Duplicate prevention via UNIQUE constraint
    """
    conn = sqlite3.connect(str(vault_service.db_path))
    cursor = conn.cursor()
    now = datetime.now(UTC).isoformat()
    favorite_id = str(uuid.uuid4())

    try:
        cursor.execute("""
            INSERT OR IGNORE INTO vault_file_favorites (id, file_id, user_id, vault_type, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (favorite_id, file_id, user_id, vault_type, now))

        conn.commit()
        return {
            "id": favorite_id,
            "file_id": file_id,
            "created_at": now
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to add favorite: {e}")
        raise
    finally:
        conn.close()


def remove_favorite(
    vault_service,
    user_id: str,
    vault_type: str,
    file_id: str
) -> bool:
    """
    Remove file from favorites.

    Args:
        vault_service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID to unfavorite

    Returns:
        True if favorite was removed, False if not found

    Security:
        - User can only remove their own favorites
        - Vault-type scoped
    """
    conn = sqlite3.connect(str(vault_service.db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM vault_file_favorites
            WHERE file_id = ? AND user_id = ? AND vault_type = ?
        """, (file_id, user_id, vault_type))

        conn.commit()
        return cursor.rowcount > 0

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to remove favorite: {e}")
        raise
    finally:
        conn.close()


def get_favorites(
    vault_service,
    user_id: str,
    vault_type: str
) -> List[str]:
    """
    Get list of favorite file IDs.

    Args:
        vault_service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'

    Returns:
        List of file IDs in favorite order (most recent first)

    Security:
        - Returns only user's favorites
        - Vault-type scoped
    """
    conn = sqlite3.connect(str(vault_service.db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT file_id
            FROM vault_file_favorites
            WHERE user_id = ? AND vault_type = ?
            ORDER BY created_at DESC
        """, (user_id, vault_type))

        return [row[0] for row in cursor.fetchall()]

    finally:
        conn.close()
