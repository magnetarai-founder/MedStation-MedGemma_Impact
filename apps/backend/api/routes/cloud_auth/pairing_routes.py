"""
Cloud Auth - Device Pairing Routes

Device pairing and unpairing endpoints.
"""

import logging
import secrets
import sqlite3
from typing import Dict
from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, HTTPException, Depends, Request, Query, status

from api.errors import http_404, http_429, http_500
from api.auth_middleware import get_current_user, User
from api.utils import sanitize_for_log, get_user_id, get_username
from api.rate_limiter import get_client_ip
from api.routes.schemas import SuccessResponse

from api.routes.cloud_auth.models import (
    CLOUD_TOKEN_EXPIRY_DAYS,
    CLOUD_REFRESH_TOKEN_EXPIRY_DAYS,
    CloudPairRequest,
    CloudPairResponse,
)
from api.routes.cloud_auth.db import get_db_path
from api.routes.cloud_auth import helpers

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/pair",
    response_model=SuccessResponse[CloudPairResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Pair device with MagnetarCloud",
    description="Register this device for cloud sync. Rate limited: 5 attempts per hour."
)
async def pair_device(
    request: CloudPairRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[CloudPairResponse]:
    """
    Pair device with MagnetarCloud for sync capabilities.

    Flow:
    1. Validate local JWT (already done via get_current_user)
    2. Check rate limit
    3. Generate cloud_device_id from user + device fingerprint
    4. Generate cloud tokens
    5. Store credentials
    6. Return tokens to client

    Security:
    - Requires valid local JWT
    - Rate limited to prevent abuse
    - Device fingerprint prevents token reuse on different devices
    """
    client_ip = get_client_ip(http_request)

    # Extract user_id from dict or User object (tests may pass User, production returns Dict)
    user_id = get_user_id(current_user)
    username = get_username(current_user)

    # Import at runtime to allow test mocking via api.routes.cloud_auth._check_pairing_rate_limit
    from api.routes import cloud_auth as cloud_auth_pkg
    if not cloud_auth_pkg._check_pairing_rate_limit(user_id, client_ip):
        raise http_429("Too many pairing attempts. Please wait 1 hour.")

    try:
        logger.info(
            "Cloud pairing request",
            extra={
                "user_id": user_id,
                "device_id": sanitize_for_log(request.device_id)
            }
        )

        # Generate cloud credentials
        cloud_device_id = helpers.generate_cloud_device_id(user_id, request.device_fingerprint)
        cloud_token = helpers.generate_cloud_token()
        cloud_refresh_token = helpers.generate_cloud_token()

        # Calculate expiry times
        token_expires = datetime.now(UTC) + timedelta(days=CLOUD_TOKEN_EXPIRY_DAYS)
        refresh_expires = datetime.now(UTC) + timedelta(days=CLOUD_REFRESH_TOKEN_EXPIRY_DAYS)

        with sqlite3.connect(str(get_db_path())) as conn:
            cursor = conn.cursor()

            # Check if device already paired
            cursor.execute("""
                SELECT id, is_active FROM cloud_devices
                WHERE user_id = ? AND device_id = ?
            """, (user_id, request.device_id))

            existing = cursor.fetchone()

            if existing:
                # Re-pair existing device (regenerate tokens)
                record_id = existing[0]
                cursor.execute("""
                    UPDATE cloud_devices
                    SET cloud_device_id = ?,
                        cloud_token_hash = ?,
                        cloud_refresh_token_hash = ?,
                        token_expires_at = ?,
                        refresh_token_expires_at = ?,
                        device_name = COALESCE(?, device_name),
                        device_platform = COALESCE(?, device_platform),
                        is_active = 1
                    WHERE id = ?
                """, (
                    cloud_device_id,
                    helpers.hash_token(cloud_token),
                    helpers.hash_token(cloud_refresh_token),
                    token_expires.isoformat(),
                    refresh_expires.isoformat(),
                    request.device_name,
                    request.device_platform,
                    record_id
                ))
                logger.info("Re-paired existing device", extra={"cloud_device_id": cloud_device_id})
            else:
                # New device pairing
                cursor.execute("""
                    INSERT INTO cloud_devices (
                        id, user_id, device_id, device_name, device_platform,
                        cloud_device_id, cloud_token_hash, cloud_refresh_token_hash,
                        token_expires_at, refresh_token_expires_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    secrets.token_urlsafe(16),
                    user_id,
                    request.device_id,
                    request.device_name,
                    request.device_platform,
                    cloud_device_id,
                    helpers.hash_token(cloud_token),
                    helpers.hash_token(cloud_refresh_token),
                    token_expires.isoformat(),
                    refresh_expires.isoformat(),
                    datetime.now(UTC).isoformat()
                ))
                logger.info("Paired new device", extra={"cloud_device_id": cloud_device_id})

            conn.commit()

        helpers.log_sync_operation(cloud_device_id, "device_pair", True, f"Device paired: {request.device_name or 'unknown'}")

        return SuccessResponse(
            data=CloudPairResponse(
                cloud_device_id=cloud_device_id,
                cloud_token=cloud_token,
                cloud_refresh_token=cloud_refresh_token,
                expires_at=token_expires.isoformat(),
                username=username
            ),
            message="Device paired with MagnetarCloud"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error("Cloud pairing failed", exc_info=True)
        raise http_500("Failed to pair device with cloud")


@router.post(
    "/unpair",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    summary="Unpair device from cloud",
    description="Revoke cloud access for a specific device"
)
async def unpair_device(
    cloud_device_id: str = Query(..., description="Cloud device ID to unpair"),
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Unpair a device from MagnetarCloud.

    This revokes the cloud token for the specified device.
    Users can only unpair their own devices.
    """
    user_id = get_user_id(current_user)

    try:
        with sqlite3.connect(str(get_db_path())) as conn:
            cursor = conn.cursor()

            # Verify ownership
            cursor.execute("""
                SELECT id FROM cloud_devices
                WHERE cloud_device_id = ? AND user_id = ?
            """, (cloud_device_id, user_id))

            row = cursor.fetchone()

            if not row:
                raise http_404("Device not found or not owned by you", resource="device")

            # Deactivate device (soft delete)
            cursor.execute("""
                UPDATE cloud_devices
                SET is_active = 0,
                    cloud_token_hash = '',
                    cloud_refresh_token_hash = ''
                WHERE cloud_device_id = ?
            """, (cloud_device_id,))

            # Invalidate any active sessions
            cursor.execute("""
                DELETE FROM cloud_sessions
                WHERE cloud_device_id = ?
            """, (cloud_device_id,))

            conn.commit()

        helpers.log_sync_operation(cloud_device_id, "device_unpair", True)
        logger.info("Device unpaired", extra={"cloud_device_id": cloud_device_id, "user_id": user_id})

        return SuccessResponse(
            data={"unpaired": True, "cloud_device_id": cloud_device_id},
            message="Device unpaired from MagnetarCloud"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error("Failed to unpair device", exc_info=True)
        raise http_500("Failed to unpair device")
