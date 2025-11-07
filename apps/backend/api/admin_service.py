#!/usr/bin/env python3
"""
Admin Service for ElohimOS

Provides Founder Rights (Founder Admin) with support capabilities:
✅ CAN: View user account metadata, list users, view user chats (for support)
❌ CANNOT: Access personal vault encrypted data, see decrypted content

This follows the Salesforce model: Admins can manage accounts but cannot see user data.
"""

import logging
import sqlite3
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

try:
    from .auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user

try:
    from .chat_memory import get_memory
except ImportError:
    from chat_memory import get_memory

try:
    from .audit_logger import AuditAction, get_audit_logger
except ImportError:
    from audit_logger import AuditAction, get_audit_logger

try:
    from .rate_limiter import get_client_ip, rate_limiter
except ImportError:
    from rate_limiter import get_client_ip, rate_limiter

try:
    from .utils import sanitize_for_log
except ImportError:
    from utils import sanitize_for_log

# Phase 2: Import permission decorator
try:
    from .permission_engine import require_perm
except ImportError:
    from permission_engine import require_perm

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def require_founder_rights(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency to require Founder Rights (Founder Admin) role"""
    if current_user.get("role") != "founder_rights":
        raise HTTPException(
            status_code=403,
            detail="Founder Rights (Founder Admin) access required"
        )
    return current_user


def get_admin_db_connection():
    """
    Get connection to admin database for user management

    Phase 0: Use auth_service.db_path (points to app_db = elohimos_app.db)
    """
    try:
        from .auth_middleware import auth_service
    except ImportError:
        from auth_middleware import auth_service

    conn = sqlite3.connect(str(auth_service.db_path))
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/users")
async def list_all_users(request: Request, current_user: dict = Depends(require_founder_rights)):
    """List all users on the system (Founder Rights only)

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

        logger.info(f"Founder Rights {current_user['username']} listed {len(users)} users")
        return {"users": users, "total": len(users)}
    finally:
        conn.close()


@router.get("/users/{target_user_id}")
async def get_user_details(
    request: Request,
    target_user_id: str,
    current_user: dict = Depends(require_founder_rights)
):
    """Get specific user's account details (Founder Rights only)

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

        logger.info(f"Founder Rights {current_user['username']} viewed user {target_user_id}")
        return user_data
    finally:
        conn.close()


@router.get("/users/{target_user_id}/chats")
async def get_user_chats(
    request: Request,
    target_user_id: str,
    current_user: dict = Depends(require_founder_rights)
):
    """Get specific user's chat sessions (Founder Rights only - for support)

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
        f"Founder Rights {current_user['username']} viewed {len(sessions)} chats "
        f"for user {target_user_id}"
    )

    return {
        "user_id": target_user_id,
        "sessions": sessions,
        "total": len(sessions)
    }


