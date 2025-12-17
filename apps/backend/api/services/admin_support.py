"""
Admin Support Service for ElohimOS

Provides Founder Rights support capabilities:
- User account metadata (list, details)
- Chat session metadata (user chats, all chats)
- Account remediation (password reset, unlock)
- Vault status metadata (document counts only, no decrypted content)
- Device overview metrics (system-wide statistics)
- Workflow metadata
- Audit log queries

Does NOT expose:
- Decrypted vault content
- User passwords
- Personal encrypted data

This follows the Salesforce model: Admins can manage accounts but cannot see user data.

Extracted from admin_service.py during Phase 6.3b modularization.
"""

import sqlite3
import logging
import secrets
import string
from typing import Dict, List, Optional, Any
from datetime import datetime
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


def _get_memory():
    """Get memory (chat) service instance."""
    try:
        from api.chat_memory import get_memory
    except ImportError:
        from chat_memory import get_memory
    return get_memory()


def _get_auth_service():
    """Get auth service instance."""
    try:
        from api.auth_middleware import auth_service
        return auth_service
    except ImportError:
        from auth_middleware import auth_service
        return auth_service


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
    try:
        from api.config_paths import PATHS
    except ImportError:
        from config_paths import PATHS

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


# ===== Vault Status Functions =====

