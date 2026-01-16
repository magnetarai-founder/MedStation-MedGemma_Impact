"""Backward Compatibility Shim - use api.auth instead."""

from api.auth.types import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    ChangePasswordFirstLoginRequest,
    LoginResponse,
    UserResponse,
)

__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "RefreshRequest",
    "ChangePasswordFirstLoginRequest",
    "LoginResponse",
    "UserResponse",
]
