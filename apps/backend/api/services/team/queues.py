"""
Queue Access Control Management (Phase 5.3)

This module manages queue creation and access control for team operations.
Queues are used for managing patient flow, medication requests, counseling appointments, etc.

Queue types: patient, medication, pharmacy, counseling, etc.
Access types:
- view: Can see queue contents
- manage: Can modify queue settings
- assign: Can assign items to queue

Permissions can be granted based on:
- User-specific grants
- Job role grants (doctor, pastor, nurse, etc.)
- Team role grants (member, admin, super_admin)

Examples:
    # Create a patient queue
    success, msg, queue_id = create_queue(
        team_id="MEDICALMISSION-A7B3C",
        queue_name="Triage Queue",
        queue_type="patient",
        description="Initial patient triage",
        created_by="user123"
    )

    # Grant view access to nurses
    add_queue_permission(
        queue_id=queue_id,
        team_id="MEDICALMISSION-A7B3C",
        access_type="view",
        grant_type="job_role",
        grant_value="nurse",
        created_by="user123"
    )
"""

import sqlite3
import logging
import uuid
from typing import List, Dict, Tuple, Optional

from . import storage

logger = logging.getLogger(__name__)


def create_queue(
    team_id: str,
    queue_name: str,
    queue_type: str,
    description: str,
    created_by: str
) -> Tuple[bool, str, str]:
    """
    Create a new queue.

    Args:
        team_id: Team ID
        queue_name: Display name for the queue
        queue_type: Type of queue (patient, medication, pharmacy, counseling, etc.)
        description: Description of the queue's purpose
        created_by: User ID who created the queue

    Returns:
        Tuple of (success: bool, message: str, queue_id: str)

    Examples:
        >>> create_queue("TEAM-ABC", "Triage", "patient", "Initial assessment", "user1")
        (True, "Queue 'Triage' created successfully", "PATIENT-A1B2C3D4")
    """
    try:
        # Generate unique queue ID
        queue_id = f"{queue_type.upper()}-{uuid.uuid4().hex[:8].upper()}"

        conn = storage.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO queues (queue_id, team_id, queue_name, queue_type, description, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (queue_id, team_id, queue_name, queue_type, description, created_by))

        conn.commit()
        conn.close()

        logger.info(f"Created queue {queue_id} ({queue_name}) in team {team_id}")

        return True, f"Queue '{queue_name}' created successfully", queue_id

    except sqlite3.IntegrityError:
        if conn:
            conn.close()
        return False, "Queue already exists", ""
    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to create queue: {e}")
        return False, str(e), ""


def add_queue_permission(
    queue_id: str,
    team_id: str,
    access_type: str,
    grant_type: str,
    grant_value: str,
    created_by: str
) -> Tuple[bool, str]:
    """
    Add queue access permission.

    Args:
        queue_id: Queue ID
        team_id: Team ID
        access_type: 'view', 'manage', 'assign'
        grant_type: 'role', 'job_role', 'user'
        grant_value: Depends on grant_type (role name, job role, or user_id)
        created_by: User ID who created this permission

    Returns:
        Tuple of (success: bool, message: str)

    Examples:
        >>> add_queue_permission("PATIENT-ABC", "TEAM-123", "view", "job_role", "nurse", "user1")
        (True, "Access granted: job_role=nurse can view")
    """
    valid_access_types = ['view', 'manage', 'assign']
    valid_grant_types = ['role', 'job_role', 'user']

    if access_type not in valid_access_types:
        return False, f"Invalid access type. Must be one of: {', '.join(valid_access_types)}"

    if grant_type not in valid_grant_types:
        return False, f"Invalid grant type. Must be one of: {', '.join(valid_grant_types)}"

    try:
        conn = storage.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO queue_permissions (queue_id, team_id, access_type, grant_type, grant_value, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (queue_id, team_id, access_type, grant_type, grant_value, created_by))

        conn.commit()
        conn.close()

        logger.info(f"Added {access_type} access for queue {queue_id}: {grant_type}={grant_value}")

        return True, f"Access granted: {grant_type}={grant_value} can {access_type}"

    except sqlite3.IntegrityError:
        if conn:
            conn.close()
        return False, "Permission already exists"
    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to add queue permission: {e}")
        return False, str(e)