async def get_vault_status(target_user_id: str) -> Dict[str, Any]:
    """
    Get user's vault status for support.

    Returns vault METADATA only:
    - Number of documents in real vault
    - Number of documents in decoy vault
    - Last access time

    Does NOT return:
    - Encrypted vault contents
    - Vault passphrase
    - Decrypted data

    Args:
        target_user_id: User identifier

    Returns:
        Dict with vault metadata

    Raises:
        HTTPException: If user not found
    """
    try:
        memory = _get_memory()
        conn = memory.memory.conn

        # Check if user exists
        user = conn.execute(
            "SELECT user_id, username FROM users WHERE user_id = ?",
            (target_user_id,)
        ).fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get document count for real vault
        doc_count_real = conn.execute("""
            SELECT COUNT(*) FROM documents
            WHERE user_id = ? AND vault_type = 'real' AND deleted_at IS NULL
        """, (target_user_id,)).fetchone()[0]

        # Get document count for decoy vault (if enabled)
        doc_count_decoy = conn.execute("""
            SELECT COUNT(*) FROM documents
            WHERE user_id = ? AND vault_type = 'decoy' AND deleted_at IS NULL
        """, (target_user_id,)).fetchone()[0]

        # Get last vault access time (approximate via last document update)
        last_access = conn.execute("""
            SELECT MAX(updated_at) FROM documents
            WHERE user_id = ?
        """, (target_user_id,)).fetchone()[0]

        return {
            "user_id": target_user_id,
            "username": user[1],
            "real_vault": {
                "document_count": doc_count_real
            },
            "decoy_vault": {
                "document_count": doc_count_decoy
            },
            "last_access": last_access,
            "note": "Metadata only - vault contents remain encrypted and inaccessible"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get vault status for {target_user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get vault status: {str(e)}")


# ===== Device Overview Functions =====

async def get_device_overview_metrics() -> Dict[str, Any]:
    """
    Gather device-wide overview statistics.

    Returns ONLY real metrics from authoritative databases.
    Never returns phantom or assumed data.

    This function does NOT perform rate limiting or audit logging.
    The router layer handles those concerns.

    Returns:
        Dict with device_overview and timestamp
    """
    try:
        from api.config_paths import PATHS
    except ImportError:
        from config_paths import PATHS

    memory = _get_memory()
    overview = {}

    # 1. Total users from auth DB
    try:
        conn = memory.memory.conn
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        overview["total_users"] = user_count
    except Exception as e:
        logger.error(f"Failed to count users: {e}")
        overview["total_users"] = None

    # 2. Total chat sessions from memory DB
    try:
        chat_count = conn.execute("SELECT COUNT(*) FROM chat_sessions").fetchone()[0]
        overview["total_chat_sessions"] = chat_count
    except Exception as e:
        logger.debug(f"No chat_sessions table or error: {e}")
        overview["total_chat_sessions"] = None

    # 3. Total workflows from workflows DB
    try:
        workflows_db_path = PATHS.data_dir / "workflows.db"
        if workflows_db_path.exists():
            workflows_conn = sqlite3.connect(str(workflows_db_path))
            workflow_count = workflows_conn.execute("SELECT COUNT(*) FROM workflows").fetchone()[0]
            workflows_conn.close()
            overview["total_workflows"] = workflow_count
        else:
            overview["total_workflows"] = None
    except Exception as e:
        logger.debug(f"No workflows DB or error: {e}")
        overview["total_workflows"] = None

    # 4. Total work items from workflows DB
    try:
        workflows_db_path = PATHS.data_dir / "workflows.db"
        if workflows_db_path.exists():
            workflows_conn = sqlite3.connect(str(workflows_db_path))
            work_item_count = workflows_conn.execute("SELECT COUNT(*) FROM work_items").fetchone()[0]
            workflows_conn.close()
            overview["total_work_items"] = work_item_count
        else:
            overview["total_work_items"] = None
    except Exception as e:
        logger.debug(f"No work_items table or error: {e}")
        overview["total_work_items"] = None

    # 5. Total documents from memory DB
    try:
        doc_count = conn.execute("SELECT COUNT(*) FROM documents WHERE deleted_at IS NULL").fetchone()[0]
        overview["total_documents"] = doc_count
    except Exception as e:
        logger.debug(f"No documents table or error: {e}")
        overview["total_documents"] = None

    # 6. Data directory size
    try:
        import os
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(PATHS.data_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        overview["data_dir_size_bytes"] = total_size
        overview["data_dir_size_mb"] = round(total_size / (1024 * 1024), 2)
    except Exception as e:
        logger.error(f"Failed to calculate data dir size: {e}")
        overview["data_dir_size_bytes"] = None
        overview["data_dir_size_mb"] = None

    return {
        "device_overview": overview,
        "timestamp": datetime.now(UTC).isoformat()
    }


# ===== Workflow Metadata Functions =====

async def get_user_workflows(target_user_id: str) -> Dict[str, Any]:
    """
    Get user's workflows for support purposes.

    Returns workflow metadata (id, name, description, category, enabled)
    and work items (id, workflow_id, status, priority).
    Does NOT return workflow execution details or sensitive data.

    Args:
        target_user_id: User identifier

    Returns:
        Dict with user_id, workflows list, work_items list, and totals

    Raises:
        HTTPException: If workflows DB not available
    """
    from pathlib import Path

    # Try multiple possible paths for workflows DB
    workflow_db = Path(".") / "apps" / "backend" / "api" / "data" / "workflows.db"
    if not workflow_db.exists():
        workflow_db = Path("data") / "workflows.db"

    try:
        from api.config_paths import PATHS
        if not workflow_db.exists():
            workflow_db = PATHS.data_dir / "workflows.db"
    except ImportError:
        pass

    if not workflow_db.exists():
        raise HTTPException(
            status_code=503,
            detail="Workflow database not available"
        )

    try:
        wf_conn = sqlite3.connect(str(workflow_db))
        wf_conn.row_factory = sqlite3.Row

        # Get user's workflows
        cursor = wf_conn.execute("""
            SELECT id, name, description, category, enabled, created_at, updated_at
            FROM workflows
            WHERE user_id = ?
            ORDER BY updated_at DESC
        """, (target_user_id,))

        workflows = []
        for row in cursor.fetchall():
            workflows.append({
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "category": row["category"],
                "enabled": bool(row["enabled"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            })

        # Get user's work items
        cursor = wf_conn.execute("""
            SELECT id, workflow_id, status, priority, created_at, updated_at
            FROM work_items
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT 100
        """, (target_user_id,))

        work_items = []
        for row in cursor.fetchall():
            work_items.append({
                "id": row["id"],
                "workflow_id": row["workflow_id"],
                "status": row["status"],
                "priority": row["priority"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            })

        wf_conn.close()

        return {
            "user_id": target_user_id,
            "workflows": workflows,
            "work_items": work_items,
            "total_workflows": len(workflows),
            "total_work_items": len(work_items)
        }

    except Exception as e:
        logger.error(f"Failed to get workflows for user {target_user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve user workflows: {str(e)}"
        )


# ===== Audit Log Functions =====

async def get_audit_logs(
    limit: int = 100,
    offset: int = 0,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Query audit logs with filters.

    Args:
        limit: Maximum number of logs to return
        offset: Number of logs to skip
        user_id: Filter by user_id
        action: Filter by action type
        start_date: Filter by start date (ISO format)
        end_date: Filter by end date (ISO format)

    Returns:
        Dict with logs list and total count
    """
    try:
        from api.config_paths import PATHS
    except ImportError:
        from config_paths import PATHS

    audit_db_path = PATHS.data_dir / "audit_log.db"
    if not audit_db_path.exists():
        return {"logs": [], "total": 0}

    try:
        conn = sqlite3.connect(str(audit_db_path))
        conn.row_factory = sqlite3.Row

        # Build query with filters
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if action:
            query += " AND action = ?"
            params.append(action)

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = conn.execute(query, params)
        logs = [dict(row) for row in cursor.fetchall()]

        # Get total count
        count_query = "SELECT COUNT(*) FROM audit_log WHERE 1=1"
        count_params = []

        if user_id:
            count_query += " AND user_id = ?"
            count_params.append(user_id)

        if action:
            count_query += " AND action = ?"
            count_params.append(action)

        if start_date:
            count_query += " AND timestamp >= ?"
            count_params.append(start_date)

        if end_date:
            count_query += " AND timestamp <= ?"
            count_params.append(end_date)

        total = conn.execute(count_query, count_params).fetchone()[0]

        conn.close()

        return {"logs": logs, "total": total}

    except Exception as e:
        logger.error(f"Failed to query audit logs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve audit logs: {str(e)}"
        )


async def export_audit_logs(
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    Export audit logs as CSV.

    Args:
        user_id: Filter by user_id
        start_date: Filter by start date (ISO format)
        end_date: Filter by end date (ISO format)

    Returns:
        CSV string of audit logs

    Raises:
        HTTPException: If audit DB not available
    """
    try:
        from api.config_paths import PATHS
    except ImportError:
        from config_paths import PATHS

    audit_db_path = PATHS.data_dir / "audit_log.db"
    if not audit_db_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Audit log database not found"
        )

    try:
        import csv
        import io

        conn = sqlite3.connect(str(audit_db_path))
        conn.row_factory = sqlite3.Row

        # Build query with filters
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        query += " ORDER BY timestamp DESC"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        # Generate CSV
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))

        conn.close()

        return output.getvalue()

    except Exception as e:
        logger.error(f"Failed to export audit logs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export audit logs: {str(e)}"
        )
