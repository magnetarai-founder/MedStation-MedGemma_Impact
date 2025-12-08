"""
Team Vault Operations (Phase 6.2)

This module manages encrypted storage for sensitive team information.
All content is encrypted at rest using Fernet symmetric encryption.

Vault items can store:
- Patient records
- Medical documents
- Notes and files
- Any sensitive team information

Permission types:
- read: Can view and decrypt vault items
- write: Can create and update vault items
- admin: Can delete vault items and manage permissions

Security features:
- All content encrypted with team-specific keys
- Soft delete for audit trail
- Fine-grained permission control
- Founder Rights override

Examples:
    # Create encrypted vault item
    success, msg, item_id = create_vault_item(
        team_id="MEDICALMISSION-A7B3C",
        item_name="Patient Record #123",
        item_type="patient_record",
        content="Sensitive medical data...",
        created_by="user123",
        mime_type="text/plain"
    )

    # Grant read access to doctors
    add_vault_permission(
        item_id=item_id,
        team_id="MEDICALMISSION-A7B3C",
        permission_type="read",
        grant_type="job_role",
        grant_value="doctor",
        created_by="user123"
    )
"""

import sqlite3
import logging
import hashlib
import uuid
import base64
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from cryptography.fernet import Fernet

from . import storage
from . import founder_rights as founder_mod

logger = logging.getLogger(__name__)


def _get_vault_encryption_key(team_id: str) -> bytes:
    """
    Get or generate encryption key for team vault.

    In production, this should use a proper key management system (KMS).
    For now, we derive a key from team_id for consistency.

    Args:
        team_id: Team ID

    Returns:
        32-byte Fernet-compatible encryption key
    """
    # Derive a consistent key from team_id
    key_material = hashlib.sha256(f"elohimos_vault_{team_id}".encode()).digest()
    # Fernet requires 32 url-safe base64-encoded bytes
    key = base64.urlsafe_b64encode(key_material)
    return key


def _encrypt_content(content: str, team_id: str) -> Tuple[str, str]:
    """
    Encrypt vault content using Fernet symmetric encryption.

    Args:
        content: Plain text content to encrypt
        team_id: Team ID (used for key derivation)

    Returns:
        Tuple of (encrypted_content: str, key_hash: str)

    Raises:
        Exception: If encryption fails
    """
    try:
        key = _get_vault_encryption_key(team_id)
        fernet = Fernet(key)

        # Encrypt content
        encrypted = fernet.encrypt(content.encode())
        encrypted_b64 = encrypted.decode()

        # Create key hash for verification
        key_hash = hashlib.sha256(key).hexdigest()

        return encrypted_b64, key_hash

    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise


def _decrypt_content(encrypted_content: str, team_id: str) -> str:
    """
    Decrypt vault content.

    Args:
        encrypted_content: Base64-encoded encrypted content
        team_id: Team ID (used for key derivation)

    Returns:
        Decrypted plain text content

    Raises:
        Exception: If decryption fails
    """
    try:
        key = _get_vault_encryption_key(team_id)
        fernet = Fernet(key)

        # Decrypt content
        decrypted = fernet.decrypt(encrypted_content.encode())
        return decrypted.decode()

    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise


