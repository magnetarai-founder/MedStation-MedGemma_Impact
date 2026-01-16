"""Backward Compatibility Shim - use api.auth instead."""

from api.auth.middleware import (
    AuthService,
    auth_service,
    User,
    get_current_user,
    get_current_user_optional,
    extract_websocket_token,
    verify_websocket_auth,
    _get_or_create_jwt_secret,
    _jwt_secret_warning_shown,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRATION_MINUTES,
    REFRESH_TOKEN_EXPIRATION_DAYS,
    IDLE_TIMEOUT_HOURS,
    logger,
)

__all__ = [
    "AuthService",
    "auth_service",
    "User",
    "get_current_user",
    "get_current_user_optional",
    "extract_websocket_token",
    "verify_websocket_auth",
    "_get_or_create_jwt_secret",
    "JWT_SECRET",
    "JWT_ALGORITHM",
    "JWT_EXPIRATION_MINUTES",
    "REFRESH_TOKEN_EXPIRATION_DAYS",
    "IDLE_TIMEOUT_HOURS",
    "logger",
]
