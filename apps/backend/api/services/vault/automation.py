"""
Vault Automation & Organization Operations

Handles organization features like pinned files, folder colors,
and vault data export for backup purposes.
"""

import sqlite3
import logging
import uuid
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


# ========================================================================
# PINNED FILES
# ========================================================================

def pin_file(
    service,
    user_id: str,
    vault_type: str,
    file_id: str,
    pin_order: int = 0
) -> Dict[str, Any]:
    """
    Pin a file for quick access

    Args:
        service: VaultService instance (for db_path access)
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID to pin
        pin_order: Sort order for pinned files (default 0)

    Returns:
        Dictionary with pin metadata
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        pin_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        cursor.execute("""
            INSERT INTO vault_pinned_files (
                id, file_id, user_id, vault_type, pin_order, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (pin_id, file_id, user_id, vault_type, pin_order, now))

        conn.commit()

        return {
            "id": pin_id,
            "file_id": file_id,
            "pin_order": pin_order,
            "created_at": now
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to pin file: {e}")
        raise
    finally:
        conn.close()


def unpin_file(
    service,
    user_id: str,
    vault_type: str,
    file_id: str
) -> bool:
    """
    Unpin a file

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID to unpin

    Returns:
        True if file was unpinned, False if not found
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM vault_pinned_files
            WHERE file_id = ? AND user_id = ? AND vault_type = ?
        """, (file_id, user_id, vault_type))

        conn.commit()
        return cursor.rowcount > 0

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to unpin file: {e}")
        raise
    finally:
        conn.close()


def get_pinned_files(
    service,
    user_id: str,
    vault_type: str
) -> List[Dict[str, Any]]:
    """
    Get all pinned files

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'

    Returns:
        List of pinned file dictionaries with metadata
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT f.id, f.filename, f.file_size, f.mime_type,
                   f.folder_path, p.pin_order, p.created_at
            FROM vault_pinned_files p
            JOIN vault_files f ON p.file_id = f.id
            WHERE p.user_id = ? AND p.vault_type = ? AND f.is_deleted = 0
            ORDER BY p.pin_order ASC, p.created_at DESC
        """, (user_id, vault_type))

        pinned = []
        for row in cursor.fetchall():
            pinned.append({
                "id": row[0],
                "filename": row[1],
                "file_size": row[2],
                "mime_type": row[3],
                "folder_path": row[4],
                "pin_order": row[5],
                "pinned_at": row[6]
            })

        return pinned

    finally:
        conn.close()


# ========================================================================
# FOLDER COLORS
# ========================================================================

def set_folder_color(
    service,
    user_id: str,
    vault_type: str,
    folder_id: str,
    color: str
) -> Dict[str, Any]:
    """
    Set color for a folder

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        folder_id: Folder ID
        color: Color code (e.g., '#3B82F6')

    Returns:
        Dictionary with folder_id and color
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        now = datetime.now(UTC).isoformat()

        # Try to update existing color
        cursor.execute("""
            UPDATE vault_folder_colors
            SET color = ?
            WHERE folder_id = ? AND user_id = ? AND vault_type = ?
        """, (color, folder_id, user_id, vault_type))

        # If no rows updated, insert new color
        if cursor.rowcount == 0:
            color_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO vault_folder_colors (
                    id, folder_id, user_id, vault_type, color, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (color_id, folder_id, user_id, vault_type, color, now))

        conn.commit()

        return {
            "folder_id": folder_id,
            "color": color
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to set folder color: {e}")
        raise
    finally:
        conn.close()


def get_folder_colors(
    service,
    user_id: str,
    vault_type: str
) -> Dict[str, str]:
    """
    Get all folder colors

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'

    Returns:
        Dictionary mapping folder_id to color code
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT folder_id, color
            FROM vault_folder_colors
            WHERE user_id = ? AND vault_type = ?
        """, (user_id, vault_type))

        colors = {}
        for row in cursor.fetchall():
            colors[row[0]] = row[1]

        return colors

    finally:
        conn.close()


# ========================================================================
# BACKUP & EXPORT
# ========================================================================

def export_vault_data(
    service,
    user_id: str,
    vault_type: str
) -> Dict[str, Any]:
    """
    Export vault metadata for backup

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'

    Returns:
        Dictionary with vault metadata including files, folders, and tags
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        # Export files metadata
        cursor.execute("""
            SELECT id, filename, file_size, mime_type, folder_path,
                   encrypted_path,
                   CASE
                       WHEN mime_type LIKE 'image/%' THEN 'images'
                       WHEN mime_type LIKE 'video/%' THEN 'videos'
                       WHEN mime_type LIKE 'audio/%' THEN 'audio'
                       WHEN mime_type LIKE 'application/pdf' THEN 'documents'
                       WHEN mime_type LIKE 'text/%' THEN 'documents'
                       ELSE 'other'
                   END as category,
                   created_at, updated_at
            FROM vault_files
            WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
        """, (user_id, vault_type))

        files = []
        for row in cursor.fetchall():
            files.append({
                "id": row[0],
                "filename": row[1],
                "file_size": row[2],
                "mime_type": row[3],
                "folder_path": row[4],
                "encrypted_path": row[5],
                "category": row[6],
                "created_at": row[7],
                "updated_at": row[8]
            })

        # Export folders
        cursor.execute("""
            SELECT id, folder_name, folder_path, parent_path, created_at
            FROM vault_folders
            WHERE user_id = ? AND vault_type = ?
        """, (user_id, vault_type))

        folders = []
        for row in cursor.fetchall():
            folders.append({
                "id": row[0],
                "folder_name": row[1],
                "folder_path": row[2],
                "parent_path": row[3],
                "created_at": row[4]
            })

        # Export tags
        cursor.execute("""
            SELECT file_id, tag_name, tag_color
            FROM vault_file_tags
            WHERE user_id = ? AND vault_type = ?
        """, (user_id, vault_type))

        tags = []
        for row in cursor.fetchall():
            tags.append({
                "file_id": row[0],
                "tag_name": row[1],
                "tag_color": row[2]
            })

        return {
            "vault_type": vault_type,
            "export_date": datetime.now(UTC).isoformat(),
            "files": files,
            "folders": folders,
            "tags": tags
        }

    finally:
        conn.close()