def remove_queue_permission(
    queue_id: str,
    team_id: str,
    access_type: str,
    grant_type: str,
    grant_value: str
) -> Tuple[bool, str]:
    """
    Remove queue access permission.

    Args:
        queue_id: Queue ID
        team_id: Team ID
        access_type: 'view', 'manage', 'assign'
        grant_type: 'role', 'job_role', 'user'
        grant_value: Depends on grant_type

    Returns:
        Tuple of (success: bool, message: str)

    Examples:
        >>> remove_queue_permission("PATIENT-ABC", "TEAM-123", "view", "job_role", "nurse")
        (True, "Access revoked: job_role=nurse can no longer view")
    """
    try:
        conn = storage.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM queue_permissions
            WHERE queue_id = ? AND team_id = ? AND access_type = ? AND grant_type = ? AND grant_value = ?
        """, (queue_id, team_id, access_type, grant_type, grant_value))

        conn.commit()
        rowcount = cursor.rowcount
        conn.close()

        if rowcount == 0:
            return False, "Permission not found"

        logger.info(f"Removed {access_type} access for queue {queue_id}: {grant_type}={grant_value}")

        return True, f"Access revoked: {grant_type}={grant_value} can no longer {access_type}"

    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to remove queue permission: {e}")
        return False, str(e)


def check_queue_access(
    queue_id: str,
    team_id: str,
    user_id: str,
    access_type: str
) -> Tuple[bool, str]:
    """
    Check if a user has access to a queue.

    Checks in priority order:
    1. Founder Rights always have all access
    2. Explicit user grants
    3. Job role grants
    4. Role grants
    5. Default permissions (admins+ can manage, members+ can view)

    Args:
        queue_id: Queue ID
        team_id: Team ID
        user_id: User ID to check
        access_type: 'view', 'manage', 'assign'

    Returns:
        Tuple of (has_access: bool, reason: str)

    Examples:
        >>> check_queue_access("PATIENT-ABC", "TEAM-123", "user1", "view")
        (True, "Job role (nurse) view access")
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

        # Founder Rights always have all access
        if user_role == 'god_rights':
            conn.close()
            return True, "Founder Rights override"

        # Check for explicit user grant
        cursor.execute("""
            SELECT 1 FROM queue_permissions
            WHERE queue_id = ? AND team_id = ? AND access_type = ? AND grant_type = 'user' AND grant_value = ?
        """, (queue_id, team_id, access_type, user_id))

        if cursor.fetchone():
            conn.close()
            return True, f"User-specific {access_type} access"

        # Check for job role grant
        cursor.execute("""
            SELECT 1 FROM queue_permissions
            WHERE queue_id = ? AND team_id = ? AND access_type = ? AND grant_type = 'job_role' AND grant_value = ?
        """, (queue_id, team_id, access_type, user_job_role))

        if cursor.fetchone():
            conn.close()
            return True, f"Job role ({user_job_role}) {access_type} access"

        # Check for role grant
        cursor.execute("""
            SELECT 1 FROM queue_permissions
            WHERE queue_id = ? AND team_id = ? AND access_type = ? AND grant_type = 'role' AND grant_value = ?
        """, (queue_id, team_id, access_type, user_role))

        if cursor.fetchone():
            conn.close()
            return True, f"Role ({user_role}) {access_type} access"

        # Check if there are any explicit permissions defined for this queue
        cursor.execute("""
            SELECT COUNT(*) as count FROM queue_permissions
            WHERE queue_id = ? AND team_id = ? AND access_type = ?
        """, (queue_id, team_id, access_type))

        has_explicit_permissions = cursor.fetchone()['count'] > 0

        # If no explicit permissions, apply defaults
        if not has_explicit_permissions:
            result = _check_default_queue_access(user_role, access_type)
            conn.close()
            return result

        # Explicit permissions exist but user doesn't match any
        conn.close()
        return False, "No matching access grants"

    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to check queue access: {e}")
        return False, str(e)


def _check_default_queue_access(user_role: str, access_type: str) -> Tuple[bool, str]:
    """
    Default queue access permissions.

    Defaults when no explicit permissions are set:
    - VIEW: member and above
    - MANAGE: admin and above
    - ASSIGN: admin and above

    Args:
        user_role: User's role
        access_type: Access type to check

    Returns:
        Tuple of (has_access: bool, reason: str)
    """
    role_hierarchy = {
        'guest': 0,
        'member': 1,
        'admin': 2,
        'super_admin': 3,
        'god_rights': 4
    }

    role_level = role_hierarchy.get(user_role, 0)

    if access_type == 'view':
        # Members and above can view
        if role_level >= role_hierarchy['member']:
            return True, f"Default view access for {user_role}"
        return False, "Guests cannot view queues by default"

    elif access_type in ['manage', 'assign']:
        # Admins and above can manage/assign
        if role_level >= role_hierarchy['admin']:
            return True, f"Default {access_type} access for {user_role}"
        return False, f"Only admins and above can {access_type} by default"

    return False, f"Invalid access type: {access_type}"


