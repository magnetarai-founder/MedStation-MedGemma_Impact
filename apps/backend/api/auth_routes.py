#!/usr/bin/env python3
"""
Authentication Routes for ElohimOS API
"""

import logging
import os
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from auth_middleware import auth_service, get_current_user, get_current_user_optional

try:
    from .permission_engine import get_permission_engine
except ImportError:
    from permission_engine import get_permission_engine

try:
    from .rate_limiter import rate_limiter, get_client_ip
except ImportError:
    from rate_limiter import rate_limiter, get_client_ip

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
    role: str = Field(default="member", description="User role")
    expires_in: int = Field(default=7 * 24 * 60 * 60, description="Token expiration in seconds")


class UserResponse(BaseModel):
    """User information response"""
    user_id: str
    username: str
    device_id: str
    role: str = Field(default="member", description="User role (member, founder_rights)")


@router.get("/setup-needed")
async def check_setup_needed():
    """Check if initial setup is required (no users exist)"""
    import sqlite3

    try:
        conn = sqlite3.connect(str(auth_service.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()

        return {"setup_needed": count == 0}
    except:
        return {"setup_needed": True}


@router.post("/register", response_model=UserResponse)
async def register(request: Request, body: RegisterRequest):
    """
    Register a new user

    This is the initial setup - creates the first user on the device

    Rate limited to prevent abuse:
    - 5 attempts per hour per IP
    """
    # Rate limit registration attempts (prevent spam/abuse)
    client_ip = get_client_ip(request)
    if not rate_limiter.check_rate_limit(f"auth:register:{client_ip}", max_requests=5, window_seconds=3600):
        raise HTTPException(status_code=429, detail="Too many registration attempts. Please try again later.")

    try:
        user = auth_service.create_user(
            username=body.username,
            password=body.password,
            device_id=body.device_id
        )

        return UserResponse(
            user_id=user.user_id,
            username=user.username,
            device_id=user.device_id,
            role='member'
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, body: LoginRequest):
    """
    Login and receive JWT token

    Rate limited to prevent brute force attacks:
    - 10 attempts per minute per IP
    """
    # Rate limit login attempts (prevent brute force)
    # BUT: Skip rate limiting for privileged accounts:
    # - Founder Rights: Always exempt (hardcoded)
    # - Super Admin: Always exempt (hardcoded)
    # - Admin: Exempt if granted auth.bypass_rate_limit permission
    from auth_middleware import FOUNDER_RIGHTS_USERNAME

    # First check if this is a privileged login attempt
    is_privileged = body.username == FOUNDER_RIGHTS_USERNAME

    # If not founder, check role and permissions
    if not is_privileged:
        try:
            import sqlite3
            conn = sqlite3.connect(str(auth_service.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, role FROM users WHERE username = ?", (body.username,))
            row = cursor.fetchone()
            conn.close()

            if row:
                user_id, role = row

                # Super Admin: always privileged (hardcoded)
                if role == 'super_admin':
                    is_privileged = True

                # Admin: check for bypass permission
                elif role == 'admin':
                    try:
                        perm_engine = get_permission_engine()
                        context = perm_engine.get_user_context(user_id)
                        # Check if admin has been granted bypass permission
                        if context.effective_permissions.get('auth.bypass_rate_limit', False):
                            is_privileged = True
                    except:
                        pass  # If permission check fails, apply rate limiting
        except:
            pass  # If check fails, apply rate limiting as normal

    # Apply rate limiting only to non-privileged accounts
    if not is_privileged:
        client_ip = get_client_ip(request)
        max_login_attempts = 30 if os.getenv("ELOHIM_ENV") == "development" else 10
        if not rate_limiter.check_rate_limit(f"auth:login:{client_ip}", max_requests=max_login_attempts, window_seconds=60):
            raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")

    try:
        auth_result = auth_service.authenticate(
            username=body.username,
            password=body.password,
            device_fingerprint=body.device_fingerprint
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
            device_id=auth_result['device_id'],
            role=auth_result['role']
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
async def logout(request: Request, user: dict = Depends(get_current_user)):
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
        device_id=user['device_id'],
        role=user.get('role', 'member')
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
async def cleanup_expired_sessions(request: Request):
    """
    Cleanup expired sessions (can be called by a cron job)
    """
    try:
        auth_service.cleanup_expired_sessions()
        return {"message": "Expired sessions cleaned up"}
    except Exception as e:
        logger.error(f"Session cleanup failed: {e}")
        raise HTTPException(status_code=500, detail="Cleanup failed")


@router.get("/permissions")
async def get_current_user_permissions(
    team_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Get current user's effective permissions

    Returns a safe, read-only view of the user's effective permissions.
    This endpoint is designed for frontend use to show/hide UI elements
    based on permissions.

    Args:
        team_id: Optional team context for team-specific permissions
        user: Current authenticated user (from token)

    Returns:
        - user_id, username, role
        - permissions: Flat map with enum values converted to JSON-serializable strings
        - profiles, permission_sets

    Never returns internal evaluation details or sensitive data.
    """
    try:
        from permission_engine import get_permission_engine

        engine = get_permission_engine()
        user_ctx = engine.load_user_context(
            user_id=user['user_id'],
            team_id=team_id
        )

        # Convert permissions to JSON-serializable format
        permissions = {}
        for key, value in user_ctx.effective_permissions.items():
            # Convert enum values to strings
            if hasattr(value, 'value'):
                permissions[key] = value.value
            elif isinstance(value, bool):
                permissions[key] = value
            elif isinstance(value, dict):
                permissions[key] = value
            else:
                permissions[key] = str(value)

        return {
            "user_id": user_ctx.user_id,
            "username": user_ctx.username,
            "role": user_ctx.role,
            "permissions": permissions,
            "profiles": user_ctx.profiles,
            "permission_sets": user_ctx.permission_sets
        }

    except Exception as e:
        logger.error(f"Failed to get user permissions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve permissions")
