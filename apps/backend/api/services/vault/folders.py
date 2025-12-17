"""
Vault Folders Operations

Handles all folder-related operations for vault service.
"""

import sqlite3
import logging
import uuid
from typing import List
from datetime import datetime

from .schemas import VaultFolder

logger = logging.getLogger(__name__)


def create_folder(
    service,
    user_id: str,
    vault_type: str,
    folder_name: str,
    parent_path: str = "/"
) -> VaultFolder:
    """
    Create a new folder in the vault

    Args:
        service: VaultService instance (for db_path access)
        user_id: User ID
        vault_type: 'real' or 'decoy'
        folder_name: Name of the new folder
        parent_path: Parent folder path (default '/')

    Returns:
        VaultFolder object
    """
    # Build full folder path
    if parent_path == "/":
        folder_path = f"/{folder_name}"
    else:
        folder_path = f"{parent_path}/{folder_name}"

    folder_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO vault_folders
            (id, user_id, vault_type, folder_name, folder_path, parent_path,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            folder_id,
            user_id,
            vault_type,
            folder_name,
            folder_path,
            parent_path,
            now,
            now
        ))

        conn.commit()

        return VaultFolder(
            id=folder_id,
            user_id=user_id,
            vault_type=vault_type,
            folder_name=folder_name,
            folder_path=folder_path,
            parent_path=parent_path,
            created_at=now,
            updated_at=now
        )

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to create folder: {e}")
        raise
    finally:
        conn.close()


def list_folders(
    service,
    user_id: str,
    vault_type: str,
    parent_path: str = None
) -> List[VaultFolder]:
    """
    List folders, optionally filtered by parent path

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        parent_path: Optional parent path to filter by

    Returns:
        List of VaultFolder objects
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    if parent_path is not None:
        cursor.execute("""
            SELECT id, user_id, vault_type, folder_name, folder_path, parent_path,
                   created_at, updated_at
            FROM vault_folders
            WHERE user_id = ? AND vault_type = ? AND parent_path = ? AND is_deleted = 0
            ORDER BY folder_name ASC
        """, (user_id, vault_type, parent_path))
    else:
        cursor.execute("""
            SELECT id, user_id, vault_type, folder_name, folder_path, parent_path,
                   created_at, updated_at
            FROM vault_folders
            WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
            ORDER BY folder_name ASC
        """, (user_id, vault_type))

    rows = cursor.fetchall()
    conn.close()

    return [
        VaultFolder(
            id=row[0],
            user_id=row[1],
            vault_type=row[2],
            folder_name=row[3],
            folder_path=row[4],
            parent_path=row[5],
            created_at=row[6],
            updated_at=row[7]
        )
        for row in rows
    ]


def delete_folder(
    service,
    user_id: str,
    vault_type: str,
    folder_path: str
) -> bool:
    """
    Soft-delete a folder (and all files/subfolders in it)

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        folder_path: Full folder path to delete

    Returns:
        True if folder was deleted, False otherwise
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()
    now = datetime.now(UTC).isoformat()

    try:
        # Delete folder
        cursor.execute("""
            UPDATE vault_folders
            SET is_deleted = 1, deleted_at = ?
            WHERE user_id = ? AND vault_type = ? AND folder_path = ? AND is_deleted = 0
        """, (now, user_id, vault_type, folder_path))

        # Delete all files in this folder
        cursor.execute("""
            UPDATE vault_files
            SET is_deleted = 1, deleted_at = ?
            WHERE user_id = ? AND vault_type = ? AND folder_path = ? AND is_deleted = 0
        """, (now, user_id, vault_type, folder_path))

        # Delete all subfolders (folders that start with this path)
        cursor.execute("""
            UPDATE vault_folders
            SET is_deleted = 1, deleted_at = ?
            WHERE user_id = ? AND vault_type = ?
            AND folder_path LIKE ? AND is_deleted = 0
        """, (now, user_id, vault_type, f"{folder_path}/%"))

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to delete folder: {e}")
        raise
    finally:
        conn.close()


def rename_folder(
    service,
    user_id: str,
    vault_type: str,
    old_path: str,
    new_name: str
) -> bool:
    """
    Rename a folder and update all nested paths

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        old_path: Current folder path
        new_name: New folder name

    Returns:
        True if folder was renamed, False otherwise
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()
    now = datetime.now(UTC).isoformat()

    try:
        # Calculate new path
        parent_path = old_path.rsplit('/', 1)[0] if old_path.count('/') > 0 else '/'
        new_path = f"{parent_path}/{new_name}" if parent_path != '/' else f"/{new_name}"

        # Update the folder itself
        cursor.execute("""
            UPDATE vault_folders
            SET folder_name = ?, folder_path = ?, updated_at = ?
            WHERE user_id = ? AND vault_type = ? AND folder_path = ? AND is_deleted = 0
        """, (new_name, new_path, now, user_id, vault_type, old_path))

        # Update all subfolders
        cursor.execute("""
            UPDATE vault_folders
            SET folder_path = REPLACE(folder_path, ?, ?), updated_at = ?
            WHERE user_id = ? AND vault_type = ?
            AND folder_path LIKE ? AND is_deleted = 0
        """, (old_path, new_path, now, user_id, vault_type, f"{old_path}/%"))

        # Update all files in this folder
        cursor.execute("""
            UPDATE vault_files
            SET folder_path = ?, updated_at = ?
            WHERE user_id = ? AND vault_type = ? AND folder_path = ? AND is_deleted = 0
        """, (new_path, now, user_id, vault_type, old_path))

        # Update files in subfolders
        cursor.execute("""
            UPDATE vault_files
            SET folder_path = REPLACE(folder_path, ?, ?), updated_at = ?
            WHERE user_id = ? AND vault_type = ?
            AND folder_path LIKE ? AND is_deleted = 0
        """, (old_path, new_path, now, user_id, vault_type, f"{old_path}/%"))

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to rename folder: {e}")
        raise
    finally:
        conn.close()