def create_vault_item(
    team_id: str,
    item_name: str,
    item_type: str,
    content: str,
    created_by: str,
    mime_type: Optional[str] = None,
    metadata: Optional[str] = None
) -> Tuple[bool, str, str]:
    """
    Create a new encrypted vault item.

    Args:
        team_id: Team ID
        item_name: Name of the item
        item_type: Type (document, image, file, note, patient_record, etc.)
        content: Content to encrypt and store
        created_by: User ID creating the item
        mime_type: MIME type if applicable (optional)
        metadata: JSON metadata string (optional)

    Returns:
        Tuple of (success: bool, message: str, item_id: str)

    Examples:
        >>> create_vault_item(
        ...     "TEAM-ABC",
        ...     "Patient Record",
        ...     "patient_record",
        ...     "Medical history...",
        ...     "user1"
        ... )
        (True, "Vault item created successfully", "A1B2C3D4")
    """
    try:
        conn = storage.get_db_connection()
        cursor = conn.cursor()

        # Generate unique item ID
        item_id = str(uuid.uuid4()).upper()[:8]

        # Encrypt content
        encrypted_content, key_hash = _encrypt_content(content, team_id)

        # Calculate file size
        file_size = len(content.encode())

        # Insert vault item
        cursor.execute("""
            INSERT INTO team_vault_items (
                item_id, team_id, item_name, item_type,
                encrypted_content, encryption_key_hash,
                file_size, mime_type, created_by, metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item_id, team_id, item_name, item_type,
            encrypted_content, key_hash,
            file_size, mime_type, created_by, metadata
        ))

        conn.commit()
        conn.close()

        logger.info(f"Created vault item {item_id} for team {team_id}")
        return True, "Vault item created successfully", item_id

    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to create vault item: {e}")
        return False, str(e), ""


def update_vault_item(
    item_id: str,
    team_id: str,
    content: str,
    updated_by: str
) -> Tuple[bool, str]:
    """
    Update vault item content with new encrypted data.

    Args:
        item_id: Item ID
        team_id: Team ID
        content: New content
        updated_by: User ID updating

    Returns:
        Tuple of (success: bool, message: str)

    Examples:
        >>> update_vault_item("A1B2C3D4", "TEAM-ABC", "Updated content", "user1")
        (True, "Vault item updated successfully")
    """
    try:
        conn = storage.get_db_connection()
        cursor = conn.cursor()

        # Check if item exists and not deleted
        cursor.execute("""
            SELECT id FROM team_vault_items
            WHERE item_id = ? AND team_id = ? AND is_deleted = 0
        """, (item_id, team_id))

        if not cursor.fetchone():
            conn.close()
            return False, "Vault item not found or deleted"

        # Encrypt new content
        encrypted_content, key_hash = _encrypt_content(content, team_id)

        # Calculate new file size
        file_size = len(content.encode())

        # Update item
        cursor.execute("""
            UPDATE team_vault_items
            SET encrypted_content = ?,
                encryption_key_hash = ?,
                file_size = ?,
                updated_at = ?,
                updated_by = ?
            WHERE item_id = ? AND team_id = ?
        """, (
            encrypted_content, key_hash, file_size,
            datetime.now().isoformat(), updated_by,
            item_id, team_id
        ))

        conn.commit()
        conn.close()

        logger.info(f"Updated vault item {item_id}")
        return True, "Vault item updated successfully"

    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to update vault item: {e}")
        return False, str(e)


def delete_vault_item(
    item_id: str,
    team_id: str,
    deleted_by: str
) -> Tuple[bool, str]:
    """
    Soft delete vault item (maintains audit trail).

    Args:
        item_id: Item ID
        team_id: Team ID
        deleted_by: User ID deleting

    Returns:
        Tuple of (success: bool, message: str)

    Examples:
        >>> delete_vault_item("A1B2C3D4", "TEAM-ABC", "user1")
        (True, "Vault item deleted successfully")
    """
    try:
        conn = storage.get_db_connection()
        cursor = conn.cursor()

        # Soft delete
        cursor.execute("""
            UPDATE team_vault_items
            SET is_deleted = 1,
                deleted_at = ?,
                deleted_by = ?
            WHERE item_id = ? AND team_id = ? AND is_deleted = 0
        """, (datetime.now().isoformat(), deleted_by, item_id, team_id))

        rowcount = cursor.rowcount
        conn.commit()
        conn.close()

        if rowcount == 0:
            return False, "Vault item not found or already deleted"

        logger.info(f"Deleted vault item {item_id}")
        return True, "Vault item deleted successfully"

    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to delete vault item: {e}")
        return False, str(e)


def get_vault_item(
    item_id: str,
    team_id: str,
    decrypt: bool = True
) -> Optional[Dict]:
    """
    Get vault item and optionally decrypt its content.

    Args:
        item_id: Item ID
        team_id: Team ID
        decrypt: Whether to decrypt content (default: True)

    Returns:
        Dict with item details or None if not found

    Examples:
        >>> get_vault_item("A1B2C3D4", "TEAM-ABC")
        {
            'item_id': 'A1B2C3D4',
            'item_name': 'Patient Record',
            'item_type': 'patient_record',
            'content': 'Decrypted medical history...',
            'file_size': 1024,
            'created_at': '2025-01-01 12:00:00',
            'created_by': 'user1'
        }
    """
    try:
        conn = storage.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT item_id, team_id, item_name, item_type,
                   encrypted_content, file_size, mime_type,
                   created_at, created_by, updated_at, updated_by,
                   metadata
            FROM team_vault_items
            WHERE item_id = ? AND team_id = ? AND is_deleted = 0
        """, (item_id, team_id))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        item = dict(row)

        # Decrypt content if requested
        if decrypt and item['encrypted_content']:
            try:
                item['content'] = _decrypt_content(item['encrypted_content'], team_id)
                del item['encrypted_content']
            except Exception as e:
                logger.error(f"Failed to decrypt vault item {item_id}: {e}")
                item['content'] = "[DECRYPTION ERROR]"
                del item['encrypted_content']

        return item

    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to get vault item: {e}")
        return None


