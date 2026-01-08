"""
Vault ACL (Access Control List) Routes

Grant, check, and revoke file-level permissions.
"""

import logging
import sqlite3
import uuid
from datetime import datetime, UTC
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Form, status

from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from api.services.vault.core import get_vault_service

logger = logging.getLogger(__name__)

router = APIRouter()


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
    """Grant permission to a user for a specific file"""
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
        now = datetime.now(UTC).isoformat()

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
        logger.error("Failed to grant file permission", exc_info=True)
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
    """Check if user has specific permission for a file"""
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
        logger.error("Failed to check file permission", exc_info=True)
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
    """Get all permissions for a file"""
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
        logger.error("Failed to get file permissions", exc_info=True)
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
    """Revoke a specific permission"""
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
        logger.error("Failed to revoke permission", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to revoke permission"
            ).model_dump()
        )
