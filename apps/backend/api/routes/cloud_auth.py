"""
MagnetarCloud Authentication Routes

Handles cloud authentication and device pairing for MagnetarCloud sync service.

Security model:
- Device must be authenticated locally first (JWT token required)
- Device pairing creates a long-lived cloud token (7 days)
- Cloud tokens are separate from local JWT tokens (different scope)
- Cloud tokens can be revoked without affecting local access
- Rate limiting on pairing attempts (5 per hour)

Authentication flow:
1. User authenticates locally (JWT token)
2. Device requests cloud pairing with device fingerprint
3. Server generates cloud_token + cloud_device_id
4. Client stores cloud credentials securely (Keychain)
5. Cloud sync uses cloud_token for operations

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
import hashlib
import secrets
import sqlite3
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, UTC
from fastapi import APIRouter, HTTPException, Depends, Request, Query, status
from pydantic import BaseModel, Field
import base64

from api.auth_middleware import get_current_user, User
from api.config_paths import get_config_paths
from api.config import is_airgap_mode
from api.utils import sanitize_for_log, get_user_id, get_username
from api.rate_limiter import rate_limiter, get_client_ip
from api.routes.schemas import SuccessResponse

logger = logging.getLogger(__name__)


# ===== Air-Gap Mode Check =====

async def check_cloud_available():
    """
    Dependency that checks if cloud features are available.

    Raises 503 Service Unavailable when in air-gap mode.
    """
    if is_airgap_mode():
        logger.warning("☁️  Cloud feature requested but air-gap mode is enabled")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "cloud_unavailable",
                "message": "Cloud features are disabled in air-gap mode",
                "hint": "Set ELOHIMOS_AIRGAP_MODE=false to enable cloud features"
            }
        )


router = APIRouter(
    prefix="/api/v1/cloud",
    tags=["cloud-auth"],
    dependencies=[Depends(check_cloud_available)]
)

# Database path (uses vault.db for consistency)
PATHS = get_config_paths()
CLOUD_DB_PATH = PATHS.data_dir / "vault.db"

# Cloud token configuration
CLOUD_TOKEN_EXPIRY_DAYS = 7
CLOUD_REFRESH_TOKEN_EXPIRY_DAYS = 30
PAIRING_RATE_LIMIT = 5  # attempts per hour
PAIRING_WINDOW_SECONDS = 3600  # 1 hour


# ===== Database Initialization =====

def _init_cloud_auth_db() -> None:
    """Initialize cloud auth tables"""
    CLOUD_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(CLOUD_DB_PATH)) as conn:
        cursor = conn.cursor()

        # Cloud device registrations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cloud_devices (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                device_name TEXT,
                device_platform TEXT,

                -- Cloud credentials
                cloud_device_id TEXT NOT NULL UNIQUE,
                cloud_token_hash TEXT NOT NULL,
                cloud_refresh_token_hash TEXT,

                -- Token expiry
                token_expires_at TEXT NOT NULL,
                refresh_token_expires_at TEXT,

                -- Metadata
                created_at TEXT NOT NULL,
                last_sync_at TEXT,
                is_active INTEGER DEFAULT 1,

                UNIQUE(user_id, device_id)
            )
        """)

        # Cloud sessions (active sync sessions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cloud_sessions (
                id TEXT PRIMARY KEY,
                cloud_device_id TEXT NOT NULL,
                session_token_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_activity TEXT,

                FOREIGN KEY (cloud_device_id) REFERENCES cloud_devices(cloud_device_id)
            )
        """)

        # Cloud sync audit log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cloud_sync_log (
                id TEXT PRIMARY KEY,
                cloud_device_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                success INTEGER NOT NULL,
                details TEXT,

                FOREIGN KEY (cloud_device_id) REFERENCES cloud_devices(cloud_device_id)
            )
        """)

        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cloud_devices_user
            ON cloud_devices(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cloud_devices_active
            ON cloud_devices(is_active, user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cloud_sessions_device
            ON cloud_sessions(cloud_device_id)
        """)

        conn.commit()


# Initialize on module load
_init_cloud_auth_db()


# ===== Request/Response Models =====

class CloudPairRequest(BaseModel):
    """Request to pair device with MagnetarCloud"""
    device_id: str = Field(..., description="Local device UUID")
    device_name: Optional[str] = Field(None, description="Human-readable device name")
    device_platform: Optional[str] = Field(None, description="Device platform (macos, ios, etc)")
    device_fingerprint: str = Field(..., description="Device fingerprint (hardware ID hash)")


class CloudPairResponse(BaseModel):
    """Response with cloud credentials"""
    cloud_device_id: str = Field(..., description="Cloud-assigned device ID")
    cloud_token: str = Field(..., description="Cloud access token (use for sync)")
    cloud_refresh_token: str = Field(..., description="Cloud refresh token (use to renew)")
    expires_at: str = Field(..., description="Token expiry timestamp (ISO 8601)")
    username: str = Field(..., description="Cloud username")


class CloudTokenRefreshRequest(BaseModel):
    """Request to refresh cloud token"""
    cloud_device_id: str = Field(..., description="Cloud device ID")
    refresh_token: str = Field(..., description="Cloud refresh token")


class CloudTokenRefreshResponse(BaseModel):
    """Response with new cloud token"""
    cloud_token: str = Field(..., description="New cloud access token")
    expires_at: str = Field(..., description="New token expiry timestamp")


class CloudDeviceInfo(BaseModel):
    """Information about a paired cloud device"""
    cloud_device_id: str
    device_name: Optional[str]
    device_platform: Optional[str]
    created_at: str
    last_sync_at: Optional[str]
    is_active: bool


class CloudStatusResponse(BaseModel):
    """Cloud connection status"""
    is_paired: bool
    cloud_device_id: Optional[str] = None
    username: Optional[str] = None
    token_expires_at: Optional[str] = None
    last_sync_at: Optional[str] = None
    paired_devices: List[CloudDeviceInfo] = []


class CloudSyncAuthRequest(BaseModel):
    """Request to authorize a sync operation"""
    cloud_token: str = Field(..., description="Cloud access token")
    operation: str = Field(..., description="Sync operation (upload, download, merge)")


class CloudSyncAuthResponse(BaseModel):
    """Sync authorization response"""
    authorized: bool
    sync_session_id: Optional[str] = None
    expires_at: Optional[str] = None


# ===== Helper Functions =====

def _hash_token(token: str) -> str:
    """Hash token for secure storage using SHA-256"""
    return hashlib.sha256(token.encode()).hexdigest()


def _generate_cloud_device_id(user_id: str, device_fingerprint: str) -> str:
    """Generate deterministic cloud device ID from user and device fingerprint"""
    combined = f"{user_id}:{device_fingerprint}"
    hash_bytes = hashlib.sha256(combined.encode()).digest()
    return base64.urlsafe_b64encode(hash_bytes[:16]).decode().rstrip('=')


def _generate_cloud_token() -> str:
    """Generate a secure cloud token"""
    return secrets.token_urlsafe(48)


def _check_pairing_rate_limit(user_id: str, client_ip: str) -> bool:
    """Check cloud pairing rate limit (5 attempts per hour)"""
    rate_key = f"cloud_pair:{user_id}:{client_ip}"
    return rate_limiter.check_rate_limit(rate_key, max_requests=PAIRING_RATE_LIMIT, window_seconds=PAIRING_WINDOW_SECONDS)


def _log_sync_operation(cloud_device_id: str, operation: str, success: bool, details: str = None) -> None:
    """Log a sync operation for audit"""
    try:
        with sqlite3.connect(str(CLOUD_DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cloud_sync_log (id, cloud_device_id, operation, timestamp, success, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                secrets.token_urlsafe(16),
                cloud_device_id,
                operation,
                datetime.now(UTC).isoformat(),
                1 if success else 0,
                details
            ))
            conn.commit()
    except Exception as e:
        logger.warning(f"Failed to log sync operation: {e}")


# ===== Endpoints =====

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

    if not _check_pairing_rate_limit(user_id, client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many pairing attempts. Please wait 1 hour."
        )

    try:
        logger.info(
            "Cloud pairing request",
            extra={
                "user_id": user_id,
                "device_id": sanitize_for_log(request.device_id)
            }
        )

        # Generate cloud credentials
        cloud_device_id = _generate_cloud_device_id(user_id, request.device_fingerprint)
        cloud_token = _generate_cloud_token()
        cloud_refresh_token = _generate_cloud_token()

        # Calculate expiry times
        token_expires = datetime.now(UTC) + timedelta(days=CLOUD_TOKEN_EXPIRY_DAYS)
        refresh_expires = datetime.now(UTC) + timedelta(days=CLOUD_REFRESH_TOKEN_EXPIRY_DAYS)

        with sqlite3.connect(str(CLOUD_DB_PATH)) as conn:
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
                    _hash_token(cloud_token),
                    _hash_token(cloud_refresh_token),
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
                    _hash_token(cloud_token),
                    _hash_token(cloud_refresh_token),
                    token_expires.isoformat(),
                    refresh_expires.isoformat(),
                    datetime.now(UTC).isoformat()
                ))
                logger.info("Paired new device", extra={"cloud_device_id": cloud_device_id})

            conn.commit()

        _log_sync_operation(cloud_device_id, "device_pair", True, f"Device paired: {request.device_name or 'unknown'}")

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pair device with cloud"
        )


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
        with sqlite3.connect(str(CLOUD_DB_PATH)) as conn:
            cursor = conn.cursor()

            # Find device by cloud_device_id and verify refresh token
            cursor.execute("""
                SELECT id, cloud_refresh_token_hash, refresh_token_expires_at, is_active
                FROM cloud_devices
                WHERE cloud_device_id = ?
            """, (request.cloud_device_id,))

            row = cursor.fetchone()

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Device not found or not paired"
                )

            record_id, stored_hash, refresh_expires, is_active = row

            # Verify device is active
            if not is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Device has been unpaired. Please re-pair."
                )

            # Verify refresh token
            if _hash_token(request.refresh_token) != stored_hash:
                _log_sync_operation(request.cloud_device_id, "token_refresh", False, "Invalid refresh token")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )

            # Check refresh token expiry
            if refresh_expires:
                refresh_expires_dt = datetime.fromisoformat(refresh_expires)
                if datetime.now(UTC) > refresh_expires_dt:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Refresh token expired. Please re-pair device."
                    )

            # Generate new cloud token
            new_cloud_token = _generate_cloud_token()
            new_expires = datetime.now(UTC) + timedelta(days=CLOUD_TOKEN_EXPIRY_DAYS)

            # Update database
            cursor.execute("""
                UPDATE cloud_devices
                SET cloud_token_hash = ?,
                    token_expires_at = ?
                WHERE id = ?
            """, (
                _hash_token(new_cloud_token),
                new_expires.isoformat(),
                record_id
            ))
            conn.commit()

        _log_sync_operation(request.cloud_device_id, "token_refresh", True)
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh cloud token"
        )


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
        with sqlite3.connect(str(CLOUD_DB_PATH)) as conn:
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cloud status"
        )


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
        with sqlite3.connect(str(CLOUD_DB_PATH)) as conn:
            cursor = conn.cursor()

            # Verify ownership
            cursor.execute("""
                SELECT id FROM cloud_devices
                WHERE cloud_device_id = ? AND user_id = ?
            """, (cloud_device_id, user_id))

            row = cursor.fetchone()

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Device not found or not owned by you"
                )

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

        _log_sync_operation(cloud_device_id, "device_unpair", True)
        logger.info("Device unpaired", extra={"cloud_device_id": cloud_device_id, "user_id": user_id})

        return SuccessResponse(
            data={"unpaired": True, "cloud_device_id": cloud_device_id},
            message="Device unpaired from MagnetarCloud"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error("Failed to unpair device", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unpair device"
        )


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
        with sqlite3.connect(str(CLOUD_DB_PATH)) as conn:
            cursor = conn.cursor()

            # Find device by token
            cursor.execute("""
                SELECT cloud_device_id, token_expires_at, is_active
                FROM cloud_devices
                WHERE cloud_token_hash = ?
            """, (_hash_token(request.cloud_token),))

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
                _hash_token(session_id),
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

        _log_sync_operation(cloud_device_id, f"sync_authorize:{request.operation}", True)
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to authorize sync"
        )


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
        with sqlite3.connect(str(CLOUD_DB_PATH)) as conn:
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
                _log_sync_operation(device_id, "emergency_revoke", True, f"User: {user_id}")

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke cloud sessions"
        )