def list_vault_items(
    team_id: str,
    user_id: str,
    item_type: Optional[str] = None,
    include_deleted: bool = False
) -> List[Dict]:
    """
    List vault items accessible to user (without decrypted content).

    Args:
        team_id: Team ID
        user_id: User ID requesting
        item_type: Filter by item type (optional)
        include_deleted: Include soft-deleted items (default: False)

    Returns:
        List of vault items (metadata only, no decrypted content)

    Examples:
        >>> list_vault_items("TEAM-ABC", "user1", item_type="patient_record")
        [
            {
                'item_id': 'A1B2C3D4',
                'item_name': 'Patient Record #123',
                'item_type': 'patient_record',
                'file_size': 1024,
                'created_at': '2025-01-01 12:00:00',
                'created_by': 'user1'
            }
        ]
    """
    try:
        conn = storage.get_db_connection()
        cursor = conn.cursor()

        # Build query
        query = """
            SELECT item_id, item_name, item_type, file_size, mime_type,
                   created_at, created_by, updated_at, updated_by, metadata
            FROM team_vault_items
            WHERE team_id = ?
        """
        params = [team_id]

        if not include_deleted:
            query += " AND is_deleted = 0"

        if item_type:
            query += " AND item_type = ?"
            params.append(item_type)

        query += " ORDER BY created_at DESC"

        cursor.execute(query, params)

        items = []
        for row in cursor.fetchall():
            # Check if user has permission to view
            can_view, _ = check_vault_permission(
                item_id=row['item_id'],
                team_id=team_id,
                user_id=user_id,
                permission_type='read'
            )

            if can_view:
                items.append(dict(row))

        conn.close()
        return items

    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to list vault items: {e}")
        return []


def check_vault_permission(
    item_id: str,
    team_id: str,
    user_id: str,
    permission_type: str
) -> Tuple[bool, str]:
    """
    Check if user has vault item permission.

    Permission priority: Founder Rights > explicit user > job_role > role > defaults

    Default permissions:
    - READ: member and above
    - WRITE: admin and above
    - ADMIN: admin and above

    Args:
        item_id: Item ID
        team_id: Team ID
        user_id: User ID
        permission_type: Permission type (read, write, admin)

    Returns:
        Tuple of (has_permission: bool, reason: str)

    Examples:
        >>> check_vault_permission("A1B2C3D4", "TEAM-ABC", "user1", "read")
        (True, "Job role permission (doctor)")
    """
    try:
        conn = storage.get_db_connection()
        cursor = conn.cursor()

        # Check Founder Rights
        has_god_rights, _ = founder_mod.check_god_rights(user_id)
        if has_god_rights:
            conn.close()
            return True, "Founder Rights override"

        # Get user's role and job_role
        cursor.execute("""
            SELECT role, job_role FROM team_members
            WHERE team_id = ? AND user_id = ?
        """, (team_id, user_id))

        member = cursor.fetchone()
        if not member:
            conn.close()
            return False, "User not a member of team"

        user_role = member['role']
        user_job_role = member['job_role'] or 'unassigned'

        # Check explicit user permission
        cursor.execute("""
            SELECT permission_type FROM team_vault_permissions
            WHERE item_id = ? AND team_id = ? AND grant_type = 'user' AND grant_value = ?
        """, (item_id, team_id, user_id))

        user_perms = [row['permission_type'] for row in cursor.fetchall()]
        if permission_type in user_perms:
            conn.close()
            return True, "Explicit user permission"

        # Check job_role permission
        cursor.execute("""
            SELECT permission_type FROM team_vault_permissions
            WHERE item_id = ? AND team_id = ? AND grant_type = 'job_role' AND grant_value = ?
        """, (item_id, team_id, user_job_role))

        job_perms = [row['permission_type'] for row in cursor.fetchall()]
        if permission_type in job_perms:
            conn.close()
            return True, f"Job role permission ({user_job_role})"

        # Check role permission
        cursor.execute("""
            SELECT permission_type FROM team_vault_permissions
            WHERE item_id = ? AND team_id = ? AND grant_type = 'role' AND grant_value = ?
        """, (item_id, team_id, user_role))

        role_perms = [row['permission_type'] for row in cursor.fetchall()]
        if permission_type in role_perms:
            conn.close()
            return True, f"Role permission ({user_role})"

        # Default permissions
        # READ: member+, WRITE/ADMIN: admin+
        conn.close()
        if permission_type == 'read':
            if user_role in ['member', 'admin', 'super_admin']:
                return True, f"Default read permission for {user_role}"
        elif permission_type in ['write', 'admin']:
            if user_role in ['admin', 'super_admin']:
                return True, f"Default {permission_type} permission for {user_role}"

        return False, "No permission granted"

    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to check vault permission: {e}")
        return False, str(e)


