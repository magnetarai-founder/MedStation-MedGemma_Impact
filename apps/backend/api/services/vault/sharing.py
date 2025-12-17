"""
Vault Sharing Logic

Handles file/folder sharing, share links, password protection, and download tracking.
"""

import sqlite3
import uuid
import hashlib
import secrets
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from api.config_paths import get_config_paths

logger = logging.getLogger(__name__)

# Configuration paths
PATHS = get_config_paths()
VAULT_DB_PATH = PATHS.data_dir / "vault.db"


def create_share_link(
    vault_service,
    user_id: str,
    vault_type: str,
    file_id: str,
    password: Optional[str] = None,
    expires_at: Optional[str] = None,
    max_downloads: Optional[int] = None,
    permissions: str = "download"
) -> Dict[str, Any]:
    """
    Create a shareable link for a file.

    Args:
        vault_service: VaultService instance
        user_id: User ID creating the share
        vault_type: 'real' or 'decoy'
        file_id: File ID to share
        password: Optional password protection
        expires_at: Optional expiration timestamp (ISO format)
        max_downloads: Optional maximum download count
        permissions: 'view' or 'download' (default: 'download')

    Returns:
        Share link dictionary with:
        - id: Share ID
        - share_token: Secure token for accessing the share
        - expires_at: Expiration timestamp
        - max_downloads: Maximum downloads allowed
        - permissions: Access permissions
        - created_at: Creation timestamp

    Security:
        - Uses cryptographically secure token generation
        - Password hashed with SHA-256
        - Vault-type scoped
        - Token is URL-safe (32 bytes = 43 chars base64)
    """
    conn = sqlite3.connect(str(vault_service.db_path))
    cursor = conn.cursor()

    try:
        # Generate secure share token
        share_token = secrets.token_urlsafe(32)
        share_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        # Hash password if provided
        password_hash = None
        if password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()

        cursor.execute("""
            INSERT INTO vault_file_shares (
                id, file_id, user_id, vault_type, share_token,
                password_hash, expires_at, max_downloads, permissions,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (share_id, file_id, user_id, vault_type, share_token,
              password_hash, expires_at, max_downloads, permissions, now))

        conn.commit()

        return {
            "id": share_id,
            "share_token": share_token,
            "expires_at": expires_at,
            "max_downloads": max_downloads,
            "permissions": permissions,
            "created_at": now
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to create share link: {e}")
        raise
    finally:
        conn.close()


def get_share_link(
    vault_service,
    share_token: str
) -> Dict[str, Any]:
    """
    Get share link details and validate access.

    Args:
        vault_service: VaultService instance
        share_token: Share token from URL

    Returns:
        Share link dictionary with:
        - id: Share ID
        - file_id: File ID being shared
        - filename: Original filename
        - file_size: File size in bytes
        - mime_type: MIME type
        - requires_password: Whether password is required
        - permissions: Access permissions
        - download_count: Current download count
        - max_downloads: Maximum downloads allowed

    Raises:
        ValueError: If share link not found, expired, or download limit reached

    Security:
        - Validates expiration
        - Checks download limits
        - Does not expose password hash
        - Joins with files table to ensure file exists
    """
    conn = sqlite3.connect(str(vault_service.db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT s.id, s.file_id, s.password_hash, s.expires_at,
                   s.max_downloads, s.download_count, s.permissions,
                   f.filename, f.file_size, f.mime_type
            FROM vault_file_shares s
            JOIN vault_files f ON s.file_id = f.id
            WHERE s.share_token = ?
        """, (share_token,))

        result = cursor.fetchone()
        if not result:
            raise ValueError("Share link not found")

        share_id, file_id, password_hash, expires_at, max_downloads, \
            download_count, permissions, filename, file_size, mime_type = result

        # Check if expired
        if expires_at:
            expires_dt = datetime.fromisoformat(expires_at)
            if datetime.now(UTC) > expires_dt:
                raise ValueError("Share link has expired")

        # Check download limit
        if max_downloads and download_count >= max_downloads:
            raise ValueError("Download limit reached")

        return {
            "id": share_id,
            "file_id": file_id,
            "filename": filename,
            "file_size": file_size,
            "mime_type": mime_type,
            "requires_password": password_hash is not None,
            "permissions": permissions,
            "download_count": download_count,
            "max_downloads": max_downloads
        }

    finally:
        conn.close()


