"""
Cloud Auth - Token Management Routes

Token refresh and cloud status endpoints.
"""

import logging
import sqlite3
from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, HTTPException, Depends, status

from api.auth_middleware import get_current_user, User
from api.utils import get_user_id, get_username
from api.routes.schemas import SuccessResponse
from api.errors import http_401, http_404, http_500

from api.routes.cloud_auth.models import (
    CLOUD_TOKEN_EXPIRY_DAYS,
    CloudTokenRefreshRequest,
    CloudTokenRefreshResponse,
    CloudDeviceInfo,
    CloudStatusResponse,
)
from api.routes.cloud_auth.db import get_db_path
from api.routes.cloud_auth import helpers

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/refresh",
    response_model=SuccessResponse[CloudTokenRefreshResponse],
    status_code=status.HTTP_200_OK,
    summary="Refresh cloud token",
    description="Get a new cloud access token using the refresh token"
)
async def refresh_cloud_token(
    request: CloudTokenRefreshRequest
) -> SuccessResponse[CloudTokenRefreshResponse]:
    """
    Refresh cloud access token using refresh token.

    Note: This endpoint does NOT require JWT authentication.
    It uses the refresh_token for authentication instead, allowing
    token refresh even when the local JWT has expired.
    """
    try:
        with sqlite3.connect(str(get_db_path())) as conn:
            cursor = conn.cursor()

            # Find device by cloud_device_id and verify refresh token
            cursor.execute("""
                SELECT id, cloud_refresh_token_hash, refresh_token_expires_at, is_active
                FROM cloud_devices
                WHERE cloud_device_id = ?
            """, (request.cloud_device_id,))

            row = cursor.fetchone()

            if not row:
                raise http_404("Device not found or not paired", resource="device")

            record_id, stored_hash, refresh_expires, is_active = row

            # Verify device is active
            if not is_active:
                raise http_401("Device has been unpaired. Please re-pair.")

            # Verify refresh token
            if helpers.hash_token(request.refresh_token) != stored_hash:
                helpers.log_sync_operation(request.cloud_device_id, "token_refresh", False, "Invalid refresh token")
                raise http_401("Invalid refresh token")

            # Check refresh token expiry
            if refresh_expires:
                refresh_expires_dt = datetime.fromisoformat(refresh_expires)
                if datetime.now(UTC) > refresh_expires_dt:
                    raise http_401("Refresh token expired. Please re-pair device.")

            # Generate new cloud token
            new_cloud_token = helpers.generate_cloud_token()
            new_expires = datetime.now(UTC) + timedelta(days=CLOUD_TOKEN_EXPIRY_DAYS)

            # Update database
            cursor.execute("""
                UPDATE cloud_devices
                SET cloud_token_hash = ?,
                    token_expires_at = ?
                WHERE id = ?
            """, (
                helpers.hash_token(new_cloud_token),
                new_expires.isoformat(),
                record_id
            ))
            conn.commit()

        helpers.log_sync_operation(request.cloud_device_id, "token_refresh", True)
        logger.info("Cloud token refreshed", extra={"cloud_device_id": request.cloud_device_id})

        return SuccessResponse(
            data=CloudTokenRefreshResponse(
                cloud_token=new_cloud_token,
                expires_at=new_expires.isoformat()
            ),
            message="Cloud token refreshed"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error("Cloud token refresh failed", exc_info=True)
        raise http_500("Failed to refresh cloud token")


@router.get(
    "/status",
    response_model=SuccessResponse[CloudStatusResponse],
    status_code=status.HTTP_200_OK,
    summary="Get cloud connection status",
    description="Check if current user has paired devices and their status"
)
async def get_cloud_status(
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[CloudStatusResponse]:
    """
    Get cloud connection status for current user.

    Returns:
    - Whether any devices are paired
    - List of paired devices with their status
    - Current device's cloud credentials (if paired)
    """
    user_id = get_user_id(current_user)
    username = get_username(current_user)

    try:
        with sqlite3.connect(str(get_db_path())) as conn:
            cursor = conn.cursor()

            # Get all paired devices for user
            cursor.execute("""
                SELECT cloud_device_id, device_name, device_platform,
                       created_at, last_sync_at, is_active, token_expires_at
                FROM cloud_devices
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))

            rows = cursor.fetchall()

            if not rows:
                return SuccessResponse(
                    data=CloudStatusResponse(
                        is_paired=False,
                        paired_devices=[]
                    ),
                    message="No devices paired with cloud"
                )

            # Build device list
            devices = []
            active_device = None

            for row in rows:
                cloud_device_id, name, platform, created, last_sync, active, expires = row
                device_info = CloudDeviceInfo(
                    cloud_device_id=cloud_device_id,
                    device_name=name,
                    device_platform=platform,
                    created_at=created,
                    last_sync_at=last_sync,
                    is_active=bool(active)
                )
                devices.append(device_info)

                # Track first active device for status
                if active and not active_device:
                    active_device = (cloud_device_id, expires, last_sync)

            return SuccessResponse(
                data=CloudStatusResponse(
                    is_paired=bool(active_device),
                    cloud_device_id=active_device[0] if active_device else None,
                    username=username,
                    token_expires_at=active_device[1] if active_device else None,
                    last_sync_at=active_device[2] if active_device else None,
                    paired_devices=devices
                ),
                message="Cloud status retrieved"
            )

    except Exception as e:
        logger.error("Failed to get cloud status", exc_info=True)
        raise http_500("Failed to get cloud status")
