"""
Team Vault Permission Management

Handles permission checks and grants for encrypted vault items.
Fine-grained access control for team vault operations.

Permission types:
- read: Can view and decrypt vault items
- write: Can create and update vault items
- admin: Can delete vault items and manage permissions

Grant types:
- user: Permission for specific user
- role: Permission for team role (member, admin, super_admin)
- job_role: Permission for job role (doctor, nurse, etc.)

Extracted from vault.py during P2 decomposition.
"""

import logging
from typing import List, Dict, Tuple

from . import storage
from . import founder_rights as founder_mod

logger = logging.getLogger(__name__)


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


__all__ = [
    "check_vault_permission",
    "add_vault_permission",
    "remove_vault_permission",
    "get_vault_permissions",
]