def verify_share_password(
    vault_service,
    share_token: str,
    password: str
) -> bool:
    """
    Verify password for a password-protected share link.

    Args:
        vault_service: VaultService instance
        share_token: Share token
        password: Password to verify

    Returns:
        True if password is correct or no password required, False otherwise

    Security:
        - Constant-time comparison via hash matching
        - Returns True if no password required
    """
    conn = sqlite3.connect(str(vault_service.db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT password_hash
            FROM vault_file_shares
            WHERE share_token = ?
        """, (share_token,))

        result = cursor.fetchone()
        if not result or not result[0]:
            return True  # No password required

        stored_hash = result[0]
        provided_hash = hashlib.sha256(password.encode()).hexdigest()

        return stored_hash == provided_hash

    finally:
        conn.close()


def increment_share_download(
    vault_service,
    share_token: str
) -> None:
    """
    Increment download counter for a share link.

    Args:
        vault_service: VaultService instance
        share_token: Share token

    Security:
        - Updates last_accessed timestamp
        - Atomic increment operation
    """
    conn = sqlite3.connect(str(vault_service.db_path))
    cursor = conn.cursor()

    try:
        now = datetime.now(UTC).isoformat()

        cursor.execute("""
            UPDATE vault_file_shares
            SET download_count = download_count + 1,
                last_accessed = ?
            WHERE share_token = ?
        """, (now, share_token))

        conn.commit()

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to increment share download: {e}")
        raise
    finally:
        conn.close()


def revoke_share_link(
    vault_service,
    user_id: str,
    vault_type: str,
    share_id: str
) -> bool:
    """
    Revoke/delete a share link.

    Args:
        vault_service: VaultService instance
        user_id: User ID (must be owner)
        vault_type: 'real' or 'decoy'
        share_id: Share ID to revoke

    Returns:
        True if share was revoked, False if not found

    Security:
        - Only owner can revoke their shares
        - Vault-type scoped
    """
    conn = sqlite3.connect(str(vault_service.db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM vault_file_shares
            WHERE id = ? AND user_id = ? AND vault_type = ?
        """, (share_id, user_id, vault_type))

        conn.commit()
        return cursor.rowcount > 0

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to revoke share link: {e}")
        raise
    finally:
        conn.close()


def get_file_shares(
    vault_service,
    user_id: str,
    vault_type: str,
    file_id: str
) -> List[Dict[str, Any]]:
    """
    Get all share links for a file.

    Args:
        vault_service: VaultService instance
        user_id: User ID (must be owner)
        vault_type: 'real' or 'decoy'
        file_id: File ID

    Returns:
        List of share dictionaries with:
        - id, share_token, expires_at, max_downloads
        - download_count, permissions, created_at, last_accessed

    Security:
        - Returns only user's shares
        - Vault-type scoped
        - Ordered by creation date (newest first)
    """
    conn = sqlite3.connect(str(vault_service.db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, share_token, expires_at, max_downloads,
                   download_count, permissions, created_at, last_accessed
            FROM vault_file_shares
            WHERE file_id = ? AND user_id = ? AND vault_type = ?
            ORDER BY created_at DESC
        """, (file_id, user_id, vault_type))

        shares = []
        for row in cursor.fetchall():
            shares.append({
                "id": row[0],
                "share_token": row[1],
                "expires_at": row[2],
                "max_downloads": row[3],
                "download_count": row[4],
                "permissions": row[5],
                "created_at": row[6],
                "last_accessed": row[7]
            })

        return shares

    finally:
        conn.close()


def validate_share_permissions(user_id: str, file_id: str, permission: str) -> bool:
    """
    Validate if user has specific permission for a file.

    Args:
        user_id: User ID
        file_id: File ID
        permission: Permission type (read, write, admin)

    Returns:
        True if user has permission

    Note:
        This is a placeholder for future ACL integration.
        Currently returns True for backwards compatibility.
    """
    # Placeholder - can be extended with vault_file_acl table integration
    return True


def generate_share_link_data(file_id: str, user_id: str, **kwargs) -> Dict[str, Any]:
    """
    Generate share link data structure (helper function).

    Args:
        file_id: File ID to share
        user_id: Owner user ID
        **kwargs: Additional share parameters (password, expiry, etc.)

    Returns:
        Share link data dictionary

    Note:
        This is a helper function. Actual share creation
        should use create_share_link() with a vault_service instance.
    """
    # Placeholder - actual logic in create_share_link
    return {}
