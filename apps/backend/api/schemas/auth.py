"""
Authentication & Authorization Pydantic schemas.

Request and response models for:
- Login
- Registration
- Token refresh
- Password change
- Session management
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator


# Request Schemas
class LoginRequest(BaseModel):
    """User login request."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    device_fingerprint: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "username": "user@example.com",
                "password": "SecureP@ssw0rd",
                "device_fingerprint": "device-abc123"
            }
        }


class RegisterRequest(BaseModel):
    """New user registration request."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: Optional[str] = Field(None, pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    device_fingerprint: Optional[str] = None

    @validator('password')
    def validate_password_strength(cls, v) -> str:
        """Ensure password meets security requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "username": "newuser",
                "password": "SecureP@ssw0rd123",
                "email": "user@example.com"
            }
        }


class RefreshTokenRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str = Field(..., description="Valid refresh token")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class ChangePasswordRequest(BaseModel):
    """Password change request."""
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)

    @validator('new_password')
    def validate_password_strength(cls, v) -> str:
        """Ensure new password meets security requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


# Response Schemas
class UserResponse(BaseModel):
    """User information in API responses."""
    id: UUID
    username: str
    email: Optional[str] = None
    role: str
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "user123",
                "email": "user@example.com",
                "role": "member",
                "created_at": "2025-11-23T10:00:00Z",
                "last_login": "2025-11-23T12:30:00Z"
            }
        }


class AuthResponse(BaseModel):
    """Successful authentication response."""
    success: bool = True
    token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    user: UserResponse
    device_id: Optional[str] = None
    expires_in: int = Field(..., description="Token expiration time in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "username": "user123",
                    "role": "member",
                    "created_at": "2025-11-23T10:00:00Z"
                },
                "device_id": "device-abc123",
                "expires_in": 604800
            }
        }


class TokenRefreshResponse(BaseModel):
    """Token refresh response."""
    success: bool = True
    token: str = Field(..., description="New JWT access token")
    refresh_token: str = Field(..., description="New JWT refresh token")
    expires_in: int = Field(..., description="Token expiration time in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "expires_in": 604800
            }
        }


class LogoutResponse(BaseModel):
    """Logout confirmation response."""
    success: bool = True
    message: str = "Logged out successfully"

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Logged out successfully"
            }
        }


class SetupStatusResponse(BaseModel):
    """User setup status response."""
    setup_needed: bool
    user_id: Optional[UUID] = None
    username: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "setup_needed": False,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "user123"
            }
        }
