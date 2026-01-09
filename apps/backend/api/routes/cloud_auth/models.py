"""
Cloud Auth - Models

Pydantic models for cloud authentication and device management.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


# ===== Configuration Constants =====

CLOUD_TOKEN_EXPIRY_DAYS = 7
CLOUD_REFRESH_TOKEN_EXPIRY_DAYS = 30
PAIRING_RATE_LIMIT = 5  # attempts per hour
PAIRING_WINDOW_SECONDS = 3600  # 1 hour


# ===== Device Pairing Models =====

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


# ===== Token Management Models =====

class CloudTokenRefreshRequest(BaseModel):
    """Request to refresh cloud token"""
    cloud_device_id: str = Field(..., description="Cloud device ID")
    refresh_token: str = Field(..., description="Cloud refresh token")


class CloudTokenRefreshResponse(BaseModel):
    """Response with new cloud token"""
    cloud_token: str = Field(..., description="New cloud access token")
    expires_at: str = Field(..., description="New token expiry timestamp")


# ===== Device Info Models =====

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


# ===== Sync Authorization Models =====

class CloudSyncAuthRequest(BaseModel):
    """Request to authorize a sync operation"""
    cloud_token: str = Field(..., description="Cloud access token")
    operation: str = Field(..., description="Sync operation (upload, download, merge)")


class CloudSyncAuthResponse(BaseModel):
    """Sync authorization response"""
    authorized: bool
    sync_session_id: Optional[str] = None
    expires_at: Optional[str] = None
