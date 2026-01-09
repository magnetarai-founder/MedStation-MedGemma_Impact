"""
Cloud Auth Package

MagnetarCloud device pairing, token management, and sync authorization.

This package provides:
- Device pairing/unpairing with cloud
- Cloud token refresh
- Sync session authorization
- Emergency session revocation

Architecture:
- models.py: Pydantic models and constants
- db.py: Database initialization and connection
- helpers.py: Token generation, hashing, rate limiting
- pairing_routes.py: Device pair/unpair endpoints
- token_routes.py: Token refresh and status endpoints
- sync_routes.py: Sync authorization endpoints
"""

from fastapi import APIRouter, Depends

from api.config import is_airgap_mode

# Import sub-routers
from api.routes.cloud_auth.pairing_routes import router as pairing_router
from api.routes.cloud_auth.token_routes import router as token_router
from api.routes.cloud_auth.sync_routes import router as sync_router

# Re-export models for backwards compatibility
from api.routes.cloud_auth.models import (
    CLOUD_TOKEN_EXPIRY_DAYS,
    CLOUD_REFRESH_TOKEN_EXPIRY_DAYS,
    PAIRING_RATE_LIMIT,
    PAIRING_WINDOW_SECONDS,
    CloudPairRequest,
    CloudPairResponse,
    CloudTokenRefreshRequest,
    CloudTokenRefreshResponse,
    CloudSyncAuthRequest,
    CloudSyncAuthResponse,
    CloudDeviceInfo,
    CloudStatusResponse,
)

# Re-export database functions
from api.routes.cloud_auth.db import (
    get_db_path,
    get_connection,
    init_cloud_auth_db,
    CLOUD_DB_PATH,
)

# Alias for backwards compatibility (tests use underscore prefix)
_init_cloud_auth_db = init_cloud_auth_db

# Re-export helpers
from api.routes.cloud_auth.helpers import (
    hash_token,
    generate_cloud_device_id,
    generate_cloud_token,
    check_pairing_rate_limit,
    log_sync_operation,
)

# Aliases for backwards compatibility (tests use underscore prefix)
_hash_token = hash_token
_generate_cloud_device_id = generate_cloud_device_id
_generate_cloud_token = generate_cloud_token
_check_pairing_rate_limit = check_pairing_rate_limit

# Re-export endpoint functions for direct access
from api.routes.cloud_auth.pairing_routes import pair_device, unpair_device
from api.routes.cloud_auth.token_routes import refresh_cloud_token, get_cloud_status
from api.routes.cloud_auth.sync_routes import authorize_sync, revoke_all_sessions


def check_cloud_available():
    """
    Dependency to check if cloud features are available.
    Raises 503 if in airgap mode.
    """
    from fastapi import HTTPException, status
    if is_airgap_mode():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloud features disabled in airgap mode"
        )


# Create main router
router = APIRouter(
    prefix="/api/v1/cloud",
    tags=["cloud-auth"],
    dependencies=[Depends(check_cloud_available)]
)

# Compose sub-routers
router.include_router(pairing_router)
router.include_router(token_router)
router.include_router(sync_router)


# Export all public symbols
__all__ = [
    # Router
    "router",
    # Constants
    "CLOUD_TOKEN_EXPIRY_DAYS",
    "CLOUD_REFRESH_TOKEN_EXPIRY_DAYS",
    "PAIRING_RATE_LIMIT",
    "PAIRING_WINDOW_SECONDS",
    # Models
    "CloudPairRequest",
    "CloudPairResponse",
    "CloudTokenRefreshRequest",
    "CloudTokenRefreshResponse",
    "CloudSyncAuthRequest",
    "CloudSyncAuthResponse",
    "CloudDeviceInfo",
    "CloudStatusResponse",
    # Database
    "get_db_path",
    "get_connection",
    "init_cloud_auth_db",
    "_init_cloud_auth_db",  # Backwards compatibility alias
    "CLOUD_DB_PATH",
    # Helpers
    "hash_token",
    "generate_cloud_device_id",
    "generate_cloud_token",
    "check_pairing_rate_limit",
    "log_sync_operation",
    # Backwards compatibility aliases
    "_hash_token",
    "_generate_cloud_device_id",
    "_generate_cloud_token",
    "_check_pairing_rate_limit",
    # Dependency
    "check_cloud_available",
    # Endpoints
    "pair_device",
    "unpair_device",
    "refresh_cloud_token",
    "get_cloud_status",
    "authorize_sync",
    "revoke_all_sessions",
]
