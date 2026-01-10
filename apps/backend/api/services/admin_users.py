"""
Admin User Operations

Provides Founder Rights support capabilities for user management:
- User account metadata (list, details)
- Chat session metadata (user chats, all chats)

Does NOT expose passwords, vault data, or personal content.
This follows the Salesforce model: Admins can manage accounts but cannot see user data.

Extracted from admin_support.py during P2 decomposition.
"""

import sqlite3
import logging
from typing import Dict, Any
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def get_admin_db_connection() -> sqlite3.Connection:
    """
    Get connection to admin database for user management.

    Uses auth_service.db_path (points to app_db = elohimos_app.db).

    Returns:
        SQLite connection with Row factory
    """
    try:
        from api.auth_middleware import auth_service
    except ImportError:
        from auth_middleware import auth_service

    conn = sqlite3.connect(str(auth_service.db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _get_memory() -> Any:
    """Get memory (chat) service instance."""
    try:
        from api.chat_memory import get_memory
    except ImportError:
        from chat_memory import get_memory
    return get_memory()


# ===== User Metadata Functions =====

async def list_all_users() -> Dict[str, Any]:
    """
    List all users on the system.

    Returns user account metadata (username, user_id, device_id, created_at, etc.)
    Does NOT return passwords, vault data, or personal content.

    Returns:
        Dict with "users" list and "total" count
    """
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

        return {"users": users, "total": len(users)}
    finally:
        conn.close()


async def get_user_details(target_user_id: str) -> Dict[str, Any]:
    """
    Get specific user's account details.

    Returns user account metadata for support purposes.
    Does NOT return passwords, vault data, or personal content.

    Args:
        target_user_id: User identifier

    Returns:
        Dict with user account metadata

    Raises:
        HTTPException: If user not found
    """
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

        return {
            "user_id": row["user_id"],
            "username": row["username"],
            "device_id": row["device_id"],
            "created_at": row["created_at"],
            "last_login": row["last_login"],
            "is_active": bool(row["is_active"]),
            "role": row["role"] or "member"
        }
    finally:
        conn.close()


# ===== Chat Metadata Functions =====

async def get_user_chats(target_user_id: str) -> Dict[str, Any]:
    """
    Get user's chat sessions for support purposes.

    Returns chat session metadata (session_id, created_at, message counts)
    Does NOT return actual chat messages or content.

    Args:
        target_user_id: User identifier

    Returns:
        Dict with user_id, sessions list, and total count
    """
    memory = _get_memory()
    sessions = memory.list_user_sessions_admin(target_user_id)

    return {
        "user_id": target_user_id,
        "sessions": sessions,
        "total": len(sessions)
    }


async def list_all_chats() -> Dict[str, Any]:
    """
    List all chat sessions across all users.

    For support and monitoring purposes.

    Returns:
        Dict with sessions list and total count
    """
    memory = _get_memory()
    sessions = memory.list_all_sessions_admin()

    return {
        "sessions": sessions,
        "total": len(sessions)
    }


__all__ = [
    "get_admin_db_connection",
    "list_all_users",
    "get_user_details",
    "get_user_chats",
    "list_all_chats",
]
