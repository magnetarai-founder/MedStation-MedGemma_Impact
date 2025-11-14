"""
Vault Sharing Routes - File sharing, ACL, invitations, and user management
"""

import logging
import sqlite3
import uuid
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, Form, Depends, Request

from api.auth_middleware import get_current_user
from api.services.vault.core import get_vault_service
from api.rate_limiter import get_client_ip, rate_limiter
from api.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

router = APIRouter()


# ===== File Sharing Endpoints =====

@router.post("/files/{file_id}/share")
async def create_share_link_endpoint(
    request: Request,
    file_id: str,
    vault_type: str = Form("real"),
    password: str = Form(None),
    expires_at: str = Form(None),
    max_downloads: int = Form(None),
    permissions: str = Form("download"),
    one_time: bool = Form(False),
    current_user: Dict = Depends(get_current_user)
):
    """
    Create a shareable link for a file

    Defaults:
    - TTL: 24 hours if expires_at not provided
    - One-time links: Set max_downloads=1 if one_time=True
    """
    # Rate limiting: 10 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:share:create:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=10, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.share.created")

    service = get_vault_service()
    user_id = current_user["user_id"]

    # Apply default 24h TTL if not provided
    if not expires_at:
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        default_expiry = now + timedelta(hours=24)
        expires_at = default_expiry.isoformat()

    # One-time link: force max_downloads=1
    if one_time and max_downloads is None:
        max_downloads = 1

    try:
        result = service.create_share_link(
            user_id, vault_type, file_id, password,
            expires_at, max_downloads, permissions
        )

        # Audit logging after success (don't log full token)
        audit_logger.log(
            user_id=user_id,
            action="vault.share.created",
            resource="vault",
            resource_id=file_id,
            details={
                "file_id": file_id,
                "share_id": result.get("id"),
                "expires_at": expires_at,
                "max_downloads": max_downloads,
                "one_time": one_time
            }
        )

        return result
    except Exception as e:
        logger.error(f"Failed to create share link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{file_id}/shares")
async def get_file_shares_endpoint(
    request: Request,
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Get all share links for a file"""
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:share:list:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.share.list")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        shares = service.get_file_shares(user_id, vault_type, file_id)
        return {"shares": shares}
    except Exception as e:
        logger.error(f"Failed to get file shares: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/shares/{share_id}")
async def revoke_share_link_endpoint(
    request: Request,
    share_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
):
    """Revoke a share link"""
    # Rate limiting: 30 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:share:revoke:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=30, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for vault.share.revoked")

    service = get_vault_service()
    user_id = current_user["user_id"]

    try:
        success = service.revoke_share_link(user_id, vault_type, share_id)
        if not success:
            raise HTTPException(status_code=404, detail="Share link not found")

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.share.revoked",
            resource="vault",
            resource_id=share_id,
            details={"share_id": share_id}
        )

        return {"success": True, "message": "Share link revoked"}
    except Exception as e:
        logger.error(f"Failed to revoke share link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/share/{share_token}")
async def access_share_link_endpoint(
    request: Request,
    share_token: str,
    password: str = None
):
    """
    Access a shared file via share token

    Enforces per-token IP throttles:
    - 5 downloads per minute per IP
    - 50 downloads per day per IP
    """
    service = get_vault_service()

    # Per-token IP throttles
    ip = get_client_ip(request)
    key_min = f"vault:share.download.min:{share_token[:8]}:{ip}"
    key_day = f"vault:share.download.day:{share_token[:8]}:{ip}"

    if not rate_limiter.check_rate_limit(key_min, max_requests=5, window_seconds=60):
        raise HTTPException(
            status_code=429,
            detail={
                "code": "rate_limited",
                "message": "Too many downloads for this link from your IP (1 min)",
                "retry_after": 60
            }
        )

    if not rate_limiter.check_rate_limit(key_day, max_requests=50, window_seconds=86400):
        raise HTTPException(
            status_code=429,
            detail={
                "code": "rate_limited",
                "message": "Too many downloads for this link from your IP (24h)",
                "retry_after": 3600
            }
        )

    try:
        # Get share details
        share_info = service.get_share_link(share_token)

        # Verify password if required
        if share_info["requires_password"]:
            if not password:
                raise HTTPException(
                    status_code=401,
                    detail={"code": "password_required", "message": "Password required"}
                )
            if not service.verify_share_password(share_token, password):
                raise HTTPException(
                    status_code=401,
                    detail={"code": "password_incorrect", "message": "Incorrect password"}
                )

        return share_info
    except ValueError as e:
        error_msg = str(e).lower()

        # Map ValueError messages to consistent error codes
        if "expired" in error_msg:
            raise HTTPException(
                status_code=410,
                detail={"code": "expired", "message": "Share link has expired"}
            )
        elif "download limit" in error_msg or "max" in error_msg:
            raise HTTPException(
                status_code=410,
                detail={"code": "max_downloads_reached", "message": "Download limit reached"}
            )
        else:
            raise HTTPException(
                status_code=404,
                detail={"code": "invalid_token", "message": "Invalid or revoked share token"}
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to access share link (token: {share_token[:6]}...): {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== User Management Endpoints =====

@router.post("/users/register")
async def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    """Register a new user"""
    service = get_vault_service()

    # Generate user ID
    user_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    # Hash password with PBKDF2
    password_key, salt = service._get_encryption_key(password)
    password_hash = base64.b64encode(password_key).decode('utf-8')
    salt_b64 = base64.b64encode(salt).decode('utf-8')

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO vault_users (user_id, username, email, password_hash, salt, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, email, password_hash, salt_b64, now, now))

        conn.commit()

        return {
            "user_id": user_id,
            "username": username,
            "email": email,
            "created_at": now
        }
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"User already exists: {str(e)}")
    finally:
        conn.close()


@router.post("/users/login")
async def login_user(
    username: str = Form(...),
    password: str = Form(...)
):
    """Login user and return user info"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT * FROM vault_users WHERE username = ? AND is_active = 1
        """, (username,))

        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Verify password
        stored_salt = base64.b64decode(user['salt'])
        password_key, _ = service._get_encryption_key(password, stored_salt)
        password_hash = base64.b64encode(password_key).decode('utf-8')

        if password_hash != user['password_hash']:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Update last login
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            UPDATE vault_users SET last_login = ? WHERE user_id = ?
        """, (now, user['user_id']))
        conn.commit()

        return {
            "user_id": user['user_id'],
            "username": user['username'],
            "email": user['email'],
            "last_login": now
        }
    finally:
        conn.close()


