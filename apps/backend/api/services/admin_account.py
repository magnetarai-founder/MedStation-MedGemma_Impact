"""
Admin Account Operations

Provides Founder Rights support capabilities for account remediation:
- Password reset (generates temporary password)
- Account unlock (clears failed login attempts)

Extracted from admin_support.py during P2 decomposition.
"""

import sqlite3
import logging
import secrets
import string
from typing import Dict, Any
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def _get_memory() -> Any:
    """Get memory (chat) service instance."""
    from api.chat_memory import get_memory
    return get_memory()


def _get_auth_service() -> Any:
    """Get auth service instance."""
    from api.auth_middleware import auth_service
    return auth_service


# ===== Account Remediation Functions =====

async def reset_user_password(target_user_id: str) -> Dict[str, Any]:
    """
    Reset user's password (for support).

    Generates a secure temporary password and sets must_change_password flag.
    The user will be required to change their password on next login.

    Args:
        target_user_id: User identifier

    Returns:
        Dict with success status, temp_password, and user details

    Raises:
        HTTPException: If user not found or inactive
    """
    from api.config_paths import PATHS

    auth_service = _get_auth_service()

    try:
        conn = sqlite3.connect(str(PATHS.app_db))
        cursor = conn.cursor()

        # Verify target user exists
        cursor.execute(
            "SELECT username, is_active FROM users WHERE user_id = ?",
            (target_user_id,)
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")

        target_username, is_active = row

        if not is_active:
            conn.close()
            raise HTTPException(
                status_code=400,
                detail="Cannot reset password for inactive user"
            )

        # Generate secure temporary password (16 characters)
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
        temp_password = ''.join(secrets.choice(alphabet) for _ in range(16))

        # Hash the temporary password using PBKDF2 (consistent with auth_middleware)
        password_hash, _ = auth_service._hash_password(temp_password)

        # Update user: set new password hash and must_change_password flag
        cursor.execute(
            """
            UPDATE users
            SET password_hash = ?, must_change_password = 1
            WHERE user_id = ?
            """,
            (password_hash, target_user_id)
        )

        conn.commit()
        conn.close()

        return {
            "success": True,
            "user_id": target_user_id,
            "username": target_username,
            "temp_password": temp_password,
            "must_change_password": True,
            "message": "Password reset successful. User must change password on next login."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset password for user {target_user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset password: {str(e)}"
        )


async def unlock_user_account(target_user_id: str) -> Dict[str, Any]:
    """
    Unlock user account after failed login attempts.

    Clears failed login counters and re-enables account.

    Args:
        target_user_id: User identifier

    Returns:
        Dict with success status and user details

    Raises:
        HTTPException: If user not found
    """
    try:
        memory = _get_memory()
        conn = memory.memory.conn

        # Check if user exists
        user = conn.execute(
            "SELECT user_id, username, is_active FROM users WHERE user_id = ?",
            (target_user_id,)
        ).fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Clear failed login counter and re-enable account
        conn.execute("""
            UPDATE users
            SET is_active = 1,
                failed_login_attempts = 0,
                lockout_until = NULL
            WHERE user_id = ?
        """, (target_user_id,))

        conn.commit()

        return {
            "success": True,
            "user_id": target_user_id,
            "username": user[1],
            "message": f"Account {user[1]} has been unlocked successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unlock user {target_user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unlock user: {str(e)}")


__all__ = [
    "reset_user_password",
    "unlock_user_account",
]
