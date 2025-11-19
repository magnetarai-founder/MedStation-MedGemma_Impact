"""
Vault Search Operations

Advanced file search functionality with multiple filters including
text search, MIME type, tags, date ranges, size ranges, and folder paths.
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def search_files(
    service,
    user_id: str,
    vault_type: str,
    query: Optional[str] = None,
    mime_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    folder_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Advanced file search with multiple filters

    Args:
        service: VaultService instance (for db_path access)
        user_id: User ID
        vault_type: 'real' or 'decoy'
        query: Text search query (searches in filename)
        mime_type: MIME type filter (supports prefix matching)
        tags: List of tag names to filter by
        date_from: Minimum creation date (ISO format)
        date_to: Maximum creation date (ISO format)
        min_size: Minimum file size in bytes
        max_size: Maximum file size in bytes
        folder_path: Folder path to filter by

    Returns:
        List of file dictionaries with metadata and category
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        # Build dynamic query
        sql = """
            SELECT DISTINCT f.id, f.filename, f.file_size, f.mime_type,
                   f.folder_path, f.created_at, f.updated_at,
                   CASE
                       WHEN f.mime_type LIKE 'image/%' THEN 'images'
                       WHEN f.mime_type LIKE 'video/%' THEN 'videos'
                       WHEN f.mime_type LIKE 'audio/%' THEN 'audio'
                       WHEN f.mime_type LIKE 'application/pdf' THEN 'documents'
                       WHEN f.mime_type LIKE 'text/%' THEN 'documents'
                       ELSE 'other'
                   END as category
            FROM vault_files f
        """

        conditions = ["f.user_id = ?", "f.vault_type = ?", "f.is_deleted = 0"]
        params = [user_id, vault_type]

        # Add tag join if searching by tags
        if tags:
            sql += " LEFT JOIN vault_file_tags t ON f.id = t.file_id"
            tag_conditions = " OR ".join(["t.tag_name = ?"] * len(tags))
            conditions.append(f"({tag_conditions})")
            params.extend(tags)

        # Text search
        if query:
            conditions.append("f.filename LIKE ?")
            params.append(f"%{query}%")

        # MIME type filter
        if mime_type:
            conditions.append("f.mime_type LIKE ?")
            params.append(f"{mime_type}%")

        # Date range
        if date_from:
            conditions.append("f.created_at >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("f.created_at <= ?")
            params.append(date_to)

        # Size range
        if min_size is not None:
            conditions.append("f.file_size >= ?")
            params.append(min_size)
        if max_size is not None:
            conditions.append("f.file_size <= ?")
            params.append(max_size)

        # Folder filter
        if folder_path:
            conditions.append("f.folder_path = ?")
            params.append(folder_path)

        sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY f.updated_at DESC"

        cursor.execute(sql, params)

        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "filename": row[1],
                "file_size": row[2],
                "mime_type": row[3],
                "folder_path": row[4],
                "created_at": row[5],
                "updated_at": row[6],
                "category": row[7]
            })

        return results

    finally:
        conn.close()
