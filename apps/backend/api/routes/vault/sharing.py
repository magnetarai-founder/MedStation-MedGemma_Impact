"""
Vault Sharing Routes - File sharing, ACL, invitations, and user management

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
import sqlite3
import uuid
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, Form, Depends, Request, status

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user
from api.services.vault.core import get_vault_service
from api.rate_limiter import get_client_ip, rate_limiter
from api.audit_logger import get_audit_logger
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

router = APIRouter()


# ===== File Sharing Endpoints =====

@router.post(
    "/files/{file_id}/share",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="vault_create_share_link",
    summary="Create share link",
    description="Create a shareable link for a file with optional password protection and expiration (rate limited: 10/min)"
)
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
) -> SuccessResponse[Dict]:
    """
    Create a shareable link for a file

    Defaults:
    - TTL: 24 hours if expires_at not provided
    - One-time links: Set max_downloads=1 if one_time=True

    Returns:
        Share link details including token and expiration
    """
    # Rate limiting: 10 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:share:create:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=10, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
                message="Rate limit exceeded for vault.share.created"
            ).model_dump()
        )

    try:
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

        return SuccessResponse(
            data=result,
            message="Share link created successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to create share link", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to create share link"
            ).model_dump()
        )


@router.get(
    "/files/{file_id}/shares",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_get_file_shares",
    summary="Get file share links",
    description="Get all share links for a file (rate limited: 60/min)"
)
async def get_file_shares_endpoint(
    request: Request,
    file_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Get all share links for a file

    Returns:
        List of share links with metadata
    """
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:share:list:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
                message="Rate limit exceeded for vault.share.list"
            ).model_dump()
        )

    try:
        service = get_vault_service()
        user_id = current_user["user_id"]

        shares = service.get_file_shares(user_id, vault_type, file_id)
        shares_data = {"shares": shares}

        return SuccessResponse(
            data=shares_data,
            message=f"Retrieved {len(shares)} share link{'s' if len(shares) != 1 else ''}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get file shares", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve file shares"
            ).model_dump()
        )


