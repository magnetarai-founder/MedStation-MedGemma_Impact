#!/usr/bin/env python3
"""
Authentication Routes for ElohimOS API

Module structure (P2 decomposition):
- auth_types.py: Request/response models
- auth_routes.py: API endpoints (this file)
"""

import logging
import os
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional, Dict, Any
from datetime import UTC

from api.auth.middleware import auth_service, get_current_user, get_current_user_optional
from api.permission_engine import get_permission_engine
from api.rate_limiter import rate_limiter, get_client_ip
from api.error_responses import (
    bad_request, unauthorized, forbidden, too_many_requests,
    internal_error, check_resource_exists
)
from api.error_codes import ErrorCode
from api.query_cache import cache_query, invalidate_query, build_permissions_cache_key

# Import from extracted module (P2 decomposition)
from api.auth.types import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    ChangePasswordFirstLoginRequest,
    LoginResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.get("/setup-needed")
async def check_setup_needed() -> Dict[str, bool]:
    """Check if initial setup is required (no users exist)"""
    import sqlite3

    try:
        conn = sqlite3.connect(str(auth_service.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()

        return {"setup_needed": count == 0}
    except (sqlite3.Error, OSError) as e:
        logger.warning(f"Database check failed, assuming setup needed: {e}")
        return {"setup_needed": True}


@router.post("/register", response_model=UserResponse)
async def register(request: Request, body: RegisterRequest) -> UserResponse:
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
async def login(request: Request, body: LoginRequest) -> LoginResponse:
    """
    Login and receive JWT access token + refresh token

    **MED-05 Security Enhancement:**
    - Access token: 1 hour lifetime (short-lived for security)
    - Refresh token: 30 day lifetime (use to get new access tokens)
    - When access token expires, call `/auth/refresh` with refresh token

    Rate limited to prevent brute force attacks:
    - 10 attempts per minute per IP (dev: 30/min)
    """
    # Rate limit login attempts (prevent brute force)
    # BUT: Skip rate limiting for privileged accounts:
    # - Founder Rights: Always exempt (role='founder_rights')
    # - Super Admin: Always exempt (role='super_admin')
    # - Admin: Exempt if granted auth.bypass_rate_limit permission
    #
    # AUTH-P2: Check role from DB for all users (including Founder)

    is_privileged = False

    # Check user role from DB to determine if rate limiting should be skipped
    try:
        import sqlite3
        conn = sqlite3.connect(str(auth_service.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, role FROM users WHERE username = ?", (body.username,))
        row = cursor.fetchone()
        conn.close()

        if row:
            user_id, role = row

            # Founder Rights: always privileged (AUTH-P2: role-based check)
            if role == 'founder_rights':
                is_privileged = True

            # Super Admin: always privileged
            elif role == 'super_admin':
                is_privileged = True

            # Admin: check for bypass permission
            elif role == 'admin':
                try:
                    perm_engine = get_permission_engine()
                    context = perm_engine.get_user_context(user_id)
                    # Check if admin has been granted bypass permission
                    if context.effective_permissions.get('auth.bypass_rate_limit', False):
                        is_privileged = True
                except Exception as e:
                    logger.debug(f"Permission check failed: {e}")  # Apply rate limiting
    except Exception as e:
        logger.debug(f"Privilege check failed: {e}")  # Apply rate limiting as normal

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


@router.post("/change-password-first-login")
async def change_password_first_login(request: Request, body: ChangePasswordFirstLoginRequest) -> Dict[str, bool]:
    """
    Forced password change after admin reset

    This endpoint is used when a user must change their password after an admin reset.
    It does not require an existing session - only the username and temporary password.

    Rate limited to prevent brute force attacks:
    - 10 attempts per minute per IP
    """
    import re
    import sqlite3
    from datetime import datetime

    # Rate limit password change attempts
    client_ip = get_client_ip(request)
    if not rate_limiter.check_rate_limit(f"auth:change-password:{client_ip}", max_requests=10, window_seconds=60):
        raise too_many_requests(ErrorCode.AUTH_RATE_LIMIT_EXCEEDED, retry_after=60)

    try:
        # Validate password confirmation matches
        if body.new_password != body.confirm_password:
            raise bad_request(ErrorCode.SYSTEM_VALIDATION_FAILED, errors="Passwords do not match")

        # Enforce password complexity (>=12 chars; upper+lower+digit+symbol)
        if len(body.new_password) < 12:
            raise bad_request(ErrorCode.SYSTEM_VALIDATION_FAILED, errors="Password must be at least 12 characters")

        if not re.search(r'[A-Z]', body.new_password):
            raise bad_request(ErrorCode.SYSTEM_VALIDATION_FAILED, errors="Password must contain at least one uppercase letter")

        if not re.search(r'[a-z]', body.new_password):
            raise bad_request(ErrorCode.SYSTEM_VALIDATION_FAILED, errors="Password must contain at least one lowercase letter")

        if not re.search(r'[0-9]', body.new_password):
            raise bad_request(ErrorCode.SYSTEM_VALIDATION_FAILED, errors="Password must contain at least one digit")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', body.new_password):
            raise bad_request(ErrorCode.SYSTEM_VALIDATION_FAILED, errors="Password must contain at least one special character")

        # MED-02: Check password against breach database (HaveIBeenPwned)
        try:
            from password_breach_checker import check_password_breach
            is_breached, breach_count = await check_password_breach(body.new_password)
            if is_breached:
                logger.warning(f"User {body.username} attempted to use breached password (found in {breach_count} breaches)")
                raise bad_request(
                    ErrorCode.SYSTEM_VALIDATION_FAILED,
                    errors=f"This password has been exposed in {breach_count} data breach(es). Please choose a different password."
                )
        except Exception as e:
            # If breach check fails, log but don't block password change
            # (fail open to prevent DOS via API unavailability)
            logger.warning(f"Password breach check failed: {e}")

        # Load user by username
        conn = sqlite3.connect(str(auth_service.db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, password_hash, must_change_password, is_active FROM users WHERE username = ?",
            (body.username,)
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            raise unauthorized(ErrorCode.AUTH_INVALID_CREDENTIALS, message="Invalid username or temporary password")

        user_id, stored_hash, must_change_password, is_active = row

        # Verify user is active
        if not is_active:
            conn.close()
            raise forbidden(ErrorCode.AUTH_ACCOUNT_DISABLED)

        # Check if must_change_password flag is set
        if must_change_password == 0:
            conn.close()
            raise bad_request(ErrorCode.SYSTEM_VALIDATION_FAILED, errors="Password has already been changed")

        # Verify temporary password
        if not auth_service._verify_password(body.temp_password, stored_hash):
            conn.close()
            raise unauthorized(ErrorCode.AUTH_INVALID_CREDENTIALS, message="Invalid username or temporary password")

        # Hash new password with PBKDF2
        new_password_hash, _ = auth_service._hash_password(body.new_password)

        # Update user: set new password hash, clear must_change_password flag, update last_login
        cursor.execute(
            """
            UPDATE users
            SET password_hash = ?, must_change_password = 0, last_login = ?
            WHERE user_id = ?
            """,
            (new_password_hash, datetime.now(UTC).isoformat(), user_id)
        )

        conn.commit()
        conn.close()

        # Audit log
        try:
            from api.audit.logger import get_audit_logger
            from api.audit.actions import AuditAction
            audit_logger = get_audit_logger()
            audit_logger.log(
                user_id=user_id,
                action=AuditAction.PASSWORD_CHANGED,
                resource="user",
                resource_id=user_id,
                details={"username": body.username, "source": "forced_change_after_reset"}
            )
        except Exception as audit_error:
            logger.error(f"Failed to log password change audit: {audit_error}")

        logger.info(f"Password changed successfully for user: {body.username} (forced change after reset)")

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Password change failed")
        raise internal_error(ErrorCode.SYSTEM_INTERNAL_ERROR, technical_detail=str(e))


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(request: Request, body: RefreshRequest) -> LoginResponse:
    """
    MED-05: Refresh access token using refresh token

    When the access token expires (1 hour), use the refresh token (30 days)
    to get a new access token without requiring login again.

    **Security**: Access tokens are short-lived (1 hour) to limit exposure window.
    Use this endpoint to automatically refresh without re-authentication.

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
async def logout(request: Request) -> Dict[str, str]:
    """
    Logout current user - works even with expired tokens

    This endpoint extracts the token without validation so users can log out
    even if their token is expired. The session is deleted from the database.
    """
    try:
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="No token provided",
                headers={"WWW-Authenticate": "Bearer"}
            )

        token = auth_header.replace("Bearer ", "")

        # SECURITY: Verify signature but allow expired tokens for logout
        import jwt
        try:
            from api.auth_middleware import JWT_SECRET, JWT_ALGORITHM
        except ImportError:
            from auth_middleware import JWT_SECRET, JWT_ALGORITHM

        try:
            # SECURITY: Verify signature, but allow expired tokens
            payload = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                options={"verify_exp": False}  # Allow expired, but verify signature
            )
            session_id = payload.get('session_id')
            username = payload.get('username', 'unknown')

            if not session_id:
                # Old token format without session_id - just return success
                logger.info(f"User logged out (old token format): {username}")
                return {"message": "Logged out successfully"}

            # Delete session from database
            import sqlite3
            from config_paths import PATHS

            conn = sqlite3.connect(str(PATHS.app_db))
            cursor = conn.cursor()

            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            deleted = cursor.rowcount
            conn.commit()
            conn.close()

            if deleted > 0:
                logger.info(f"User logged out and session deleted: {username} (session: {session_id})")
            else:
                logger.info(f"User logged out (session not found): {username} (session: {session_id})")

            return {"message": "Logged out successfully"}

        except jwt.InvalidTokenError:
            # Token is malformed or has invalid signature - treat as already logged out
            logger.info("Logout with invalid token - treating as logged out")
            return {"message": "Logged out successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Logout failed")
        raise internal_error(ErrorCode.SYSTEM_INTERNAL_ERROR, technical_detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: Dict[str, Any] = Depends(get_current_user)) -> UserResponse:
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
async def verify_token(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Verify if token is still valid
    """
    return {
        "valid": True,
        "user_id": user['user_id'],
        "username": user['username']
    }


@router.post("/cleanup-sessions")
async def cleanup_expired_sessions(request: Request) -> Dict[str, str]:
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
    user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
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


# Re-exports for backwards compatibility (P2 decomposition)
__all__ = [
    # Router
    "router",
    # Re-exported from auth_types
    "RegisterRequest",
    "LoginRequest",
    "RefreshRequest",
    "ChangePasswordFirstLoginRequest",
    "LoginResponse",
    "UserResponse",
]
