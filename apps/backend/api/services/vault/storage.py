"""
Vault Service Storage Layer

Database access functions for vault-related persistence.
All raw DB operations for vault documents should go through this module.
"""

import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from .schemas import VaultDocument, VaultDocumentCreate, VaultDocumentUpdate, VaultFile

logger = logging.getLogger(__name__)


def _get_vault_conn() -> sqlite3.Connection:
    """Get connection to vault database with row factory"""
    from api.config_paths import get_config_paths
    PATHS = get_config_paths()
    VAULT_DB_PATH = PATHS.data_dir / "vault.db"
    conn = sqlite3.connect(str(VAULT_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ========================================================================
# DOCUMENT CRUD OPERATIONS
# ========================================================================

def store_document_record(
    user_id: str,
    doc: VaultDocumentCreate,
    team_id: Optional[str] = None
) -> VaultDocument:
    """
    Store encrypted vault document

    Args:
        user_id: User ID from auth
        doc: Encrypted document data
        team_id: Optional team ID for team-scoped documents

    Returns:
        Stored vault document
    """
    now = datetime.utcnow().isoformat()
    size_bytes = len(doc.encrypted_blob) + len(doc.encrypted_metadata)

    conn = _get_vault_conn()
    cursor = conn.cursor()

    try:
        # Phase 3: include team_id if column exists (added by migration)
        cursor.execute("PRAGMA table_info(vault_documents)")
        cols = [r[1] for r in cursor.fetchall()]
        has_team_id = "team_id" in cols

        if has_team_id:
            cursor.execute(
                """
                INSERT OR REPLACE INTO vault_documents
                (id, user_id, vault_type, encrypted_blob, encrypted_metadata,
                 created_at, updated_at, size_bytes, team_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.id,
                    user_id,
                    doc.vault_type,
                    doc.encrypted_blob,
                    doc.encrypted_metadata,
                    now,
                    now,
                    size_bytes,
                    team_id,
                ),
            )
        else:
            cursor.execute(
                """
                INSERT OR REPLACE INTO vault_documents
                (id, user_id, vault_type, encrypted_blob, encrypted_metadata,
                 created_at, updated_at, size_bytes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.id,
                    user_id,
                    doc.vault_type,
                    doc.encrypted_blob,
                    doc.encrypted_metadata,
                    now,
                    now,
                    size_bytes,
                ),
            )

        conn.commit()

        return VaultDocument(
            id=doc.id,
            user_id=user_id,
            vault_type=doc.vault_type,
            encrypted_blob=doc.encrypted_blob,
            encrypted_metadata=doc.encrypted_metadata,
            created_at=now,
            updated_at=now,
            size_bytes=size_bytes
        )

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to store vault document: {e}")
        raise
    finally:
        conn.close()


def get_document_record(
    user_id: str,
    doc_id: str,
    vault_type: str,
    team_id: Optional[str] = None
) -> Optional[VaultDocument]:
    """Get encrypted vault document by ID (Phase 3: optional team scope)"""
    conn = _get_vault_conn()
    cursor = conn.cursor()

    if team_id:
        cursor.execute(
            """
            SELECT id, user_id, vault_type, encrypted_blob, encrypted_metadata,
                   created_at, updated_at, size_bytes
            FROM vault_documents
            WHERE id = ? AND team_id = ? AND vault_type = ? AND is_deleted = 0
            """,
            (doc_id, team_id, vault_type),
        )
    else:
        cursor.execute(
            """
            SELECT id, user_id, vault_type, encrypted_blob, encrypted_metadata,
                   created_at, updated_at, size_bytes
            FROM vault_documents
            WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0 AND (team_id IS NULL OR team_id = '')
            """,
            (doc_id, user_id, vault_type),
        )

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return VaultDocument(
        id=row[0],
        user_id=row[1],
        vault_type=row[2],
        encrypted_blob=row[3],
        encrypted_metadata=row[4],
        created_at=row[5],
        updated_at=row[6],
        size_bytes=row[7]
    )


def list_documents_records(
    user_id: str,
    vault_type: str,
    team_id: Optional[str] = None
) -> List[VaultDocument]:
    """
    List all vault documents for a user and vault type

    Phase 3: if team_id is provided, return team-scoped documents.

    Args:
        user_id: User ID
        vault_type: Vault type ('real', 'decoy', 'personal', or 'team')
        team_id: Optional team ID for team-scoped documents

    Returns:
        List of vault documents
    """
    conn = _get_vault_conn()
    cursor = conn.cursor()

    # Map API vault_type to DB vault_type
    db_vault_type = vault_type
    if vault_type in ("personal", "team"):
        db_vault_type = "real"

    if team_id:
        # Team documents: filter by team_id and 'real'
        cursor.execute(
            """
            SELECT id, user_id, vault_type, encrypted_blob, encrypted_metadata,
                   created_at, updated_at, size_bytes
            FROM vault_documents
            WHERE team_id = ? AND vault_type = ? AND is_deleted = 0
            ORDER BY updated_at DESC
            """,
            (team_id, db_vault_type),
        )
    else:
        # Personal/decoy: filter by user_id and team_id IS NULL
        cursor.execute(
            """
            SELECT id, user_id, vault_type, encrypted_blob, encrypted_metadata,
                   created_at, updated_at, size_bytes
            FROM vault_documents
            WHERE user_id = ? AND vault_type = ? AND is_deleted = 0 AND (team_id IS NULL OR team_id = '')
            ORDER BY updated_at DESC
            """,
            (user_id, db_vault_type),
        )

    rows = cursor.fetchall()
    conn.close()

    documents = [
        VaultDocument(
            id=row[0],
            user_id=row[1],
            vault_type=row[2],
            encrypted_blob=row[3],
            encrypted_metadata=row[4],
            created_at=row[5],
            updated_at=row[6],
            size_bytes=row[7]
        )
        for row in rows
    ]

    return documents


def update_document_record(
    user_id: str,
    doc_id: str,
    vault_type: str,
    update: VaultDocumentUpdate,
    team_id: Optional[str] = None
) -> Tuple[bool, int]:
    """
    Update encrypted vault document (Phase 3: optional team scope)

    Args:
        user_id: User ID
        doc_id: Document ID
        vault_type: Vault type
        update: Document update data
        team_id: Optional team ID

    Returns:
        Tuple of (success: bool, rowcount: int)
    """
    conn = _get_vault_conn()
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()
    size_bytes = len(update.encrypted_blob) + len(update.encrypted_metadata)

    try:
        if team_id:
            cursor.execute(
                """
                UPDATE vault_documents
                SET encrypted_blob = ?,
                    encrypted_metadata = ?,
                    updated_at = ?,
                    size_bytes = ?
                WHERE id = ? AND team_id = ? AND vault_type = ? AND is_deleted = 0
                """,
                (
                    update.encrypted_blob,
                    update.encrypted_metadata,
                    now,
                    size_bytes,
                    doc_id,
                    team_id,
                    vault_type,
                ),
            )
        else:
            cursor.execute(
                """
                UPDATE vault_documents
                SET encrypted_blob = ?,
                    encrypted_metadata = ?,
                    updated_at = ?,
                    size_bytes = ?
                WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0 AND (team_id IS NULL OR team_id = '')
                """,
                (
                    update.encrypted_blob,
                    update.encrypted_metadata,
                    now,
                    size_bytes,
                    doc_id,
                    user_id,
                    vault_type,
                ),
            )

        rowcount = cursor.rowcount
        conn.commit()
        return True, rowcount

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to update vault document: {e}")
        raise
    finally:
        conn.close()


def delete_document_record(
    user_id: str,
    doc_id: str,
    vault_type: str,
    team_id: Optional[str] = None
) -> bool:
    """
    Soft-delete vault document (Phase 3: optional team scope)

    Args:
        user_id: User ID
        doc_id: Document ID
        vault_type: Vault type
        team_id: Optional team ID

    Returns:
        True if document was deleted (rowcount > 0)
    """
    conn = _get_vault_conn()
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()

    try:
        if team_id:
            cursor.execute(
                """
                UPDATE vault_documents
                SET is_deleted = 1,
                    deleted_at = ?
                WHERE id = ? AND team_id = ? AND vault_type = ? AND is_deleted = 0
                """,
                (now, doc_id, team_id, vault_type),
            )
        else:
            cursor.execute(
                """
                UPDATE vault_documents
                SET is_deleted = 1,
                    deleted_at = ?
                WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0 AND (team_id IS NULL OR team_id = '')
                """,
                (now, doc_id, user_id, vault_type),
            )

        conn.commit()
        return cursor.rowcount > 0

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to delete vault document: {e}")
        raise
    finally:
        conn.close()


def get_vault_stats_record(user_id: str, vault_type: str) -> Dict[str, Any]:
    """
    Get vault statistics

    Args:
        user_id: User ID
        vault_type: Vault type

    Returns:
        Dictionary with document_count, total_size_bytes, vault_type
    """
    conn = _get_vault_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as doc_count,
            SUM(size_bytes) as total_size
        FROM vault_documents
        WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
    """, (user_id, vault_type))

    row = cursor.fetchone()
    conn.close()

    return {
        "document_count": row[0] or 0,
        "total_size_bytes": row[1] or 0,
        "vault_type": vault_type
    }

# ========================================================================
# FILE CRUD OPERATIONS
# ========================================================================

def create_file_record(
    file_id: str,
    user_id: str,
    vault_type: str,
    filename: str,
    file_size: int,
    mime_type: str,
    encrypted_path: str,
    folder_path: str,
    created_at: str,
    updated_at: str
) -> VaultFile:
    """
    Store file metadata in database

    Args:
        file_id: Unique file identifier
        user_id: User ID
        vault_type: 'real' or 'decoy'
        filename: Original filename
        file_size: File size in bytes
        mime_type: MIME type
        encrypted_path: Path to encrypted file on disk
        folder_path: Folder path in vault
        created_at: Creation timestamp
        updated_at: Update timestamp

    Returns:
        VaultFile object
    """
    conn = _get_vault_conn()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO vault_files
            (id, user_id, vault_type, filename, file_size, mime_type,
             encrypted_path, folder_path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            file_id,
            user_id,
            vault_type,
            filename,
            file_size,
            mime_type,
            encrypted_path,
            folder_path,
            created_at,
            updated_at
        ))

        conn.commit()

        return VaultFile(
            id=file_id,
            user_id=user_id,
            vault_type=vault_type,
            filename=filename,
            file_size=file_size,
            mime_type=mime_type,
            encrypted_path=encrypted_path,
            folder_path=folder_path,
            created_at=created_at,
            updated_at=updated_at
        )

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to create file record: {e}")
        raise
    finally:
        conn.close()


def list_files_records(
    user_id: str,
    vault_type: str,
    folder_path: Optional[str] = None
) -> List[VaultFile]:
    """
    List vault files, optionally filtered by folder

    Args:
        user_id: User ID
        vault_type: 'real' or 'decoy'
        folder_path: Optional folder path to filter by

    Returns:
        List of VaultFile objects
    """
    conn = _get_vault_conn()
    cursor = conn.cursor()

    if folder_path is not None:
        # List files in specific folder only
        cursor.execute("""
            SELECT id, user_id, vault_type, filename, file_size, mime_type,
                   encrypted_path, folder_path, created_at, updated_at
            FROM vault_files
            WHERE user_id = ? AND vault_type = ? AND folder_path = ? AND is_deleted = 0
            ORDER BY created_at DESC
        """, (user_id, vault_type, folder_path))
    else:
        # List all files
        cursor.execute("""
            SELECT id, user_id, vault_type, filename, file_size, mime_type,
                   encrypted_path, folder_path, created_at, updated_at
            FROM vault_files
            WHERE user_id = ? AND vault_type = ? AND is_deleted = 0
            ORDER BY created_at DESC
        """, (user_id, vault_type))

    rows = cursor.fetchall()
    conn.close()

    return [
        VaultFile(
            id=row[0],
            user_id=row[1],
            vault_type=row[2],
            filename=row[3],
            file_size=row[4],
            mime_type=row[5],
            encrypted_path=row[6],
            folder_path=row[7],
            created_at=row[8],
            updated_at=row[9]
        )
        for row in rows
    ]


def delete_file_record(
    file_id: str,
    user_id: str,
    vault_type: str,
    deleted_at: str
) -> bool:
    """
    Soft-delete a file

    Args:
        file_id: File ID
        user_id: User ID
        vault_type: 'real' or 'decoy'
        deleted_at: Deletion timestamp

    Returns:
        True if file was deleted, False otherwise
    """
    conn = _get_vault_conn()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE vault_files
            SET is_deleted = 1, deleted_at = ?
            WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0
        """, (deleted_at, file_id, user_id, vault_type))

        conn.commit()
        success = cursor.rowcount > 0
        return success

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to delete file: {e}")
        raise
    finally:
        conn.close()


def rename_file_record(
    file_id: str,
    user_id: str,
    vault_type: str,
    new_filename: str,
    updated_at: str
) -> bool:
    """
    Rename a file

    Args:
        file_id: File ID
        user_id: User ID
        vault_type: 'real' or 'decoy'
        new_filename: New filename
        updated_at: Update timestamp

    Returns:
        True if file was renamed, False otherwise
    """
    conn = _get_vault_conn()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE vault_files
            SET filename = ?, updated_at = ?
            WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0
        """, (new_filename, updated_at, file_id, user_id, vault_type))

        conn.commit()
        success = cursor.rowcount > 0
        return success

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to rename file: {e}")
        raise
    finally:
        conn.close()


def move_file_record(
    file_id: str,
    user_id: str,
    vault_type: str,
    new_folder_path: str,
    updated_at: str
) -> bool:
    """
    Move a file to a different folder

    Args:
        file_id: File ID
        user_id: User ID
        vault_type: 'real' or 'decoy'
        new_folder_path: New folder path
        updated_at: Update timestamp

    Returns:
        True if file was moved, False otherwise
    """
    conn = _get_vault_conn()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE vault_files
            SET folder_path = ?, updated_at = ?
            WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0
        """, (new_folder_path, updated_at, file_id, user_id, vault_type))

        conn.commit()
        success = cursor.rowcount > 0
        return success

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to move file: {e}")
        raise
    finally:
        conn.close()