@router.delete(
    "/shares/{share_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_revoke_share_link",
    summary="Revoke share link",
    description="Revoke a share link (rate limited: 30/min)"
)
async def revoke_share_link_endpoint(
    request: Request,
    share_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Revoke a share link

    Returns:
        Confirmation of share link revocation
    """
    # Rate limiting: 30 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:share:revoke:{current_user['user_id']}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=30, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
                message="Rate limit exceeded for vault.share.revoked"
            ).model_dump()
        )

    try:
        service = get_vault_service()
        user_id = current_user["user_id"]

        success = service.revoke_share_link(user_id, vault_type, share_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Share link not found"
                ).model_dump()
            )

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.share.revoked",
            resource="vault",
            resource_id=share_id,
            details={"share_id": share_id}
        )

        return SuccessResponse(
            data={"success": True},
            message="Share link revoked"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to revoke share link", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to revoke share link"
            ).model_dump()
        )


@router.get(
    "/share/{share_token}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_access_share_link",
    summary="Access shared file",
    description="Access a shared file via share token - PUBLIC endpoint (rate limited: 5/min per IP, 50/day per IP)"
)
async def access_share_link_endpoint(
    request: Request,
    share_token: str,
    password: str = None
) -> SuccessResponse[Dict]:
    """
    Access a shared file via share token - PUBLIC endpoint

    Enforces per-token IP throttles:
    - 5 downloads per minute per IP
    - 50 downloads per day per IP

    Returns:
        Share link details and file information
    """
    # Per-token IP throttles
    ip = get_client_ip(request)
    key_min = f"vault:share.download.min:{share_token[:8]}:{ip}"
    key_day = f"vault:share.download.day:{share_token[:8]}:{ip}"

    if not rate_limiter.check_rate_limit(key_min, max_requests=5, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "rate_limited",
                "message": "Too many downloads for this link from your IP (1 min)",
                "retry_after": 60
            }
        )

    if not rate_limiter.check_rate_limit(key_day, max_requests=50, window_seconds=86400):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "rate_limited",
                "message": "Too many downloads for this link from your IP (24h)",
                "retry_after": 3600
            }
        )

    try:
        service = get_vault_service()

        # Get share details
        share_info = service.get_share_link(share_token)

        # Verify password if required
        if share_info["requires_password"]:
            if not password:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"code": "password_required", "message": "Password required"}
                )
            if not service.verify_share_password(share_token, password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"code": "password_incorrect", "message": "Incorrect password"}
                )

        return SuccessResponse(
            data=share_info,
            message="Share link accessed successfully"
        )

    except ValueError as e:
        error_msg = str(e).lower()

        # Map ValueError messages to consistent error codes
        if "expired" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail={"code": "expired", "message": "Share link has expired"}
            )
        elif "download limit" in error_msg or "max" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail={"code": "max_downloads_reached", "message": "Download limit reached"}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "invalid_token", "message": "Invalid or revoked share token"}
            )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to access share link (token: {share_token[:6]}...)", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to access share link"
            ).model_dump()
        )


# ===== User Management Endpoints =====

@router.post(
    "/users/register",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="vault_register_user",
    summary="Register user",
    description="Register a new user"
)
async def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
) -> SuccessResponse[Dict]:
    """
    Register a new user

    Returns:
        New user details including user_id
    """
    try:
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

            user_data = {
                "user_id": user_id,
                "username": username,
                "email": email,
                "created_at": now
            }

            return SuccessResponse(
                data=user_data,
                message="User registered successfully"
            )

        except sqlite3.IntegrityError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=f"User already exists: {str(e)}"
                ).model_dump()
            )
        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to register user", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to register user"
            ).model_dump()
        )


@router.post(
    "/users/login",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_login_user",
    summary="Login user",
    description="Login user and return user info"
)
async def login_user(
    username: str = Form(...),
    password: str = Form(...)
) -> SuccessResponse[Dict]:
    """
    Login user and return user info

    Returns:
        User details including last login timestamp
    """
    try:
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
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=ErrorResponse(
                        error_code=ErrorCode.AUTH_ERROR,
                        message="Invalid credentials"
                    ).model_dump()
                )

            # Verify password
            stored_salt = base64.b64decode(user['salt'])
            password_key, _ = service._get_encryption_key(password, stored_salt)
            password_hash = base64.b64encode(password_key).decode('utf-8')

            if password_hash != user['password_hash']:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=ErrorResponse(
                        error_code=ErrorCode.AUTH_ERROR,
                        message="Invalid credentials"
                    ).model_dump()
                )

            # Update last login
            now = datetime.utcnow().isoformat()
            cursor.execute("""
                UPDATE vault_users SET last_login = ? WHERE user_id = ?
            """, (now, user['user_id']))
            conn.commit()

            user_data = {
                "user_id": user['user_id'],
                "username": user['username'],
                "email": user['email'],
                "last_login": now
            }

            return SuccessResponse(
                data=user_data,
                message="User logged in successfully"
            )

        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to login user", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to login user"
            ).model_dump()
        )


# ===== ACL Endpoints =====

@router.post(
    "/acl/grant-file-permission",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="vault_grant_file_permission",
    summary="Grant file permission",
    description="Grant permission to a user for a specific file"
)
async def grant_file_permission(
    file_id: str = Form(...),
    user_id: str = Form(...),
    permission: str = Form(...),
    granted_by: str = Form(...),
    expires_at: Optional[str] = Form(None)
) -> SuccessResponse[Dict]:
    """
    Grant permission to a user for a specific file

    Returns:
        ACL entry details including acl_id
    """
    try:
        service = get_vault_service()

        if permission not in ['read', 'write', 'delete', 'share']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Invalid permission type"
                ).model_dump()
            )

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

            acl_data = {
                "acl_id": acl_id,
                "file_id": file_id,
                "user_id": user_id,
                "permission": permission,
                "granted_at": now
            }

            return SuccessResponse(
                data=acl_data,
                message="File permission granted successfully"
            )

        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Permission already exists"
                ).model_dump()
            )
        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to grant file permission", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to grant file permission"
            ).model_dump()
        )


@router.post(
    "/acl/check-permission",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_check_file_permission",
    summary="Check file permission",
    description="Check if user has specific permission for a file"
)
async def check_file_permission(
    file_id: str = Form(...),
    user_id: str = Form(...),
    permission: str = Form(...)
) -> SuccessResponse[Dict]:
    """
    Check if user has specific permission for a file

    Returns:
        Permission check result with has_permission boolean
    """
    try:
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

            permission_data = {
                "file_id": file_id,
                "user_id": user_id,
                "permission": permission,
                "has_permission": has_permission
            }

            return SuccessResponse(
                data=permission_data,
                message="Permission check completed"
            )

        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to check file permission", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to check file permission"
            ).model_dump()
        )


@router.get(
    "/acl/file-permissions/{file_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_get_file_permissions",
    summary="Get file permissions",
    description="Get all permissions for a file"
)
async def get_file_permissions(file_id: str) -> SuccessResponse[Dict]:
    """
    Get all permissions for a file

    Returns:
        List of active permissions for the file
    """
    try:
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

            permissions_data = {"file_id": file_id, "permissions": permissions}

            return SuccessResponse(
                data=permissions_data,
                message=f"Retrieved {len(permissions)} permission{'s' if len(permissions) != 1 else ''}"
            )

        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get file permissions", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get file permissions"
            ).model_dump()
        )


@router.delete(
    "/acl/revoke-permission/{acl_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_revoke_permission",
    summary="Revoke permission",
    description="Revoke a specific permission"
)
async def revoke_permission(acl_id: str) -> SuccessResponse[Dict]:
    """
    Revoke a specific permission

    Returns:
        Confirmation of permission revocation
    """
    try:
        service = get_vault_service()

        conn = sqlite3.connect(service.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM vault_file_acl WHERE id = ?", (acl_id,))
            conn.commit()

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error_code=ErrorCode.NOT_FOUND,
                        message="Permission not found"
                    ).model_dump()
                )

            return SuccessResponse(
                data={"success": True, "acl_id": acl_id},
                message="Permission revoked successfully"
            )

        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to revoke permission", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to revoke permission"
            ).model_dump()
        )


# ===== Sharing Invitations =====

@router.post(
    "/sharing/create-invitation",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="vault_create_sharing_invitation",
    summary="Create sharing invitation",
    description="Create a sharing invitation for a file or folder"
)
async def create_sharing_invitation(
    resource_type: str = Form(...),
    resource_id: str = Form(...),
    from_user_id: str = Form(...),
    to_user_email: str = Form(...),
    permission: str = Form(...),
    expires_in_days: int = Form(7)
) -> SuccessResponse[Dict]:
    """
    Create a sharing invitation

    Returns:
        Invitation details including token and share URL
    """
    try:
        service = get_vault_service()

        if resource_type not in ['file', 'folder']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Invalid resource type"
                ).model_dump()
            )

        if permission not in ['read', 'write', 'delete', 'share']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Invalid permission"
                ).model_dump()
            )

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

            invitation_data = {
                "invitation_id": invitation_id,
                "invitation_token": invitation_token,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "to_user_email": to_user_email,
                "permission": permission,
                "expires_at": expires_at,
                "share_url": f"/api/v1/vault/sharing/accept/{invitation_token}"
            }

            return SuccessResponse(
                data=invitation_data,
                message="Sharing invitation created successfully"
            )

        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to create sharing invitation", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to create sharing invitation"
            ).model_dump()
        )


@router.post(
    "/sharing/accept/{invitation_token}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_accept_sharing_invitation",
    summary="Accept sharing invitation",
    description="Accept a sharing invitation"
)
async def accept_sharing_invitation(
    invitation_token: str,
    user_id: str = Form(...)
) -> SuccessResponse[Dict]:
    """
    Accept a sharing invitation

    Returns:
        Accepted invitation details including resource info
    """
    try:
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
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error_code=ErrorCode.NOT_FOUND,
                        message="Invalid or expired invitation"
                    ).model_dump()
                )

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

            acceptance_data = {
                "success": True,
                "resource_type": invitation['resource_type'],
                "resource_id": invitation['resource_id'],
                "permission": invitation['permission']
            }

            return SuccessResponse(
                data=acceptance_data,
                message="Sharing invitation accepted successfully"
            )

        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to accept sharing invitation", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to accept sharing invitation"
            ).model_dump()
        )


@router.post(
    "/sharing/decline/{invitation_token}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_decline_sharing_invitation",
    summary="Decline sharing invitation",
    description="Decline a sharing invitation"
)
async def decline_sharing_invitation(invitation_token: str) -> SuccessResponse[Dict]:
    """
    Decline a sharing invitation

    Returns:
        Confirmation of invitation decline
    """
    try:
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
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error_code=ErrorCode.NOT_FOUND,
                        message="Invitation not found"
                    ).model_dump()
                )

            return SuccessResponse(
                data={"success": True},
                message="Sharing invitation declined"
            )

        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to decline sharing invitation", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to decline sharing invitation"
            ).model_dump()
        )


@router.get(
    "/sharing/my-invitations",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_get_my_invitations",
    summary="Get my invitations",
    description="Get all pending invitations for a user"
)
async def get_my_invitations(user_email: str) -> SuccessResponse[Dict]:
    """
    Get all pending invitations for a user

    Returns:
        List of pending invitations
    """
    try:
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

            invitations_data = {"invitations": invitations}

            return SuccessResponse(
                data=invitations_data,
                message=f"Retrieved {len(invitations)} invitation{'s' if len(invitations) != 1 else ''}"
            )

        finally:
            conn.close()

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get invitations", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get invitations"
            ).model_dump()
        )
