"""
Authentication service for MagnetarCode.

Provides JWT-based authentication with secure token generation,
validation, and refresh mechanisms.
"""

from .jwt_auth import (
    JWTError,
    TokenData,
    create_access_token,
    create_api_token,
    create_refresh_token,
    refresh_access_token,
    verify_bridge_token,
    verify_token,
)

__all__ = [
    "JWTError",
    "TokenData",
    "create_access_token",
    "create_api_token",
    "create_refresh_token",
    "refresh_access_token",
    "verify_bridge_token",
    "verify_token",
]
