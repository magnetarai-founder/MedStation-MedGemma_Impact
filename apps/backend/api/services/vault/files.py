"""
Vault Files Operations

Handles all file-related operations for vault service including:
- File upload/list/delete
- File versioning
- Trash/recycle bin
- Secure deletion
- Tags, favorites, and metadata
"""

import sqlite3
import logging
import hashlib
import uuid
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from cryptography.fernet import Fernet

from .schemas import VaultFile
from . import storage, encryption

logger = logging.getLogger(__name__)


# ========================================================================
# CORE FILE OPERATIONS
# ========================================================================

def upload_file(
    service,
    user_id: str,
    file_data: bytes,
    filename: str,
    mime_type: str,
    vault_type: str,
    passphrase: str,
    folder_path: str = "/"
) -> VaultFile:
    """
    Encrypt and store file in vault

    Args:
        service: VaultService instance (for db_path/files_path access)
        user_id: User ID
        file_data: Raw file bytes
        filename: Original filename
        mime_type: MIME type
        vault_type: 'real' or 'decoy'
        passphrase: Vault passphrase for encryption
        folder_path: Folder path (default '/')

    Returns:
        VaultFile metadata
    """
    # Generate unique file ID
    file_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    # Encrypt file data
    key, salt = encryption.get_encryption_key(passphrase)
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(file_data)

    # Save encrypted file to disk
    encrypted_filename = f"{file_id}_{hashlib.sha256(filename.encode()).hexdigest()}.enc"
    encrypted_path = service.files_path / encrypted_filename

    with open(encrypted_path, 'wb') as f:
        f.write(encrypted_data)

    # Store metadata in database
    try:
        return storage.create_file_record(
            file_id=file_id,
            user_id=user_id,
            vault_type=vault_type,
            filename=filename,
            file_size=len(file_data),
            mime_type=mime_type,
            encrypted_path=str(encrypted_path),
            folder_path=folder_path,
            created_at=now,
            updated_at=now
        )
    except Exception as e:
        # Clean up file if database insert fails
        if encrypted_path.exists():
            encrypted_path.unlink()
        logger.error(f"Failed to upload file: {e}")
        raise


def list_files(
    service,
    user_id: str,
    vault_type: str,
    folder_path: Optional[str] = None
) -> List[VaultFile]:
    """
    List vault files, optionally filtered by folder

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        folder_path: Optional folder path to filter by

    Returns:
        List of VaultFile objects
    """
    return storage.list_files_records(user_id, vault_type, folder_path)


def delete_file(service, user_id: str, vault_type: str, file_id: str) -> bool:
    """
    Soft-delete a file

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID

    Returns:
        True if file was deleted, False otherwise
    """
    now = datetime.now(UTC).isoformat()
    return storage.delete_file_record(file_id, user_id, vault_type, now)


def rename_file(
    service,
    user_id: str,
    vault_type: str,
    file_id: str,
    new_filename: str
) -> bool:
    """
    Rename a file

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID
        new_filename: New filename

    Returns:
        True if file was renamed, False otherwise
    """
    now = datetime.now(UTC).isoformat()
    return storage.rename_file_record(file_id, user_id, vault_type, new_filename, now)


def move_file(
    service,
    user_id: str,
    vault_type: str,
    file_id: str,
    new_folder_path: str
) -> bool:
    """
    Move a file to a different folder

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID
        new_folder_path: New folder path

    Returns:
        True if file was moved, False otherwise
    """
    now = datetime.now(UTC).isoformat()
    return storage.move_file_record(file_id, user_id, vault_type, new_folder_path, now)


# ========================================================================
# FILE VERSIONING
# ========================================================================

