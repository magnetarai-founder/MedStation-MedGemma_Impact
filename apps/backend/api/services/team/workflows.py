"""
Workflow Permission Management (Phase 5.2)

This module provides workflow-level permission management for teams.
Permissions can be granted based on:
- User-specific grants
- Job role grants (doctor, pastor, nurse, etc.)
- Team role grants (member, admin, super_admin)

Permission types:
- view: Can view workflow
- edit: Can modify workflow
- delete: Can delete workflow
- assign: Can assign workflow to users

Examples:
    # Add permission for doctors to edit a workflow
    success, msg = add_workflow_permission(
        workflow_id="WORKFLOW-123",
        team_id="MEDICALMISSION-A7B3C",
        permission_type="edit",
        grant_type="job_role",
        grant_value="doctor",
        created_by="user123"
    )

    # Check if user has permission
    can_edit, reason = check_workflow_permission(
        workflow_id="WORKFLOW-123",
        team_id="MEDICALMISSION-A7B3C",
        user_id="user456",
        permission_type="edit"
    )
"""

import sqlite3
import logging
from typing import List, Dict, Tuple

from . import storage

logger = logging.getLogger(__name__)


def add_workflow_permission(
    workflow_id: str,
    team_id: str,
    permission_type: str,
    grant_type: str,
    grant_value: str,
    created_by: str
) -> Tuple[bool, str]:
    """
    Add a workflow permission grant.

    Args:
        workflow_id: Workflow ID
        team_id: Team ID
        permission_type: 'view', 'edit', 'delete', 'assign'
        grant_type: 'role', 'job_role', 'user'
        grant_value: Depends on grant_type (role name, job role, or user_id)
        created_by: User ID who created this permission

    Returns:
        Tuple of (success: bool, message: str)

    Examples:
        >>> # Grant view permission to all members
        >>> add_workflow_permission("WF-123", "TEAM-ABC", "view", "role", "member", "user1")
        (True, "Permission granted: role=member can view")

        >>> # Grant edit permission to doctors
        >>> add_workflow_permission("WF-123", "TEAM-ABC", "edit", "job_role", "doctor", "user1")
        (True, "Permission granted: job_role=doctor can edit")
    """
    valid_permission_types = ['view', 'edit', 'delete', 'assign']
    valid_grant_types = ['role', 'job_role', 'user']

    if permission_type not in valid_permission_types:
        return False, f"Invalid permission type. Must be one of: {', '.join(valid_permission_types)}"

    if grant_type not in valid_grant_types:
        return False, f"Invalid grant type. Must be one of: {', '.join(valid_grant_types)}"

    try:
        conn = storage.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO workflow_permissions (workflow_id, team_id, permission_type, grant_type, grant_value, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (workflow_id, team_id, permission_type, grant_type, grant_value, created_by))

        conn.commit()
        conn.close()

        logger.info(f"Added {permission_type} permission for workflow {workflow_id}: {grant_type}={grant_value}")

        return True, f"Permission granted: {grant_type}={grant_value} can {permission_type}"

    except sqlite3.IntegrityError:
        if conn:
            conn.close()
        return False, "Permission already exists"
    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to add workflow permission: {e}")
        return False, str(e)