def add_vault_permission(
    item_id: str,
    team_id: str,
    permission_type: str,
    grant_type: str,
    grant_value: str,
    created_by: str
) -> Tuple[bool, str]:
    """
    Add vault item permission.

    Args:
        item_id: Item ID
        team_id: Team ID
        permission_type: Permission type (read, write, admin)
        grant_type: Grant type (role, job_role, user)
        grant_value: Grant value
        created_by: User ID creating permission

    Returns:
        Tuple of (success: bool, message: str)

    Examples:
        >>> add_vault_permission(
        ...     "A1B2C3D4",
        ...     "TEAM-ABC",
        ...     "read",
        ...     "job_role",
        ...     "doctor",
        ...     "user1"
        ... )
        (True, "Permission added successfully")
    """
    try:
        # Validate permission type
        if permission_type not in ['read', 'write', 'admin']:
            return False, "Invalid permission type. Must be: read, write, admin"

        # Validate grant type
        if grant_type not in ['role', 'job_role', 'user']:
            return False, "Invalid grant type. Must be: role, job_role, user"

        conn = storage.get_db_connection()
        cursor = conn.cursor()

        # Check if permission already exists
        cursor.execute("""
            SELECT id FROM team_vault_permissions
            WHERE item_id = ? AND team_id = ? AND permission_type = ?
              AND grant_type = ? AND grant_value = ?
        """, (item_id, team_id, permission_type, grant_type, grant_value))

        if cursor.fetchone():
            conn.close()
            return False, "Permission already exists"

        # Add permission
        cursor.execute("""
            INSERT INTO team_vault_permissions (
                item_id, team_id, permission_type,
                grant_type, grant_value, created_by
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (item_id, team_id, permission_type, grant_type, grant_value, created_by))

        conn.commit()
        conn.close()

        logger.info(f"Added {permission_type} permission for {grant_type}:{grant_value} to item {item_id}")
        return True, "Permission added successfully"

    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to add vault permission: {e}")
        return False, str(e)


def remove_vault_permission(
    item_id: str,
    team_id: str,
    permission_type: str,
    grant_type: str,
    grant_value: str
) -> Tuple[bool, str]:
    """
    Remove vault item permission.

    Args:
        item_id: Item ID
        team_id: Team ID
        permission_type: Permission type
        grant_type: Grant type
        grant_value: Grant value

    Returns:
        Tuple of (success: bool, message: str)

    Examples:
        >>> remove_vault_permission(
        ...     "A1B2C3D4",
        ...     "TEAM-ABC",
        ...     "read",
        ...     "job_role",
        ...     "doctor"
        ... )
        (True, "Permission removed successfully")
    """
    try:
        conn = storage.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM team_vault_permissions
            WHERE item_id = ? AND team_id = ? AND permission_type = ?
              AND grant_type = ? AND grant_value = ?
        """, (item_id, team_id, permission_type, grant_type, grant_value))

        rowcount = cursor.rowcount
        conn.commit()
        conn.close()

        if rowcount == 0:
            return False, "Permission not found"

        logger.info(f"Removed {permission_type} permission for {grant_type}:{grant_value} from item {item_id}")
        return True, "Permission removed successfully"

    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to remove vault permission: {e}")
        return False, str(e)


def get_vault_permissions(
    item_id: str,
    team_id: str
) -> List[Dict]:
    """
    Get all permissions for a vault item.

    Args:
        item_id: Item ID
        team_id: Team ID

    Returns:
        List of permission grants

    Examples:
        >>> get_vault_permissions("A1B2C3D4", "TEAM-ABC")
        [
            {
                'permission_type': 'read',
                'grant_type': 'job_role',
                'grant_value': 'doctor',
                'created_at': '2025-01-01 12:00:00',
                'created_by': 'user1'
            }
        ]
    """
    try:
        conn = storage.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT permission_type, grant_type, grant_value, created_at, created_by
            FROM team_vault_permissions
            WHERE item_id = ? AND team_id = ?
            ORDER BY created_at DESC
        """, (item_id, team_id))

        permissions = []
        for row in cursor.fetchall():
            permissions.append(dict(row))

        conn.close()
        return permissions

    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to get vault permissions: {e}")
        return []
