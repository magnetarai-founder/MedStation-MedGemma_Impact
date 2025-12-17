"""
Auth Test Utilities (AUTH-P4)

Provides helpers for creating users with different roles and testing RBAC policies.

Usage:
    from tests.utils.auth_test_utils import create_user_with_role, ROLES

    # Create test users
    founder_id, founder_token = create_user_with_role(db_path, "founder", ROLES.FOUNDER)
    admin_id, admin_token = create_user_with_role(db_path, "admin", ROLES.ADMIN)
    member_id, member_token = create_user_with_role(db_path, "member", ROLES.MEMBER)

    # Use tokens in test requests
    headers = {"Authorization": f"Bearer {member_token}"}
    response = client.post("/api/admin/reset-all", headers=headers)
    assert response.status_code == 403  # Member should be denied
"""

import sqlite3
import secrets
from pathlib import Path
from typing import Tuple
from datetime import datetime, UTC


class ROLES:
    """Standard role constants for testing"""
    FOUNDER = "founder_rights"
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


def create_user_with_role(
    db_path: Path,
    username: str,
    role: str,
    password: str = "Test123!@#"
) -> Tuple[str, str]:
    """
    Create a test user with a specific role and return (user_id, jwt_token)

    This function:
    1. Creates a user row in the users table with the specified role
    2. Generates a JWT token for the user via normal authentication flow

    Args:
        db_path: Path to test database
        username: Username for the test user
        role: Role to assign (use ROLES constants)
        password: Password for the user (default: "Test123!@#")

    Returns:
        Tuple of (user_id, jwt_token) for making authenticated requests

    Example:
        user_id, token = create_user_with_role(tmp_db, "test_admin", ROLES.ADMIN)
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/admin/status", headers=headers)
    """
    # Generate user_id
    user_id = f"{role}_{secrets.token_urlsafe(8)}"

    # Hash password using the same method as auth_bootstrap
    from api.auth_bootstrap import _hash_password_pbkdf2
    password_hash, _ = _hash_password_pbkdf2(password)

    # Create user in database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO users (user_id, username, password_hash, device_id, created_at, role, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        username,
        password_hash,
        "test_device",
        datetime.now(UTC).isoformat(),
        role,
        1
    ))

    conn.commit()
    conn.close()

    # Authenticate to get JWT token
    from api.auth_middleware import AuthService
    auth_service = AuthService(db_path=db_path)

    auth_result = auth_service.authenticate(username, password)

    if not auth_result:
        raise ValueError(f"Failed to authenticate test user {username}")

    return user_id, auth_result['token']


def create_test_users(db_path: Path) -> dict:
    """
    Create a standard set of test users with different roles

    Convenient helper that creates one user of each type for policy tests.

    Args:
        db_path: Path to test database

    Returns:
        Dictionary mapping role name to (user_id, token) tuples:
        {
            "founder": (user_id, token),
            "super_admin": (user_id, token),
            "admin": (user_id, token),
            "member": (user_id, token),
            "guest": (user_id, token),
        }

    Example:
        users = create_test_users(tmp_db)
        founder_token = users["founder"][1]
        member_token = users["member"][1]

        # Founder can access dangerous operations
        response = client.post("/api/admin/reset-all",
                             headers={"Authorization": f"Bearer {founder_token}"})
        assert response.status_code == 200

        # Member cannot
        response = client.post("/api/admin/reset-all",
                             headers={"Authorization": f"Bearer {member_token}"})
        assert response.status_code == 403
    """
    return {
        "founder": create_user_with_role(db_path, "test_founder", ROLES.FOUNDER),
        "super_admin": create_user_with_role(db_path, "test_super_admin", ROLES.SUPER_ADMIN),
        "admin": create_user_with_role(db_path, "test_admin", ROLES.ADMIN),
        "member": create_user_with_role(db_path, "test_member", ROLES.MEMBER),
        "guest": create_user_with_role(db_path, "test_guest", ROLES.GUEST),
    }


def grant_permission_to_user(
    db_path: Path,
    user_id: str,
    permission_key: str,
    permission_level: str = "write"
):
    """
    Grant a specific permission to a user via permission set

    Useful for testing scenarios where you need to grant specific permissions
    to users that don't normally have them.

    Args:
        db_path: Path to test database
        user_id: User to grant permission to
        permission_key: Permission to grant (e.g., "system.manage_settings")
        permission_level: Level to grant ("read", "write", "admin")

    Example:
        # Create a member user
        member_id, member_token = create_user_with_role(tmp_db, "test_member", ROLES.MEMBER)

        # Grant them admin permissions for testing
        grant_permission_to_user(tmp_db, member_id, "system.manage_settings", "admin")

        # Now they can access admin operations
        response = client.post("/api/admin/export-all",
                             headers={"Authorization": f"Bearer {member_token}"})
        assert response.status_code == 200
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create a permission set for this grant
    perm_set_id = f"test_perm_set_{secrets.token_urlsafe(8)}"
    cursor.execute("""
        INSERT INTO permission_sets (permission_set_id, set_name, set_description, created_at, is_active)
        VALUES (?, ?, ?, ?, ?)
    """, (
        perm_set_id,
        f"Test permission set for {user_id}",
        f"Grants {permission_key} to {user_id}",
        datetime.now(UTC).isoformat(),
        1
    ))

    # Find or create the permission
    cursor.execute("SELECT permission_id FROM permissions WHERE permission_key = ?", (permission_key,))
    perm_row = cursor.fetchone()

    if perm_row:
        permission_id = perm_row[0]
    else:
        # Create permission if it doesn't exist
        permission_id = f"perm_{secrets.token_urlsafe(8)}"
        cursor.execute("""
            INSERT INTO permissions (permission_id, permission_key, permission_name, permission_description,
                                   category, permission_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            permission_id,
            permission_key,
            permission_key.replace(".", " ").title(),
            f"Test permission {permission_key}",
            "system",
            "level",
            datetime.now(UTC).isoformat()
        ))

    # Add permission to set
    cursor.execute("""
        INSERT INTO permission_set_permissions (permission_set_id, permission_id, is_granted, permission_level, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        perm_set_id,
        permission_id,
        1,
        permission_level,
        datetime.now(UTC).isoformat()
    ))

    # Assign set to user
    cursor.execute("""
        INSERT INTO user_permission_sets (user_id, permission_set_id, assigned_at)
        VALUES (?, ?, ?)
    """, (
        user_id,
        perm_set_id,
        datetime.now(UTC).isoformat()
    ))

    conn.commit()
    conn.close()