def remove_workflow_permission(
    workflow_id: str,
    team_id: str,
    permission_type: str,
    grant_type: str,
    grant_value: str
) -> Tuple[bool, str]:
    """
    Remove a workflow permission grant.

    Args:
        workflow_id: Workflow ID
        team_id: Team ID
        permission_type: 'view', 'edit', 'delete', 'assign'
        grant_type: 'role', 'job_role', 'user'
        grant_value: Depends on grant_type

    Returns:
        Tuple of (success: bool, message: str)

    Examples:
        >>> remove_workflow_permission("WF-123", "TEAM-ABC", "edit", "job_role", "doctor")
        (True, "Permission revoked: job_role=doctor can no longer edit")
    """
    try:
        conn = storage.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM workflow_permissions
            WHERE workflow_id = ? AND team_id = ? AND permission_type = ? AND grant_type = ? AND grant_value = ?
        """, (workflow_id, team_id, permission_type, grant_type, grant_value))

        conn.commit()
        rowcount = cursor.rowcount
        conn.close()

        if rowcount == 0:
            return False, "Permission not found"

        logger.info(f"Removed {permission_type} permission for workflow {workflow_id}: {grant_type}={grant_value}")

        return True, f"Permission revoked: {grant_type}={grant_value} can no longer {permission_type}"

    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to remove workflow permission: {e}")
        return False, str(e)


def check_workflow_permission(
    workflow_id: str,
    team_id: str,
    user_id: str,
    permission_type: str
) -> Tuple[bool, str]:
    """
    Check if a user has a specific workflow permission.

    Checks in priority order:
    1. Founder Rights always have all permissions
    2. Explicit user grants
    3. Job role grants
    4. Role grants
    5. Default permissions (if no explicit permissions exist)

    Args:
        workflow_id: Workflow ID
        team_id: Team ID
        user_id: User ID to check
        permission_type: 'view', 'edit', 'delete', 'assign'

    Returns:
        Tuple of (has_permission: bool, reason: str)

    Examples:
        >>> check_workflow_permission("WF-123", "TEAM-ABC", "user1", "edit")
        (True, "Job role grant (doctor)")
    """
    try:
        conn = storage.get_db_connection()
        cursor = conn.cursor()

        # Get user's role and job_role
        cursor.execute("""
            SELECT role, job_role FROM team_members
            WHERE team_id = ? AND user_id = ?
        """, (team_id, user_id))

        member = cursor.fetchone()
        if not member:
            conn.close()
            return False, "User not found in team"

        user_role = member['role']
        user_job_role = member['job_role'] or 'unassigned'

        # Founder Rights always have all permissions
        if user_role == 'god_rights':
            conn.close()
            return True, "Founder Rights override"

        # Check if any explicit permissions exist for this workflow
        cursor.execute("""
            SELECT COUNT(*) as count FROM workflow_permissions
            WHERE workflow_id = ? AND team_id = ?
        """, (workflow_id, team_id))

        has_explicit_perms = cursor.fetchone()['count'] > 0

        if has_explicit_perms:
            # Check explicit permissions in order: user > job_role > role
            cursor.execute("""
                SELECT grant_type, grant_value FROM workflow_permissions
                WHERE workflow_id = ? AND team_id = ? AND permission_type = ?
            """, (workflow_id, team_id, permission_type))

            grants = cursor.fetchall()

            for grant in grants:
                if grant['grant_type'] == 'user' and grant['grant_value'] == user_id:
                    conn.close()
                    return True, "Explicit user grant"
                if grant['grant_type'] == 'job_role' and grant['grant_value'] == user_job_role:
                    conn.close()
                    return True, f"Job role grant ({user_job_role})"
                if grant['grant_type'] == 'role' and grant['grant_value'] == user_role:
                    conn.close()
                    return True, f"Role grant ({user_role})"

            conn.close()
            return False, "No matching permission grant found"

        else:
            # Use default permissions
            conn.close()
            return _check_default_permission(user_role, permission_type)

    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to check workflow permission: {e}")
        return False, str(e)


def _check_default_permission(user_role: str, permission_type: str) -> Tuple[bool, str]:
    """
    Check default permissions when no explicit grants exist.

    Default permissions:
    - VIEW: member and above
    - EDIT: admin and above
    - DELETE: super_admin and above
    - ASSIGN: admin and above

    Args:
        user_role: User's role
        permission_type: Permission to check

    Returns:
        Tuple of (has_permission: bool, reason: str)
    """
    role_hierarchy = {
        'guest': 0,
        'member': 1,
        'admin': 2,
        'super_admin': 3,
        'god_rights': 4
    }

    user_level = role_hierarchy.get(user_role, 0)

    if permission_type == 'view':
        required_level = role_hierarchy['member']
        if user_level >= required_level:
            return True, "Default: members can view"
        return False, "Default: only members and above can view"

    elif permission_type == 'edit':
        required_level = role_hierarchy['admin']
        if user_level >= required_level:
            return True, "Default: admins can edit"
        return False, "Default: only admins and above can edit"

    elif permission_type == 'delete':
        required_level = role_hierarchy['super_admin']
        if user_level >= required_level:
            return True, "Default: super admins can delete"
        return False, "Default: only super admins and above can delete"

    elif permission_type == 'assign':
        required_level = role_hierarchy['admin']
        if user_level >= required_level:
            return True, "Default: admins can assign"
        return False, "Default: only admins and above can assign"

    else:
        return False, f"Unknown permission type: {permission_type}"


def get_workflow_permissions(workflow_id: str, team_id: str) -> List[Dict]:
    """
    Get all permission grants for a workflow.

    Args:
        workflow_id: Workflow ID
        team_id: Team ID

    Returns:
        List of permission grants

    Examples:
        >>> get_workflow_permissions("WF-123", "TEAM-ABC")
        [
            {
                'permission_type': 'view',
                'grant_type': 'role',
                'grant_value': 'member',
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
            FROM workflow_permissions
            WHERE workflow_id = ? AND team_id = ?
            ORDER BY permission_type, grant_type, grant_value
        """, (workflow_id, team_id))

        permissions = []
        for row in cursor.fetchall():
            permissions.append({
                'permission_type': row['permission_type'],
                'grant_type': row['grant_type'],
                'grant_value': row['grant_value'],
                'created_at': row['created_at'],
                'created_by': row['created_by']
            })

        conn.close()
        return permissions

    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to get workflow permissions: {e}")
        return []