def get_accessible_queues(
    team_id: str,
    user_id: str,
    access_type: str = 'view'
) -> List[Dict]:
    """
    Get all queues a user can access.

    Args:
        team_id: Team ID
        user_id: User ID
        access_type: 'view', 'manage', or 'assign' (default: 'view')

    Returns:
        List of accessible queues with details

    Examples:
        >>> get_accessible_queues("TEAM-ABC", "user1", "view")
        [
            {
                'queue_id': 'PATIENT-123',
                'queue_name': 'Triage',
                'queue_type': 'patient',
                'description': 'Initial assessment',
                'created_at': '2025-01-01 12:00:00',
                'created_by': 'user1',
                'access_reason': 'Job role (nurse) view access'
            }
        ]
    """
    try:
        conn = storage.get_db_connection()
        cursor = conn.cursor()

        # Get all active queues for this team
        cursor.execute("""
            SELECT queue_id, queue_name, queue_type, description, created_at, created_by
            FROM queues
            WHERE team_id = ? AND is_active = 1
            ORDER BY queue_name
        """, (team_id,))

        accessible_queues = []
        for row in cursor.fetchall():
            queue_id = row['queue_id']

            # Check if user has access
            has_access, reason = check_queue_access(queue_id, team_id, user_id, access_type)

            if has_access:
                accessible_queues.append({
                    'queue_id': queue_id,
                    'queue_name': row['queue_name'],
                    'queue_type': row['queue_type'],
                    'description': row['description'],
                    'created_at': row['created_at'],
                    'created_by': row['created_by'],
                    'access_reason': reason
                })

        conn.close()
        return accessible_queues

    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to get accessible queues: {e}")
        return []


def get_queue_permissions(queue_id: str, team_id: str) -> List[Dict]:
    """
    Get all permission grants for a queue.

    Args:
        queue_id: Queue ID
        team_id: Team ID

    Returns:
        List of permission grants

    Examples:
        >>> get_queue_permissions("PATIENT-ABC", "TEAM-123")
        [
            {
                'id': 1,
                'access_type': 'view',
                'grant_type': 'job_role',
                'grant_value': 'nurse',
                'created_at': '2025-01-01 12:00:00',
                'created_by': 'user1'
            }
        ]
    """
    try:
        conn = storage.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, access_type, grant_type, grant_value, created_at, created_by
            FROM queue_permissions
            WHERE queue_id = ? AND team_id = ?
            ORDER BY access_type, grant_type, grant_value
        """, (queue_id, team_id))

        permissions = []
        for row in cursor.fetchall():
            permissions.append({
                'id': row['id'],
                'access_type': row['access_type'],
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
        logger.error(f"Failed to get queue permissions: {e}")
        return []


def get_queue(queue_id: str, team_id: str) -> Optional[Dict]:
    """
    Get queue details.

    Args:
        queue_id: Queue ID
        team_id: Team ID

    Returns:
        Queue details or None if not found

    Examples:
        >>> get_queue("PATIENT-ABC", "TEAM-123")
        {
            'queue_id': 'PATIENT-ABC',
            'queue_name': 'Triage',
            'queue_type': 'patient',
            'description': 'Initial assessment',
            'created_at': '2025-01-01 12:00:00',
            'created_by': 'user1',
            'is_active': True
        }
    """
    try:
        conn = storage.get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT queue_id, queue_name, queue_type, description, created_at, created_by, is_active
            FROM queues
            WHERE queue_id = ? AND team_id = ?
        """, (queue_id, team_id))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            'queue_id': row['queue_id'],
            'queue_name': row['queue_name'],
            'queue_type': row['queue_type'],
            'description': row['description'],
            'created_at': row['created_at'],
            'created_by': row['created_by'],
            'is_active': bool(row['is_active'])
        }

    except Exception as e:
        if conn:
            conn.close()
        logger.error(f"Failed to get queue: {e}")
        return None
