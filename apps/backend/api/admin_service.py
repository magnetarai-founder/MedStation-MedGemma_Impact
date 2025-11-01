#!/usr/bin/env python3
"""
Admin Service for ElohimOS

Provides God Rights (Founder Admin) with support capabilities:
✅ CAN: View user account metadata, list users, view user chats (for support)
❌ CANNOT: Access personal vault encrypted data, see decrypted content

This follows the Salesforce model: Admins can manage accounts but cannot see user data.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, List, Optional
import sqlite3
import logging

try:
    from .auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user

try:
    from .chat_memory import get_memory
except ImportError:
    from chat_memory import get_memory

try:
    from .audit_logger import get_audit_logger, AuditAction
except ImportError:
    from audit_logger import get_audit_logger, AuditAction

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def require_god_rights(current_user: Dict = Depends(get_current_user)) -> Dict:
    """Dependency to require God Rights (Founder Admin) role"""
    if current_user.get("role") != "god_rights":
        raise HTTPException(
            status_code=403,
            detail="God Rights (Founder Admin) access required"
        )
    return current_user


def get_admin_db_connection():
    """Get connection to admin database for user management"""
    db_path = ".neutron_data/elohimos_app.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/users")
async def list_all_users(request: Request, current_user: Dict = Depends(require_god_rights)):
    """List all users on the system (God Rights only)

    Returns user account metadata (username, user_id, email, created_at)
    Does NOT return passwords, vault data, or personal content.

    This is for support purposes - helping users who forget their user_id.
    """
    # Audit log
    audit_logger.log(
        user_id=current_user["user_id"],
        action=AuditAction.ADMIN_LIST_USERS,
        ip_address=request.client.host if request.client else None,
        details={"admin_username": current_user["username"]}
    )

    conn = get_admin_db_connection()
    try:
        cursor = conn.execute("""
            SELECT user_id, username, device_id, created_at, last_login, is_active, role
            FROM users
            ORDER BY created_at DESC
        """)

        users = []
        for row in cursor.fetchall():
            users.append({
                "user_id": row["user_id"],
                "username": row["username"],
                "device_id": row["device_id"],
                "created_at": row["created_at"],
                "last_login": row["last_login"],
                "is_active": bool(row["is_active"]),
                "role": row["role"] or "member"
            })

        logger.info(f"God Rights {current_user['username']} listed {len(users)} users")
        return {"users": users, "total": len(users)}
    finally:
        conn.close()


@router.get("/users/{target_user_id}")
async def get_user_details(
    request: Request,
    target_user_id: str,
    current_user: Dict = Depends(require_god_rights)
):
    """Get specific user's account details (God Rights only)

    Returns user account metadata for support purposes.
    Does NOT return passwords, vault data, or personal content.
    """
    # Audit log
    audit_logger.log(
        user_id=current_user["user_id"],
        action=AuditAction.ADMIN_VIEW_USER,
        resource="user",
        resource_id=target_user_id,
        ip_address=request.client.host if request.client else None,
        details={"admin_username": current_user["username"]}
    )

    conn = get_admin_db_connection()
    try:
        cursor = conn.execute("""
            SELECT user_id, username, device_id, created_at, last_login, is_active, role
            FROM users
            WHERE user_id = ?
        """, (target_user_id,))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = {
            "user_id": row["user_id"],
            "username": row["username"],
            "device_id": row["device_id"],
            "created_at": row["created_at"],
            "last_login": row["last_login"],
            "is_active": bool(row["is_active"]),
            "role": row["role"] or "member"
        }

        logger.info(f"God Rights {current_user['username']} viewed user {target_user_id}")
        return user_data
    finally:
        conn.close()


@router.get("/users/{target_user_id}/chats")
async def get_user_chats(
    request: Request,
    target_user_id: str,
    current_user: Dict = Depends(require_god_rights)
):
    """Get specific user's chat sessions (God Rights only - for support)

    This is an ADMIN endpoint - explicitly for support access.
    Returns the user's chat sessions to help with troubleshooting.

    Does NOT return chat message contents - only session metadata.
    """
    # Get memory singleton
    memory = get_memory()

    # Use the new admin method that bypasses user filtering
    sessions = memory.list_user_sessions_admin(target_user_id)

    # Audit log
    audit_logger.log(
        user_id=current_user["user_id"],
        action=AuditAction.ADMIN_VIEW_USER_CHATS,
        resource="chat_sessions",
        resource_id=target_user_id,
        ip_address=request.client.host if request.client else None,
        details={
            "admin_username": current_user["username"],
            "chat_count": len(sessions)
        }
    )

    logger.info(
        f"God Rights {current_user['username']} viewed {len(sessions)} chats "
        f"for user {target_user_id}"
    )

    return {
        "user_id": target_user_id,
        "sessions": sessions,
        "total": len(sessions)
    }


@router.get("/chats")
async def list_all_chats(request: Request, current_user: Dict = Depends(require_god_rights)):
    """List ALL chat sessions across all users (God Rights only - for support)

    This is an ADMIN endpoint - explicitly for support access.
    Returns all chat sessions with user_id included.

    Does NOT return chat message contents - only session metadata.
    """
    # Get memory singleton
    memory = get_memory()

    # Use the new admin method that returns all sessions
    sessions = memory.list_all_sessions_admin()

    # Audit log
    audit_logger.log(
        user_id=current_user["user_id"],
        action=AuditAction.ADMIN_LIST_ALL_CHATS,
        ip_address=request.client.host if request.client else None,
        details={
            "admin_username": current_user["username"],
            "total_chats": len(sessions)
        }
    )

    logger.info(
        f"God Rights {current_user['username']} listed {len(sessions)} total chats "
        f"across all users"
    )

    return {
        "sessions": sessions,
        "total": len(sessions)
    }


@router.post("/users/{target_user_id}/reset-password")
async def reset_user_password(
    target_user_id: str,
    current_user: Dict = Depends(require_god_rights)
):
    """Reset user's password (God Rights only - for support)

    TODO: Implement password reset functionality
    - Generate temporary password
    - Force password change on next login
    - Send notification to user (if email configured)
    - NEVER see the user's current password
    """
    logger.warning(
        f"God Rights {current_user['username']} attempted to reset password "
        f"for user {target_user_id} - NOT YET IMPLEMENTED"
    )

    raise HTTPException(
        status_code=501,
        detail="Password reset not yet implemented. See roadmap Phase 1B."
    )


@router.post("/users/{target_user_id}/unlock")
async def unlock_user_account(
    target_user_id: str,
    current_user: Dict = Depends(require_god_rights)
):
    """Unlock user account after failed login attempts (God Rights only)

    TODO: Implement account unlock functionality
    - Clear failed login counter
    - Re-enable account
    - Notify user of unlock
    """
    logger.warning(
        f"God Rights {current_user['username']} attempted to unlock "
        f"user {target_user_id} - NOT YET IMPLEMENTED"
    )

    raise HTTPException(
        status_code=501,
        detail="Account unlock not yet implemented. See roadmap Phase 1B."
    )


@router.get("/users/{target_user_id}/vault-status")
async def get_user_vault_status(
    target_user_id: str,
    current_user: Dict = Depends(require_god_rights)
):
    """Get user's vault status (God Rights only - for support)

    Returns vault METADATA only:
    - Number of documents
    - Vault lock status
    - Last access time
    - Failed unlock attempts

    Does NOT return:
    - Encrypted vault contents
    - Vault passphrase
    - Decrypted data

    This is for support - helping users who are locked out of their vault.
    God Rights can reset the lock counter but CANNOT decrypt vault data.
    """
    logger.warning(
        f"God Rights {current_user['username']} requested vault status "
        f"for user {target_user_id} - NOT YET IMPLEMENTED"
    )

    raise HTTPException(
        status_code=501,
        detail="Vault status endpoint not yet implemented. See roadmap Phase 1B."
    )


# Export the router
__all__ = ["router"]