# ===== ACL Endpoints =====

@router.post("/acl/grant-file-permission")
async def grant_file_permission(
    file_id: str = Form(...),
    user_id: str = Form(...),
    permission: str = Form(...),
    granted_by: str = Form(...),
    expires_at: Optional[str] = Form(None)
):
    """Grant permission to a user for a specific file"""
    service = get_vault_service()

    if permission not in ['read', 'write', 'delete', 'share']:
        raise HTTPException(status_code=400, detail="Invalid permission type")

    acl_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO vault_file_acl (id, file_id, user_id, permission, granted_by, granted_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (acl_id, file_id, user_id, permission, granted_by, now, expires_at))

        conn.commit()

        return {
            "acl_id": acl_id,
            "file_id": file_id,
            "user_id": user_id,
            "permission": permission,
            "granted_at": now
        }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Permission already exists")
    finally:
        conn.close()


@router.post("/acl/check-permission")
async def check_file_permission(
    file_id: str = Form(...),
    user_id: str = Form(...),
    permission: str = Form(...)
):
    """Check if user has specific permission for a file"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        # Check for unexpired permission
        cursor.execute("""
            SELECT * FROM vault_file_acl
            WHERE file_id = ? AND user_id = ? AND permission = ?
              AND (expires_at IS NULL OR expires_at > datetime('now'))
        """, (file_id, user_id, permission))

        has_permission = cursor.fetchone() is not None

        return {
            "file_id": file_id,
            "user_id": user_id,
            "permission": permission,
            "has_permission": has_permission
        }
    finally:
        conn.close()


@router.get("/acl/file-permissions/{file_id}")
async def get_file_permissions(file_id: str):
    """Get all permissions for a file"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT acl.*, u.username
            FROM vault_file_acl acl
            JOIN vault_users u ON acl.user_id = u.user_id
            WHERE acl.file_id = ?
              AND (acl.expires_at IS NULL OR acl.expires_at > datetime('now'))
        """, (file_id,))

        permissions = []
        for row in cursor.fetchall():
            permissions.append({
                "acl_id": row['id'],
                "user_id": row['user_id'],
                "username": row['username'],
                "permission": row['permission'],
                "granted_by": row['granted_by'],
                "granted_at": row['granted_at'],
                "expires_at": row['expires_at']
            })

        return {"file_id": file_id, "permissions": permissions}
    finally:
        conn.close()


@router.delete("/acl/revoke-permission/{acl_id}")
async def revoke_permission(acl_id: str):
    """Revoke a specific permission"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM vault_file_acl WHERE id = ?", (acl_id,))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Permission not found")

        return {"success": True, "acl_id": acl_id}
    finally:
        conn.close()


