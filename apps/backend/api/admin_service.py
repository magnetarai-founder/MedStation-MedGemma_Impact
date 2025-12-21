#!/usr/bin/env python3
"""
Admin Service Router for ElohimOS

Thin HTTP router for Founder Rights (Founder Admin) endpoints.
Handles:
- HTTP security (require_founder_rights, @require_perm decorators)
- Audit logging
- Rate limiting
- Request/response handling

Business logic delegated to services.admin_support.

Provides Founder Rights (Founder Admin) with support capabilities:
✅ CAN: View user account metadata, list users, view user chats (for support)
❌ CANNOT: Access personal vault encrypted data, see decrypted content

This follows the Salesforce model: Admins can manage accounts but cannot see user data.

Refactored in Phase 6.3b: Router layer separated from business logic.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

try:
    from .auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user

try:
    from .audit_logger import AuditAction, get_audit_logger
except ImportError:
    from audit_logger import AuditAction, get_audit_logger

try:
    from .rate_limiter import get_client_ip, rate_limiter
except ImportError:
    from rate_limiter import get_client_ip, rate_limiter

# Phase 2: Import permission decorator
try:
    from .permission_engine import require_perm
except ImportError:
    from permission_engine import require_perm

# Import admin support service
try:
    from api.services import admin_support
except ImportError:
    import services.admin_support as admin_support

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


# ===== User Account Endpoints =====

@router.get("/users")
async def list_all_users(request: Request, current_user: dict = Depends(require_founder_rights)) -> Dict[str, Any]:
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

    result = await admin_support.list_all_users()

    logger.info(f"Founder Rights {current_user['username']} listed {result['total']} users")
    return result


@router.get("/users/{target_user_id}")
async def get_user_details(
    request: Request,
    target_user_id: str,
    current_user: dict = Depends(require_founder_rights)
) -> Dict[str, Any]:
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

    result = await admin_support.get_user_details(target_user_id)

    logger.info(f"Founder Rights {current_user['username']} viewed user {target_user_id}")
    return result


# ===== Chat Support Endpoints =====

@router.get("/users/{target_user_id}/chats")
async def get_user_chats(
    request: Request,
    target_user_id: str,
    current_user: dict = Depends(require_founder_rights)
) -> Dict[str, Any]:
    """Get user's chat sessions (Founder Rights only - for support)

    Returns chat session metadata (session_id, timestamp, message count).
    Does NOT return actual chat messages.

    This is for support purposes - understanding user's chat usage patterns.
    """
    # Audit log
    audit_logger.log(
        user_id=current_user["user_id"],
        action=AuditAction.ADMIN_VIEW_USER_CHATS,
        resource="chat",
        resource_id=target_user_id,
        ip_address=request.client.host if request.client else None,
        details={"admin_username": current_user["username"]}
    )

    result = await admin_support.get_user_chats(target_user_id)

    logger.info(
        f"Founder Rights {current_user['username']} viewed chats for user {target_user_id}: "
        f"{result['total']} sessions"
    )
    return result


@router.get("/chats")
async def list_all_chats(request: Request, current_user: dict = Depends(require_founder_rights)) -> Dict[str, Any]:
    """List all chat sessions (Founder Rights only - for monitoring)

    Returns chat session metadata across all users.
    Does NOT return actual chat messages.
    """
    # Audit log
    audit_logger.log(
        user_id=current_user["user_id"],
        action=AuditAction.ADMIN_LIST_CHATS,
        ip_address=request.client.host if request.client else None,
        details={"admin_username": current_user["username"]}
    )

    result = await admin_support.list_all_chats()

    logger.info(f"Founder Rights {current_user['username']} listed {result['total']} chat sessions")
    return result


# ===== Account Remediation Endpoints =====

@router.post("/users/{target_user_id}/reset-password")
async def reset_user_password(
    request: Request,
    target_user_id: str,
    current_user: dict = Depends(require_founder_rights)
) -> Dict[str, Any]:
    """Reset user's password (Founder Rights only - for support)

    Generates a secure temporary password and sets must_change_password flag.
    The user will be required to change their password on next login.

    Security:
    - Founder Rights only
    - Generates cryptographically secure temporary password
    - Forces password change on next login
    - Audit logged
    - Original password is never disclosed
    """
    result = await admin_support.reset_user_password(target_user_id)

    # Audit log
    audit_logger.log(
        user_id=current_user["user_id"],
        action=AuditAction.PASSWORD_RESET,
        resource="user",
        resource_id=target_user_id,
        ip_address=request.client.host if request.client else None,
        details={
            "target_username": result["username"],
            "reset_by": current_user["username"]
        }
    )

    logger.info(
        f"Founder Rights {current_user['username']} reset password for user "
        f"{result['username']} (ID: {target_user_id})"
    )

    return result


@router.post("/users/{target_user_id}/unlock")
async def unlock_user_account(
    request: Request,
    target_user_id: str,
    current_user: dict = Depends(require_founder_rights)
) -> Dict[str, Any]:
    """Unlock user account after failed login attempts (Founder Rights only)

    Clears failed login counters and re-enables account.
    """
    result = await admin_support.unlock_user_account(target_user_id)

    # Audit log
    audit_logger.log(
        user_id=current_user["user_id"],
        action=AuditAction.ACCOUNT_UNLOCKED,
        resource="user",
        resource_id=target_user_id,
        ip_address=request.client.host if request.client else None,
        details={
            "target_username": result["username"],
            "unlocked_by": current_user["username"]
        }
    )

    logger.info(
        f"Founder Rights {current_user['username']} unlocked account for user "
        f"{result['username']} ({target_user_id})"
    )

    return result


# ===== Vault Status Endpoint =====

@router.get("/users/{target_user_id}/vault-status")
async def get_user_vault_status(
    request: Request,
    target_user_id: str,
    current_user: dict = Depends(require_founder_rights)
) -> Dict[str, Any]:
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
    result = await admin_support.get_vault_status(target_user_id)

    # Audit log
    audit_logger.log(
        user_id=current_user["user_id"],
        action="admin.vault.status_viewed",
        resource="vault",
        resource_id=target_user_id,
        ip_address=request.client.host if request.client else None,
        details={
            "target_user_id": target_user_id,
            "target_username": result["username"]
        }
    )

    logger.info(
        f"Founder Rights {current_user['username']} viewed vault status for "
        f"{result['username']} ({target_user_id})"
    )

    return result


# ===== Device Overview Endpoint =====

@router.get("/device/overview")
@require_perm("system.view_admin_dashboard")
async def get_device_overview(
    request: Request,
    current_user: dict = Depends(require_founder_rights)
) -> Dict[str, Any]:
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
    # Rate limit: 20/min (300/min in development)
    try:
        from rate_limiter import is_dev_mode
        client_ip = get_client_ip(request)
        max_per_min = 300 if is_dev_mode(request) else 20
        if not rate_limiter.check_rate_limit(f"device_overview:{client_ip}", max_requests=max_per_min, window_seconds=60):
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Max {max_per_min} requests per minute.")
    except Exception as e:
        logger.warning(f"Rate limiting error (continuing anyway): {e}")

    # Audit log (best-effort)
    try:
        audit_logger.log(
            user_id=current_user["user_id"],
            action="admin.device_overview_viewed",
            ip_address=request.client.host if request.client else None,
            details={"admin_username": current_user["username"]}
        )
    except Exception as e:
        logger.error(f"Failed to write audit log for device overview: {e}")

    result = await admin_support.get_device_overview_metrics()

    logger.info(f"Founder Rights {current_user['username']} viewed device overview")
    return result


@router.get("/device-overview")
@require_perm("system.view_admin_dashboard")
async def get_device_overview_alias(request: Request, current_user: dict = Depends(require_founder_rights)) -> Dict[str, Any]:
    """Alias for /device/overview endpoint"""
    return await get_device_overview(request, current_user)


# ===== Workflow Endpoints =====

@router.get("/users/{target_user_id}/workflows")
async def get_user_workflows(
    request: Request,
    target_user_id: str,
    current_user: dict = Depends(require_founder_rights)
) -> Dict[str, Any]:
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

    result = await admin_support.get_user_workflows(target_user_id)

    logger.info(
        f"Founder Rights {current_user['username']} viewed workflows for user {target_user_id}: "
        f"{result['total_workflows']} workflows, {result['total_work_items']} items"
    )

    return result


# ===== Audit Log Endpoints =====

@router.get("/audit/logs")
@require_perm("system.view_audit_logs")
async def get_audit_logs(
    request: Request,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get audit logs with filters (requires system.view_audit_logs permission)

    Query params:
    - user_id: Filter by user
    - action: Filter by action type
    - start_date: ISO format date string (YYYY-MM-DD)
    - end_date: ISO format date string (YYYY-MM-DD)
    - limit: Max results (default 100)
    - offset: Pagination offset (default 0)

    Returns:
    - logs: List of audit log entries
    - total: Total count matching filters
    """
    # Validate date formats
    if start_date:
        from datetime import datetime
        try:
            datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")

    if end_date:
        from datetime import datetime
        try:
            datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

    result = await admin_support.get_audit_logs(
        limit=limit,
        offset=offset,
        user_id=user_id,
        action=action,
        start_date=start_date,
        end_date=end_date
    )

    logger.info(f"User {current_user['username']} queried audit logs: {result['total']} results")
    return result


@router.get("/audit/export")
@require_perm("system.export_audit_logs")
async def export_audit_logs(
    request: Request,
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
) -> Response:
    """
    Export audit logs as CSV (requires system.export_audit_logs permission)

    Query params:
    - user_id: Filter by user
    - start_date: ISO format date string (YYYY-MM-DD)
    - end_date: ISO format date string (YYYY-MM-DD)

    Returns CSV file
    """
    # Validate date formats
    if start_date:
        from datetime import datetime
        try:
            datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")

    if end_date:
        from datetime import datetime
        try:
            datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

    csv_content = await admin_support.export_audit_logs(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )

    logger.info(f"User {current_user['username']} exported audit logs")

    # Return CSV response
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"}
    )
