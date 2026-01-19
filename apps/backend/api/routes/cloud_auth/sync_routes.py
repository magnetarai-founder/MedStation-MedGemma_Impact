"""
Cloud Auth - Sync Authorization Routes

Sync session authorization and emergency logout.
"""

import logging
import secrets
import sqlite3
from typing import Dict
from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, HTTPException, Depends, status

from api.auth_middleware import get_current_user, User
from api.utils import get_user_id
from api.routes.schemas import SuccessResponse
from api.errors import http_500

from api.routes.cloud_auth.models import (
    CloudSyncAuthRequest,
    CloudSyncAuthResponse,
)
from api.routes.cloud_auth.db import get_db_path
from api.routes.cloud_auth import helpers

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/sync/authorize",
    response_model=SuccessResponse[CloudSyncAuthResponse],
    status_code=status.HTTP_200_OK,
    summary="Authorize sync operation",
    description="Get authorization for a sync operation (upload/download/merge)"
)
async def authorize_sync(
    request: CloudSyncAuthRequest
) -> SuccessResponse[CloudSyncAuthResponse]:
    """
    Authorize a cloud sync operation.

    This endpoint validates the cloud token and creates a time-limited
    sync session for the requested operation.

    Note: Does NOT require JWT - uses cloud_token for auth.
    """
    try:
        with sqlite3.connect(str(get_db_path())) as conn:
            cursor = conn.cursor()

            # Find device by token
            cursor.execute("""
                SELECT cloud_device_id, token_expires_at, is_active
                FROM cloud_devices
                WHERE cloud_token_hash = ?
            """, (helpers.hash_token(request.cloud_token),))

            row = cursor.fetchone()

            if not row:
                return SuccessResponse(
                    data=CloudSyncAuthResponse(authorized=False),
                    message="Invalid or expired cloud token"
                )

            cloud_device_id, expires_at, is_active = row

            # Verify device is active
            if not is_active:
                return SuccessResponse(
                    data=CloudSyncAuthResponse(authorized=False),
                    message="Device has been unpaired"
                )

            # Check token expiry
            if expires_at:
                expires_dt = datetime.fromisoformat(expires_at)
                if datetime.now(UTC) > expires_dt:
                    return SuccessResponse(
                        data=CloudSyncAuthResponse(authorized=False),
                        message="Cloud token expired. Please refresh."
                    )

            # Create sync session (valid for 1 hour)
            session_id = secrets.token_urlsafe(32)
            session_expires = datetime.now(UTC) + timedelta(hours=1)

            cursor.execute("""
                INSERT INTO cloud_sessions (id, cloud_device_id, session_token_hash, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                secrets.token_urlsafe(16),
                cloud_device_id,
                helpers.hash_token(session_id),
                datetime.now(UTC).isoformat(),
                session_expires.isoformat()
            ))

            # Update last activity on device
            cursor.execute("""
                UPDATE cloud_devices
                SET last_sync_at = ?
                WHERE cloud_device_id = ?
            """, (datetime.now(UTC).isoformat(), cloud_device_id))

            conn.commit()

        helpers.log_sync_operation(cloud_device_id, f"sync_authorize:{request.operation}", True)
        logger.info("Sync authorized", extra={"cloud_device_id": cloud_device_id, "operation": request.operation})

        return SuccessResponse(
            data=CloudSyncAuthResponse(
                authorized=True,
                sync_session_id=session_id,
                expires_at=session_expires.isoformat()
            ),
            message="Sync operation authorized"
        )

    except Exception as e:
        logger.error("Sync authorization failed", exc_info=True)
        raise http_500("Failed to authorize sync")


@router.delete(
    "/sessions",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    summary="Revoke all cloud sessions",
    description="Revoke all cloud sessions for all devices (emergency logout)"
)
async def revoke_all_sessions(
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Revoke all cloud sessions for all devices.

    Emergency logout - use when you suspect a device has been compromised.
    This immediately invalidates all cloud tokens and sessions.
    """
    user_id = get_user_id(current_user)

    try:
        with sqlite3.connect(str(get_db_path())) as conn:
            cursor = conn.cursor()

            # Get all device IDs for user
            cursor.execute("""
                SELECT cloud_device_id FROM cloud_devices
                WHERE user_id = ?
            """, (user_id,))

            device_ids = [row[0] for row in cursor.fetchall()]

            # Invalidate all tokens
            cursor.execute("""
                UPDATE cloud_devices
                SET cloud_token_hash = '',
                    cloud_refresh_token_hash = '',
                    is_active = 0
                WHERE user_id = ?
            """, (user_id,))

            # Delete all sessions
            for device_id in device_ids:
                cursor.execute("""
                    DELETE FROM cloud_sessions
                    WHERE cloud_device_id = ?
                """, (device_id,))
                helpers.log_sync_operation(device_id, "emergency_revoke", True, f"User: {user_id}")

            conn.commit()

        logger.warning(
            "All cloud sessions revoked",
            extra={"user_id": user_id, "devices_affected": len(device_ids)}
        )

        return SuccessResponse(
            data={"revoked": True, "devices_affected": len(device_ids)},
            message=f"All cloud sessions revoked ({len(device_ids)} devices)"
        )

    except Exception as e:
        logger.error("Failed to revoke cloud sessions", exc_info=True)
        raise http_500("Failed to revoke cloud sessions")
