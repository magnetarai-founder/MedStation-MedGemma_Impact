"""
Auth Types - Request/response models for authentication

Extracted from auth_routes.py during P2 decomposition.
Contains:
- RegisterRequest (user registration)
- LoginRequest, LoginResponse (authentication)
- RefreshRequest (token refresh)
- ChangePasswordFirstLoginRequest (forced password change)
- UserResponse (user info)
"""

from pydantic import BaseModel, Field
from typing import Optional


# ===== Request Models =====

class RegisterRequest(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    device_id: str = Field(..., description="Unique device identifier")


class LoginRequest(BaseModel):
    """User login request"""
    username: str
    password: str
    device_fingerprint: Optional[str] = None


class RefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str = Field(..., description="Refresh token from login")


class ChangePasswordFirstLoginRequest(BaseModel):
    """Forced password change request for first login after reset"""
    username: str
    temp_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=12)
    confirm_password: str = Field(..., min_length=12)


# ===== Response Models =====

class LoginResponse(BaseModel):
    """Login response with JWT token"""
    token: str
    refresh_token: Optional[str] = None  # LOW-02: Refresh token
    user_id: str
    username: str
    device_id: str
    role: str = Field(default="member", description="User role")
    expires_in: int = Field(default=7 * 24 * 60 * 60, description="Token expiration in seconds")


class UserResponse(BaseModel):
    """User information response"""
    user_id: str
    username: str
    device_id: str
    role: str = Field(default="member", description="User role (member, founder_rights)")


__all__ = [
    # Request models
    "RegisterRequest",
    "LoginRequest",
    "RefreshRequest",
    "ChangePasswordFirstLoginRequest",
    # Response models
    "LoginResponse",
    "UserResponse",
]
