"""Backward Compatibility Shim - use api.auth instead."""

from api.auth.routes import router

# Re-export types that were traditionally imported from this module
from api.auth.types import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    ChangePasswordFirstLoginRequest,
    LoginResponse,
    UserResponse,
)

# Re-export middleware functions for backward compatibility
from api.auth.middleware import get_current_user, get_current_user_optional

__all__ = [
    "router",
    "RegisterRequest",
    "LoginRequest",
    "RefreshRequest",
    "ChangePasswordFirstLoginRequest",
    "LoginResponse",
    "UserResponse",
    "get_current_user",
    "get_current_user_optional",
]