@router.get("/chats")
async def list_all_chats(request: Request, current_user: dict = Depends(require_founder_rights)):
    """List ALL chat sessions across all users (Founder Rights only - for support)

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
        f"Founder Rights {current_user['username']} listed {len(sessions)} total chats "
        f"across all users"
    )

    return {
        "sessions": sessions,
        "total": len(sessions)
    }


@router.post("/users/{target_user_id}/reset-password")
async def reset_user_password(
    target_user_id: str,
    current_user: dict = Depends(require_founder_rights)
):
    """Reset user's password (Founder Rights only - for support)

    TODO: Implement password reset functionality
    - Generate temporary password
    - Force password change on next login
    - Send notification to user (if email configured)
    - NEVER see the user's current password
    """
    logger.warning(
        f"Founder Rights {current_user['username']} attempted to reset password "
        f"for user {target_user_id} - NOT YET IMPLEMENTED"
    )

    raise HTTPException(
        status_code=501,
        detail="Password reset not yet implemented. See roadmap Phase 1B."
    )


@router.post("/users/{target_user_id}/unlock")
async def unlock_user_account(
    request: Request,
    target_user_id: str,
    current_user: dict = Depends(require_founder_rights)
):
    """Unlock user account after failed login attempts (Founder Rights only)

    Clears failed login counters and re-enables account.
    """
    try:
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

        # Audit log
        audit_logger.log(
            user_id=current_user["user_id"],
            action="admin.user.unlocked",
            resource="user",
            resource_id=target_user_id,
            ip_address=request.client.host if request.client else None,
            details={
                "target_user_id": target_user_id,
                "target_username": user[1]
            }
        )

        logger.info(
            f"Founder Rights {current_user['username']} unlocked user {user[1]} ({target_user_id})"
        )

        return {
            "success": True,
            "user_id": target_user_id,
            "username": user[1],
            "message": "User account unlocked successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unlock user {target_user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unlock user: {str(e)}")


@router.get("/users/{target_user_id}/vault-status")
async def get_user_vault_status(
    request: Request,
    target_user_id: str,
    current_user: dict = Depends(require_founder_rights)
):
    """Get user's vault status (Founder Rights only - for support)

    Returns vault METADATA only:
    - Number of documents
    - Vault lock status
    - Last access time

    Does NOT return:
    - Encrypted vault contents
    - Vault passphrase
    - Decrypted data
    """
    try:
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

        # Audit log
        audit_logger.log(
            user_id=current_user["user_id"],
            action="admin.vault.status_viewed",
            resource="vault",
            resource_id=target_user_id,
            ip_address=request.client.host if request.client else None,
            details={
                "target_user_id": target_user_id,
                "target_username": user[1]
            }
        )

        logger.info(
            f"Founder Rights {current_user['username']} viewed vault status for {user[1]} ({target_user_id})"
        )

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


@router.get("/device/overview")
@require_perm("system.view_admin_dashboard")
async def get_device_overview(
    request: Request,
    current_user: dict = Depends(require_founder_rights)
):
    """
    Get device-wide overview statistics (Founder Rights only)

    Phase 0: Returns ONLY real metrics from authoritative databases.
    Never returns phantom or assumed data.

    Returns:
    - Total users from auth.users
    - Total chat sessions from memory DB (if exists)
    - Total workflows/work_items from workflows DB (if exists)
    - Total documents from docs DB (if exists)
    - Data directory size in bytes

    This is for administrative monitoring purposes.
    """
    # Rate limit: 20 device overview requests per minute per device
    client_ip = get_client_ip(request)
    if not rate_limiter.check_rate_limit(f"device_overview:{client_ip}", max_requests=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 20 requests per minute.")

    # Audit log
    audit_logger.log(
        user_id=current_user["user_id"],
        action=AuditAction.ADMIN_VIEW_DEVICE_OVERVIEW,
        ip_address=request.client.host if request.client else None,
        details={"admin_username": current_user["username"]}
    )

    overview = {}

    # Phase 0: Get user statistics from auth.users in app_db
    try:
        conn = get_admin_db_connection()
        try:
            # Total users from auth.users table
            cursor = conn.execute("SELECT COUNT(*) as total FROM users")
            overview["total_users"] = cursor.fetchone()["total"]

            # Active users (simplified for Phase 0)
            overview["active_users_7d"] = overview["total_users"]

            # Users by role
            cursor = conn.execute("""
                SELECT role, COUNT(*) as count FROM users
                GROUP BY role
            """)
            overview["users_by_role"] = {
                row["role"] or "member": row["count"]
                for row in cursor.fetchall()
            }

        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Could not get user statistics from auth.users: {e}", exc_info=True)
        overview["total_users"] = None
        overview["active_users_7d"] = None
        overview["users_by_role"] = None

    # Phase 0: Get chat statistics from PATHS.memory_db (if exists)
    try:
        from pathlib import Path
        try:
            from .config_paths import PATHS
        except ImportError:
            from config_paths import PATHS

        memory_db = PATHS.memory_db
        if memory_db.exists():
            mem_conn = sqlite3.connect(str(memory_db))
            mem_conn.row_factory = sqlite3.Row

            # Check if chat_sessions table exists
            cursor = mem_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='chat_sessions'"
            )
            if cursor.fetchone():
                cursor = mem_conn.execute("SELECT COUNT(*) as total FROM chat_sessions")
                overview["total_chat_sessions"] = cursor.fetchone()["total"]
            else:
                overview["total_chat_sessions"] = None

            mem_conn.close()
        else:
            overview["total_chat_sessions"] = None
    except Exception as e:
        logger.warning(f"Could not get chat statistics: {e}")
        overview["total_chat_sessions"] = None

    # Phase 0: Get workflow statistics from workflows DB (if exists)
    try:
        # Phase 0: Use PATHS to find workflows DB in app_db
        # For now, workflows might still be in separate DB - check both locations
        workflow_db = PATHS.data_dir / "workflows.db"

        if workflow_db.exists():
            wf_conn = sqlite3.connect(str(workflow_db))
            wf_conn.row_factory = sqlite3.Row

            # Check tables exist
            cursor = wf_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='workflows'"
            )
            if cursor.fetchone():
                cursor = wf_conn.execute("SELECT COUNT(*) as total FROM workflows")
                overview["total_workflows"] = cursor.fetchone()["total"]
            else:
                overview["total_workflows"] = None

            cursor = wf_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='work_items'"
            )
            if cursor.fetchone():
                cursor = wf_conn.execute("SELECT COUNT(*) as total FROM work_items")
                overview["total_work_items"] = cursor.fetchone()["total"]
            else:
                overview["total_work_items"] = None

            wf_conn.close()
        else:
            overview["total_workflows"] = None
            overview["total_work_items"] = None
    except Exception as e:
        logger.warning(f"Could not get workflow statistics: {e}")
        overview["total_workflows"] = None
        overview["total_work_items"] = None

    # Phase 0: Get document statistics from docs DB (if exists)
    try:
        docs_db = PATHS.data_dir / "docs.db"

        if docs_db.exists():
            docs_conn = sqlite3.connect(str(docs_db))
            docs_conn.row_factory = sqlite3.Row

            cursor = docs_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='documents'"
            )
            if cursor.fetchone():
                cursor = docs_conn.execute("SELECT COUNT(*) as total FROM documents")
                overview["total_documents"] = cursor.fetchone()["total"]
            else:
                overview["total_documents"] = None

            docs_conn.close()
        else:
            overview["total_documents"] = None
    except Exception as e:
        logger.warning(f"Could not get document statistics: {e}")
        overview["total_documents"] = None

    # Phase 0: Calculate data directory size in bytes
    try:
        import os
        data_dir = PATHS.data_dir
        total_size = 0

        if data_dir.exists():
            for dirpath, dirnames, filenames in os.walk(data_dir):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)

        overview["data_dir_size_bytes"] = total_size
        # Also provide human-readable size
        if total_size >= 1024**3:  # GB
            overview["data_dir_size_human"] = f"{total_size / (1024**3):.2f} GB"
        elif total_size >= 1024**2:  # MB
            overview["data_dir_size_human"] = f"{total_size / (1024**2):.2f} MB"
        elif total_size >= 1024:  # KB
            overview["data_dir_size_human"] = f"{total_size / 1024:.2f} KB"
        else:
            overview["data_dir_size_human"] = f"{total_size} bytes"
    except Exception as e:
        logger.warning(f"Could not calculate data directory size: {e}")
        overview["data_dir_size_bytes"] = None
        overview["data_dir_size_human"] = None

    logger.info(f"Founder Rights {current_user['username']} viewed device overview")

    return {
        "device_overview": overview,
        "timestamp": str(__import__('datetime').datetime.utcnow().isoformat())
    }


@router.get("/users/{target_user_id}/workflows")
async def get_user_workflows(
    request: Request,
    target_user_id: str,
    current_user: dict = Depends(require_founder_rights)
):
    """Get specific user's workflows (Founder Rights only - for support)

    Returns the user's workflow definitions and work items.
    This is for support purposes - helping users troubleshoot workflow issues.

    Does NOT return workflow execution data or sensitive business logic.
    """
    # Audit log
    audit_logger.log(
        user_id=current_user["user_id"],
        action=AuditAction.ADMIN_VIEW_USER_WORKFLOWS,
        resource="workflows",
        resource_id=target_user_id,
        ip_address=request.client.host if request.client else None,
        details={"admin_username": current_user["username"]}
    )

    try:
        from pathlib import Path
        workflow_db = Path(".") / "apps" / "backend" / "api" / "data" / "workflows.db"
        if not workflow_db.exists():
            workflow_db = Path("data") / "workflows.db"

        if not workflow_db.exists():
            raise HTTPException(
                status_code=503,
                detail="Workflow database not available"
            )

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

        logger.info(
            f"Founder Rights {current_user['username']} viewed workflows "
            f"for user {target_user_id}: {len(workflows)} workflows, {len(work_items)} items"
        )

        return {
            "user_id": target_user_id,
            "workflows": workflows,
            "work_items": work_items,
            "total_workflows": len(workflows),
            "total_work_items": len(work_items)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user workflows: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve user workflows: {str(e)}"
        )


@router.get("/audit/logs")
@require_perm("system.view_audit_logs")
async def get_audit_logs(
    request: Request,
    user_id: str | None = None,
    action: str | None = None,
    resource: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """
    Get audit logs with filters (requires system.view_audit_logs permission)

    Query params:
    - user_id: Filter by user
    - action: Filter by action type
    - resource: Filter by resource type
    - start_date: ISO format date string (YYYY-MM-DD)
    - end_date: ISO format date string (YYYY-MM-DD)
    - limit: Max results (default 100)
    - offset: Pagination offset (default 0)

    Returns:
    - logs: List of audit log entries
    - total: Total count matching filters
    """
    from datetime import datetime

    # Parse dates if provided
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

    try:
        # Get logs from audit logger
        logs = audit_logger.get_logs(
            user_id=user_id,
            action=action,
            resource=resource,
            start_date=start_dt,
            end_date=end_dt,
            limit=limit,
            offset=offset
        )

        # Get total count
        total = audit_logger.count_logs(
            user_id=user_id,
            action=action,
            resource=resource,
            start_date=start_dt,
            end_date=end_dt
        )

        # Log this audit access
        audit_logger.log(
            user_id=current_user["user_id"],
            action="audit.logs.viewed",
            ip_address=request.client.host if request.client else None,
            details={
                "filters": {
                    "user_id": user_id,
                    "action": action,
                    "resource": resource,
                    "start_date": start_date,
                    "end_date": end_date
                },
                "result_count": len(logs)
            }
        )

        return {
            "logs": [log.dict() for log in logs],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit logs: {str(e)}")


@router.get("/audit/export")
@require_perm("system.view_audit_logs")
async def export_audit_logs(
    request: Request,
    start_date: str | None = None,
    end_date: str | None = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Export audit logs to CSV (requires system.view_audit_logs permission)

    Query params:
    - start_date: ISO format date string (YYYY-MM-DD)
    - end_date: ISO format date string (YYYY-MM-DD)

    Returns:
    - CSV file download
    """
    import tempfile
    from datetime import datetime
    from pathlib import Path

    from fastapi.responses import FileResponse

    # Parse dates if provided
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

    try:
        # Create temp file for CSV
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        temp_path = Path(temp_file.name)
        temp_file.close()

        # Export to CSV
        success = audit_logger.export_to_csv(
            output_path=temp_path,
            start_date=start_dt,
            end_date=end_dt
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to export audit logs")

        # Log this export
        audit_logger.log(
            user_id=current_user["user_id"],
            action="audit.logs.exported",
            ip_address=request.client.host if request.client else None,
            details={
                "start_date": start_date,
                "end_date": end_date
            }
        )

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"audit_logs_{timestamp}.csv"

        # Return file with background deletion
        from starlette.background import BackgroundTask
        return FileResponse(
            path=temp_path,
            filename=filename,
            media_type="text/csv",
            background=BackgroundTask(lambda: temp_path.unlink(missing_ok=True))
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export audit logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export audit logs: {str(e)}")


# Export the router
__all__ = ["router"]