# ===== Sharing Invitations =====

@router.post("/sharing/create-invitation")
async def create_sharing_invitation(
    resource_type: str = Form(...),
    resource_id: str = Form(...),
    from_user_id: str = Form(...),
    to_user_email: str = Form(...),
    permission: str = Form(...),
    expires_in_days: int = Form(7)
):
    """Create a sharing invitation"""
    service = get_vault_service()

    if resource_type not in ['file', 'folder']:
        raise HTTPException(status_code=400, detail="Invalid resource type")

    if permission not in ['read', 'write', 'delete', 'share']:
        raise HTTPException(status_code=400, detail="Invalid permission")

    import secrets
    invitation_id = str(uuid.uuid4())
    invitation_token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    expires_at = (now + timedelta(days=expires_in_days)).isoformat()
    now_iso = now.isoformat()

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO vault_share_invitations
            (id, resource_type, resource_id, from_user_id, to_user_email, permission,
             invitation_token, status, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """, (invitation_id, resource_type, resource_id, from_user_id, to_user_email,
              permission, invitation_token, now_iso, expires_at))

        conn.commit()

        return {
            "invitation_id": invitation_id,
            "invitation_token": invitation_token,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "to_user_email": to_user_email,
            "permission": permission,
            "expires_at": expires_at,
            "share_url": f"/api/v1/vault/sharing/accept/{invitation_token}"
        }
    finally:
        conn.close()


@router.post("/sharing/accept/{invitation_token}")
async def accept_sharing_invitation(invitation_token: str, user_id: str = Form(...)):
    """Accept a sharing invitation"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Get invitation
        cursor.execute("""
            SELECT * FROM vault_share_invitations
            WHERE invitation_token = ? AND status = 'pending'
              AND expires_at > datetime('now')
        """, (invitation_token,))

        invitation = cursor.fetchone()

        if not invitation:
            raise HTTPException(status_code=404, detail="Invalid or expired invitation")

        # Create ACL entry
        acl_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        if invitation['resource_type'] == 'file':
            cursor.execute("""
                INSERT INTO vault_file_acl (id, file_id, user_id, permission, granted_by, granted_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (acl_id, invitation['resource_id'], user_id, invitation['permission'],
                  invitation['from_user_id'], now))

        # Update invitation status
        cursor.execute("""
            UPDATE vault_share_invitations
            SET status = 'accepted', accepted_at = ?
            WHERE id = ?
        """, (now, invitation['id']))

        conn.commit()

        return {
            "success": True,
            "resource_type": invitation['resource_type'],
            "resource_id": invitation['resource_id'],
            "permission": invitation['permission']
        }
    finally:
        conn.close()


@router.post("/sharing/decline/{invitation_token}")
async def decline_sharing_invitation(invitation_token: str):
    """Decline a sharing invitation"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE vault_share_invitations
            SET status = 'declined'
            WHERE invitation_token = ? AND status = 'pending'
        """, (invitation_token,))

        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Invitation not found")

        return {"success": True}
    finally:
        conn.close()


@router.get("/sharing/my-invitations")
async def get_my_invitations(user_email: str):
    """Get all pending invitations for a user"""
    service = get_vault_service()

    conn = sqlite3.connect(service.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT i.*, u.username as from_username
            FROM vault_share_invitations i
            JOIN vault_users u ON i.from_user_id = u.user_id
            WHERE i.to_user_email = ? AND i.status = 'pending'
              AND i.expires_at > datetime('now')
            ORDER BY i.created_at DESC
        """, (user_email,))

        invitations = []
        for row in cursor.fetchall():
            invitations.append({
                "invitation_id": row['id'],
                "invitation_token": row['invitation_token'],
                "resource_type": row['resource_type'],
                "resource_id": row['resource_id'],
                "from_username": row['from_username'],
                "permission": row['permission'],
                "created_at": row['created_at'],
                "expires_at": row['expires_at']
            })

        return {"invitations": invitations}
    finally:
        conn.close()
