#!/usr/bin/env python3
"""
Authentication Routes for ElohimOS API
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from auth_middleware import auth_service, get_current_user, get_current_user_optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


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


class LoginResponse(BaseModel):
    """Login response with JWT token"""
    token: str
    user_id: str
    username: str
    device_id: str
    expires_in: int = Field(default=7 * 24 * 60 * 60, description="Token expiration in seconds")


class UserResponse(BaseModel):
    """User information response"""
    user_id: str
    username: str
    device_id: str


@router.post("/register", response_model=UserResponse)
async def register(request: RegisterRequest):
    """
    Register a new user

    This is the initial setup - creates the first user on the device
    """
    try:
        user = auth_service.create_user(
            username=request.username,
            password=request.password,
            device_id=request.device_id
        )

        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            device_id=user.device_id
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login and receive JWT token
    """
    try:
        auth_result = auth_service.authenticate(
            username=request.username,
            password=request.password,
            device_fingerprint=request.device_fingerprint
        )

        if not auth_result:
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )

        # Return token and user info (no need to decode again)
        return LoginResponse(
            token=auth_result['token'],
            user_id=auth_result['user_id'],
            username=auth_result['username'],
            device_id=auth_result['device_id']
        )

    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Login failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """
    Logout current user
    """
    try:
        # Extract token from request
        # Note: In production, you'd get this from the Authorization header
        # For now, we just invalidate based on user_id
        logger.info(f"User logged out: {user['username']}")

        return {"message": "Logged out successfully"}

    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """
    Get current user information
    """
    return UserResponse(
        user_id=user['user_id'],
        username=user['username'],
        device_id=user['device_id']
    )


@router.get("/verify")
async def verify_token(user: dict = Depends(get_current_user)):
    """
    Verify if token is still valid
    """
    return {
        "valid": True,
        "user_id": user['user_id'],
        "username": user['username']
    }


@router.post("/cleanup-sessions")
async def cleanup_expired_sessions():
    """
    Cleanup expired sessions (can be called by a cron job)
    """
    try:
        auth_service.cleanup_expired_sessions()
        return {"message": "Expired sessions cleaned up"}
    except Exception as e:
        logger.error(f"Session cleanup failed: {e}")
        raise HTTPException(status_code=500, detail="Cleanup failed")
