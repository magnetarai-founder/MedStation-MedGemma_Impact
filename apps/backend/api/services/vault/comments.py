"""
Vault File Comments and Metadata Module

Handles file annotations:
- Comments: User notes attached to files
- Metadata: Custom key-value pairs for files

Extracted from core.py during P2 decomposition.
"""

import uuid
import sqlite3
import logging
from datetime import datetime, UTC
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


# ===== File Comments =====

def add_file_comment(
    service: Any,
    user_id: str,
    vault_type: str,
    file_id: str,
    comment_text: str
) -> Dict[str, Any]:
    """
    Add a comment to a file.

    Args:
        service: VaultService instance (for db_path)
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID
        comment_text: Comment content

    Returns:
        Comment data with id, file_id, comment_text, created_at
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        comment_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        cursor.execute("""
            INSERT INTO vault_file_comments (
                id, file_id, user_id, vault_type, comment_text, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (comment_id, file_id, user_id, vault_type, comment_text, now))

        conn.commit()

        return {
            "id": comment_id,
            "file_id": file_id,
            "comment_text": comment_text,
            "created_at": now
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to add comment: {e}")
        raise
    finally:
        conn.close()


def get_file_comments(
    service: Any,
    user_id: str,
    vault_type: str,
    file_id: str
) -> List[Dict[str, Any]]:
    """
    Get all comments for a file.

    Args:
        service: VaultService instance (for db_path)
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID

    Returns:
        List of comments ordered by created_at DESC
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, comment_text, created_at, updated_at
            FROM vault_file_comments
            WHERE file_id = ? AND user_id = ? AND vault_type = ?
            ORDER BY created_at DESC
        """, (file_id, user_id, vault_type))

        comments = []
        for row in cursor.fetchall():
            comments.append({
                "id": row[0],
                "comment_text": row[1],
                "created_at": row[2],
                "updated_at": row[3]
            })

        return comments

    finally:
        conn.close()


def update_file_comment(
    service: Any,
    user_id: str,
    vault_type: str,
    comment_id: str,
    comment_text: str
) -> Dict[str, Any]:
    """
    Update a comment.

    Args:
        service: VaultService instance (for db_path)
        user_id: User ID
        vault_type: 'real' or 'decoy'
        comment_id: Comment ID
        comment_text: New comment content

    Returns:
        Updated comment data

    Raises:
        ValueError: If comment not found
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        now = datetime.now(UTC).isoformat()

        cursor.execute("""
            UPDATE vault_file_comments
            SET comment_text = ?, updated_at = ?
            WHERE id = ? AND user_id = ? AND vault_type = ?
        """, (comment_text, now, comment_id, user_id, vault_type))

        if cursor.rowcount == 0:
            raise ValueError("Comment not found")

        conn.commit()

        return {
            "id": comment_id,
            "comment_text": comment_text,
            "updated_at": now
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to update comment: {e}")
        raise
    finally:
        conn.close()


def delete_file_comment(
    service: Any,
    user_id: str,
    vault_type: str,
    comment_id: str
) -> bool:
    """
    Delete a comment.

    Args:
        service: VaultService instance (for db_path)
        user_id: User ID
        vault_type: 'real' or 'decoy'
        comment_id: Comment ID

    Returns:
        True if deleted, False if not found
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM vault_file_comments
            WHERE id = ? AND user_id = ? AND vault_type = ?
        """, (comment_id, user_id, vault_type))

        conn.commit()
        return cursor.rowcount > 0

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to delete comment: {e}")
        raise
    finally:
        conn.close()


# ===== File Metadata =====

def set_file_metadata(
    service: Any,
    user_id: str,
    vault_type: str,
    file_id: str,
    key: str,
    value: str
) -> Dict[str, Any]:
    """
    Set custom metadata for a file.

    Updates existing key if present, otherwise inserts new.

    Args:
        service: VaultService instance (for db_path)
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID
        key: Metadata key
        value: Metadata value

    Returns:
        Metadata entry with key, value, updated_at
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        now = datetime.now(UTC).isoformat()

        # Try to update existing metadata
        cursor.execute("""
            UPDATE vault_file_metadata
            SET value = ?, updated_at = ?
            WHERE file_id = ? AND user_id = ? AND vault_type = ? AND key = ?
        """, (value, now, file_id, user_id, vault_type, key))

        # If no rows updated, insert new metadata
        if cursor.rowcount == 0:
            metadata_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO vault_file_metadata (
                    id, file_id, user_id, vault_type, key, value, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (metadata_id, file_id, user_id, vault_type, key, value, now))

        conn.commit()

        return {
            "key": key,
            "value": value,
            "updated_at": now
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to set metadata: {e}")
        raise
    finally:
        conn.close()


def get_file_metadata(
    service: Any,
    user_id: str,
    vault_type: str,
    file_id: str
) -> Dict[str, str]:
    """
    Get all metadata for a file.

    Args:
        service: VaultService instance (for db_path)
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID

    Returns:
        Dictionary of key-value pairs
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT key, value
            FROM vault_file_metadata
            WHERE file_id = ? AND user_id = ? AND vault_type = ?
        """, (file_id, user_id, vault_type))

        metadata = {}
        for row in cursor.fetchall():
            metadata[row[0]] = row[1]

        return metadata

    finally:
        conn.close()


# Type hint for service parameter
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .core import VaultService
    Any = VaultService


__all__ = [
    "add_file_comment",
    "get_file_comments",
    "update_file_comment",
    "delete_file_comment",
    "set_file_metadata",
    "get_file_metadata",
]