def create_file_version(
    service,
    user_id: str,
    vault_type: str,
    file_id: str,
    encrypted_path: str,
    file_size: int,
    mime_type: str,
    comment: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new version of a file

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID
        encrypted_path: Path to encrypted version file
        file_size: Version file size
        mime_type: MIME type
        comment: Optional version comment

    Returns:
        Dictionary with version metadata
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        # Get current version count
        cursor.execute("""
            SELECT COALESCE(MAX(version_number), 0)
            FROM vault_file_versions
            WHERE file_id = ?
        """, (file_id,))

        current_version = cursor.fetchone()[0]
        new_version = current_version + 1

        # Create version record
        version_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        cursor.execute("""
            INSERT INTO vault_file_versions (
                id, file_id, user_id, vault_type, version_number,
                encrypted_path, file_size, mime_type, created_at,
                created_by, comment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (version_id, file_id, user_id, vault_type, new_version,
              encrypted_path, file_size, mime_type, now, user_id, comment))

        conn.commit()

        return {
            "id": version_id,
            "file_id": file_id,
            "version_number": new_version,
            "file_size": file_size,
            "mime_type": mime_type,
            "created_at": now,
            "comment": comment
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to create file version: {e}")
        raise
    finally:
        conn.close()


def get_file_versions(
    service,
    user_id: str,
    vault_type: str,
    file_id: str
) -> List[Dict[str, Any]]:
    """
    Get all versions of a file

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID

    Returns:
        List of version dictionaries
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, version_number, file_size, mime_type,
                   created_at, created_by, comment
            FROM vault_file_versions
            WHERE file_id = ? AND user_id = ? AND vault_type = ?
            ORDER BY version_number DESC
        """, (file_id, user_id, vault_type))

        versions = []
        for row in cursor.fetchall():
            versions.append({
                "id": row[0],
                "version_number": row[1],
                "file_size": row[2],
                "mime_type": row[3],
                "created_at": row[4],
                "created_by": row[5],
                "comment": row[6]
            })

        return versions

    finally:
        conn.close()


def restore_file_version(
    service,
    user_id: str,
    vault_type: str,
    file_id: str,
    version_id: str
) -> Dict[str, Any]:
    """
    Restore a file to a previous version

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID
        version_id: Version ID to restore

    Returns:
        Dictionary with restore result

    Raises:
        ValueError: If version or file not found
    """
    import shutil
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        # Get version details
        cursor.execute("""
            SELECT encrypted_path, file_size, mime_type, version_number
            FROM vault_file_versions
            WHERE id = ? AND file_id = ? AND user_id = ? AND vault_type = ?
        """, (version_id, file_id, user_id, vault_type))

        version_data = cursor.fetchone()
        if not version_data:
            raise ValueError("Version not found")

        version_encrypted_path, version_size, version_mime, version_number = version_data

        # Get current file details
        cursor.execute("""
            SELECT encrypted_path
            FROM vault_files
            WHERE id = ? AND user_id = ? AND vault_type = ?
        """, (file_id, user_id, vault_type))

        current_data = cursor.fetchone()
        if not current_data:
            raise ValueError("File not found")

        current_encrypted_path = current_data[0]

        # Copy version file to current file location
        version_path = service.files_path / version_encrypted_path
        current_path = service.files_path / current_encrypted_path

        if version_path.exists():
            shutil.copy2(version_path, current_path)

        # Update file record
        now = datetime.now(UTC).isoformat()
        cursor.execute("""
            UPDATE vault_files
            SET file_size = ?, mime_type = ?, updated_at = ?
            WHERE id = ? AND user_id = ? AND vault_type = ?
        """, (version_size, version_mime, now, file_id, user_id, vault_type))

        conn.commit()

        return {
            "id": file_id,
            "restored_version": version_number,
            "file_size": version_size,
            "updated_at": now
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to restore file version: {e}")
        raise
    finally:
        conn.close()


def delete_file_version(
    service,
    user_id: str,
    vault_type: str,
    version_id: str
) -> bool:
    """
    Delete a specific file version

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        version_id: Version ID

    Returns:
        True if version was deleted, False otherwise
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        # Get version file path
        cursor.execute("""
            SELECT encrypted_path
            FROM vault_file_versions
            WHERE id = ? AND user_id = ? AND vault_type = ?
        """, (version_id, user_id, vault_type))

        result = cursor.fetchone()
        if not result:
            return False

        encrypted_path = result[0]

        # Delete physical file
        file_path = service.files_path / encrypted_path
        if file_path.exists():
            os.remove(file_path)

        # Delete version record
        cursor.execute("""
            DELETE FROM vault_file_versions
            WHERE id = ? AND user_id = ? AND vault_type = ?
        """, (version_id, user_id, vault_type))

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to delete file version: {e}")
        raise
    finally:
        conn.close()


# ========================================================================
# TRASH/RECYCLE BIN
# ========================================================================

def move_to_trash(
    service,
    user_id: str,
    vault_type: str,
    file_id: str
) -> Dict[str, Any]:
    """
    Move a file to trash (soft delete)

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID

    Returns:
        Dictionary with trash status

    Raises:
        ValueError: If file not found or already deleted
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        now = datetime.now(UTC).isoformat()

        cursor.execute("""
            UPDATE vault_files
            SET is_deleted = 1, deleted_at = ?
            WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0
        """, (now, file_id, user_id, vault_type))

        if cursor.rowcount == 0:
            raise ValueError("File not found or already deleted")

        conn.commit()

        return {
            "id": file_id,
            "deleted_at": now,
            "status": "moved to trash"
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to move file to trash: {e}")
        raise
    finally:
        conn.close()


def restore_from_trash(
    service,
    user_id: str,
    vault_type: str,
    file_id: str
) -> Dict[str, Any]:
    """
    Restore a file from trash

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID

    Returns:
        Dictionary with restore status

    Raises:
        ValueError: If file not found in trash
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE vault_files
            SET is_deleted = 0, deleted_at = NULL
            WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 1
        """, (file_id, user_id, vault_type))

        if cursor.rowcount == 0:
            raise ValueError("File not found in trash")

        conn.commit()

        return {
            "id": file_id,
            "status": "restored from trash"
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to restore file from trash: {e}")
        raise
    finally:
        conn.close()


def get_trash_files(
    service,
    user_id: str,
    vault_type: str
) -> List[Dict[str, Any]]:
    """
    Get all files in trash

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'

    Returns:
        List of trash file dictionaries
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, filename, file_size, mime_type, folder_path,
                   deleted_at,
                   CASE
                       WHEN mime_type LIKE 'image/%' THEN 'images'
                       WHEN mime_type LIKE 'video/%' THEN 'videos'
                       WHEN mime_type LIKE 'audio/%' THEN 'audio'
                       WHEN mime_type LIKE 'application/pdf' THEN 'documents'
                       WHEN mime_type LIKE 'text/%' THEN 'documents'
                       ELSE 'other'
                   END as category
            FROM vault_files
            WHERE user_id = ? AND vault_type = ? AND is_deleted = 1
            ORDER BY deleted_at DESC
        """, (user_id, vault_type))

        trash_files = []
        for row in cursor.fetchall():
            trash_files.append({
                "id": row[0],
                "filename": row[1],
                "file_size": row[2],
                "mime_type": row[3],
                "folder_path": row[4],
                "deleted_at": row[5],
                "category": row[6]
            })

        return trash_files

    finally:
        conn.close()


def empty_trash(
    service,
    user_id: str,
    vault_type: str
) -> Dict[str, Any]:
    """
    Permanently delete all files in trash

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'

    Returns:
        Dictionary with deletion count
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        # Get all trashed files
        cursor.execute("""
            SELECT id, encrypted_path
            FROM vault_files
            WHERE user_id = ? AND vault_type = ? AND is_deleted = 1
        """, (user_id, vault_type))

        trashed_files = cursor.fetchall()
        deleted_count = 0

        # Delete physical files
        for file_id, encrypted_path in trashed_files:
            file_path = service.files_path / encrypted_path
            if file_path.exists():
                os.remove(file_path)
            deleted_count += 1

        # Delete from database
        cursor.execute("""
            DELETE FROM vault_files
            WHERE user_id = ? AND vault_type = ? AND is_deleted = 1
        """, (user_id, vault_type))

        conn.commit()

        return {
            "deleted_count": deleted_count,
            "status": "trash emptied"
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to empty trash: {e}")
        raise
    finally:
        conn.close()


# ========================================================================
# SECURE DELETION
# ========================================================================

def secure_delete_file(
    service,
    user_id: str,
    vault_type: str,
    file_id: str
) -> bool:
    """
    Securely delete a file by overwriting with random data before deletion

    Args:
        service: VaultService instance
        user_id: User ID
        vault_type: 'real' or 'decoy'
        file_id: File ID

    Returns:
        True if file was securely deleted, False otherwise
    """
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    try:
        # Get file path
        cursor.execute("""
            SELECT encrypted_path
            FROM vault_files
            WHERE id = ? AND user_id = ? AND vault_type = ? AND is_deleted = 0
        """, (file_id, user_id, vault_type))

        result = cursor.fetchone()
        if not result:
            return False

        encrypted_path = result[0]
        file_path = service.files_path / encrypted_path

        # Securely overwrite file with random data (3 passes)
        if file_path.exists():
            file_size = file_path.stat().st_size
            with open(file_path, 'wb') as f:
                for _ in range(3):
                    f.seek(0)
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())

            # Delete the file
            os.remove(file_path)

        # Mark as deleted in database
        now = datetime.now(UTC).isoformat()
        cursor.execute("""
            UPDATE vault_files
            SET is_deleted = 1, deleted_at = ?
            WHERE id = ? AND user_id = ? AND vault_type = ?
        """, (now, file_id, user_id, vault_type))

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to securely delete file: {e}")
        raise
    finally:
        conn.close()
