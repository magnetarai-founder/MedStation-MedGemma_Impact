"""
Vault Sharing Invitations Routes

Create, accept, decline, and list sharing invitations.
"""

import logging
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, UTC
from typing import Dict

from fastapi import APIRouter, HTTPException, Form, status

from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from api.errors import http_400, http_404, http_500
from api.services.vault.core import get_vault_service

logger = logging.getLogger(__name__)

router = APIRouter()


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
    """Create a sharing invitation"""
    try:
        service = get_vault_service()

        if resource_type not in ['file', 'folder']:
            raise http_400("Invalid resource type")

        if permission not in ['read', 'write', 'delete', 'share']:
            raise http_400("Invalid permission")

        invitation_id = str(uuid.uuid4())
        invitation_token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
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
        logger.error("Failed to create sharing invitation", exc_info=True)
        raise http_500("Failed to create sharing invitation")


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
    """Accept a sharing invitation"""
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
                raise http_404("Invalid or expired invitation", resource="invitation")

            # Create ACL entry
            acl_id = str(uuid.uuid4())
            now = datetime.now(UTC).isoformat()

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
        logger.error("Failed to accept sharing invitation", exc_info=True)
        raise http_500("Failed to accept sharing invitation")


@router.post(
    "/sharing/decline/{invitation_token}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_decline_sharing_invitation",
    summary="Decline sharing invitation",
    description="Decline a sharing invitation"
)
async def decline_sharing_invitation(invitation_token: str) -> SuccessResponse[Dict]:
    """Decline a sharing invitation"""
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
                raise http_404("Invitation not found", resource="invitation")

            return SuccessResponse(
                data={"success": True},
                message="Sharing invitation declined"
            )

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to decline sharing invitation", exc_info=True)
        raise http_500("Failed to decline sharing invitation")


@router.get(
    "/sharing/my-invitations",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_get_my_invitations",
    summary="Get my invitations",
    description="Get all pending invitations for a user"
)
async def get_my_invitations(user_email: str) -> SuccessResponse[Dict]:
    """Get all pending invitations for a user"""
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
        logger.error("Failed to get invitations", exc_info=True)
        raise http_500("Failed to get invitations")
