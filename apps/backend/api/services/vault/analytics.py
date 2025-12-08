"""
Vault Analytics & Statistics

Handles file access logging, recent files tracking, and storage statistics.
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


def log_file_access(
    vault_service,
    user_id: str,
    vault_type: str,
    file_id: str,
    access_type: str = "view"
) -> None:
    """
    Log file access for recent files tracking and analytics.

    Args:
        vault_service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID that was accessed
        access_type: Type of access ('view', 'download', 'preview')

    Security:
        - Access logs are vault-type scoped
        - Does not fail main operation if logging fails
        - User isolation enforced
    """
    conn = sqlite3.connect(str(vault_service.db_path))
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    log_id = str(uuid.uuid4())

    try:
        cursor.execute("""
            INSERT INTO vault_file_access_logs (id, file_id, user_id, vault_type, access_type, accessed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (log_id, file_id, user_id, vault_type, access_type, now))

        conn.commit()

    except Exception as e:
        # Don't fail the main operation if logging fails
        logger.warning(f"Failed to log file access: {e}")
    finally:
        conn.close()


def get_recent_files(
    vault_service,
    user_id: str,
    vault_type: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get recently accessed files.

    Args:
        vault_service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        limit: Maximum number of files to return (default: 10)

    Returns:
        List of file dictionaries with metadata and last_accessed timestamp

    Security:
        - Returns only user's files
        - Vault-type scoped
        - Excludes deleted files
    """
    conn = sqlite3.connect(str(vault_service.db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT DISTINCT
                vf.id, vf.filename, vf.file_size, vf.mime_type, vf.folder_path,
                vf.created_at, vf.updated_at,
                MAX(val.accessed_at) as last_accessed
            FROM vault_files vf
            INNER JOIN vault_file_access_logs val ON vf.id = val.file_id
            WHERE vf.user_id = ? AND vf.vault_type = ? AND vf.is_deleted = 0
            GROUP BY vf.id
            ORDER BY last_accessed DESC
            LIMIT ?
        """, (user_id, vault_type, limit))

        return [dict(row) for row in cursor.fetchall()]

    finally:
        conn.close()


def get_storage_stats(
    vault_service,
    user_id: str,
    vault_type: str
) -> Dict[str, Any]:
    """
    Get comprehensive storage statistics.

    Args:
        vault_service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'

    Returns:
        Dictionary containing:
        - total_files: Total number of files
        - total_size: Total storage used in bytes
        - breakdown: List of file type categories with count and size
        - largest_files: Top 10 largest files

    Security:
        - Returns only user's statistics
        - Vault-type scoped
        - Excludes deleted files
    """
    conn = sqlite3.connect(str(vault_service.db_path))
    cursor = conn.cursor()

    try:
        # Get total files and size
        cursor.execute("""
            SELECT COUNT(*) as total_files, COALESCE(SUM(file_size), 0) as total_size
            FROM vault_files
            WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
        """, (user_id, vault_type))

        total_files, total_size = cursor.fetchone()

        # Get file type breakdown
        cursor.execute("""
            SELECT
                CASE
                    WHEN mime_type LIKE 'image/%' THEN 'images'
                    WHEN mime_type LIKE 'video/%' THEN 'videos'
                    WHEN mime_type LIKE 'audio/%' THEN 'audio'
                    WHEN mime_type LIKE 'application/pdf' THEN 'documents'
                    WHEN mime_type LIKE 'text/%' THEN 'documents'
                    ELSE 'other'
                END as category,
                COUNT(*) as count,
                COALESCE(SUM(file_size), 0) as size
            FROM vault_files
            WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
            GROUP BY category
        """, (user_id, vault_type))

        breakdown = []
        for row in cursor.fetchall():
            category, count, size = row
            breakdown.append({
                "category": category,
                "count": count,
                "size": size
            })

        # Get largest files
        cursor.execute("""
            SELECT id, filename, file_size, mime_type, folder_path
            FROM vault_files
            WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
            ORDER BY file_size DESC
            LIMIT 10
        """, (user_id, vault_type))

        largest_files = []
        for row in cursor.fetchall():
            largest_files.append({
                "id": row[0],
                "filename": row[1],
                "file_size": row[2],
                "mime_type": row[3],
                "folder_path": row[4]
            })

        return {
            "total_files": total_files,
            "total_size": total_size,
            "breakdown": breakdown,
            "largest_files": largest_files
        }

    finally:
        conn.close()
