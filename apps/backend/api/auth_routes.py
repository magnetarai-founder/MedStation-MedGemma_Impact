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

try:
    from .error_responses import (
        bad_request, unauthorized, forbidden, too_many_requests,
        internal_error, check_resource_exists
    )
    from .error_codes import ErrorCode
    from .query_cache import cache_query, invalidate_query, build_permissions_cache_key
except ImportError:
    from error_responses import (
        bad_request, unauthorized, forbidden, too_many_requests,
        internal_error, check_resource_exists
    )
    from error_codes import ErrorCode
    from query_cache import cache_query, invalidate_query, build_permissions_cache_key

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


class RefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str = Field(..., description="Refresh token from login")


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
        raise too_many_requests(ErrorCode.AUTH_RATE_LIMIT_EXCEEDED, retry_after=3600)

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
        # Check if user already exists
        if "already exists" in str(e).lower():
            raise bad_request(ErrorCode.AUTH_USER_ALREADY_EXISTS)
        raise bad_request(ErrorCode.SYSTEM_VALIDATION_FAILED, errors=str(e))
    except Exception as e:
        logger.exception("Registration failed")
        raise internal_error(ErrorCode.SYSTEM_INTERNAL_ERROR, technical_detail=str(e))


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
            raise too_many_requests(ErrorCode.AUTH_RATE_LIMIT_EXCEEDED, retry_after=60)

    try:
        auth_result = auth_service.authenticate(
            username=body.username,
            password=body.password,
            device_fingerprint=body.device_fingerprint
        )

        if not auth_result:
            raise unauthorized(ErrorCode.AUTH_INVALID_CREDENTIALS)

        # Check if user must change password (Phase 1B)
        import sqlite3
        conn = sqlite3.connect(str(auth_service.db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT must_change_password FROM users WHERE user_id = ?",
            (auth_result['user_id'],)
        )
        row = cursor.fetchone()
        conn.close()

        must_change_password = False
        if row and len(row) > 0:
            must_change_password = bool(row[0])

        # If must_change_password is set, return error indicating password change required
        if must_change_password:
            raise HTTPException(
                status_code=403,
                detail={
                    "error_code": "AUTH_PASSWORD_CHANGE_REQUIRED",
                    "message": "Password change required. Please use temporary password to set a new password.",
                    "user_id": auth_result['user_id'],
                    "must_change_password": True
                }
            )

        # Return token and user info (no need to decode again)
        # LOW-02: Include refresh token
        return LoginResponse(
            token=auth_result['token'],
            refresh_token=auth_result.get('refresh_token'),  # LOW-02
            user_id=auth_result['user_id'],
            username=auth_result['username'],
            device_id=auth_result['device_id'],
            role=auth_result['role']
        )

    except ValueError as e:
        # Check for account-disabled or other auth errors
        if "disabled" in str(e).lower():
            raise forbidden(ErrorCode.AUTH_ACCOUNT_DISABLED)
        raise forbidden(ErrorCode.AUTH_INVALID_CREDENTIALS)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Login failed")
        raise internal_error(ErrorCode.SYSTEM_INTERNAL_ERROR, technical_detail=str(e))


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(request: Request, body: RefreshRequest):
    """
    LOW-02: Refresh access token using refresh token

    When the access token expires (7 days), use the refresh token (30 days)
    to get a new access token without requiring login again.

    Rate limited to prevent abuse:
    - 10 requests per minute per IP
    """
    client_ip = get_client_ip(request)
    if not rate_limiter.check_rate_limit(f"auth:refresh:{client_ip}", max_requests=10, window_seconds=60):
        raise too_many_requests(ErrorCode.AUTH_RATE_LIMIT_EXCEEDED, retry_after=60)

    try:
        refresh_result = auth_service.refresh_access_token(body.refresh_token)

        if not refresh_result:
            raise unauthorized(ErrorCode.AUTH_INVALID_CREDENTIALS, message="Invalid or expired refresh token")

        return LoginResponse(
            token=refresh_result['token'],
            refresh_token=None,  # Don't return new refresh token (keep existing one)
            user_id=refresh_result['user_id'],
            username=refresh_result['username'],
            device_id=refresh_result['device_id'],
            role=refresh_result['role']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Token refresh failed")
        raise internal_error(ErrorCode.SYSTEM_INTERNAL_ERROR, technical_detail=str(e))


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
        logger.exception("Logout failed")
        raise internal_error(ErrorCode.SYSTEM_INTERNAL_ERROR, technical_detail=str(e))


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
        logger.exception("Session cleanup failed")
        raise internal_error(ErrorCode.SYSTEM_INTERNAL_ERROR, technical_detail=str(e))


@router.get("/permissions")
async def get_current_user_permissions(
    team_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Get current user's effective permissions - Cached for 10 minutes

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

        # Build cache key (include team_id for team-specific permissions)
        cache_key = build_permissions_cache_key(user['user_id'])
        if team_id:
            cache_key = f"{cache_key}_team_{team_id}"

        def fetch_permissions():
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

        # Cache for 10 minutes (permissions rarely change)
        return cache_query(cache_key, fetch_permissions, ttl=600)

    except Exception as e:
        logger.exception("Failed to get user permissions")
        raise internal_error(ErrorCode.SYSTEM_INTERNAL_ERROR, technical_detail=str(e))
