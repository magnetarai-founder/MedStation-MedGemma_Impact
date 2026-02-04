"""
Authentication Context Middleware

Provides user authentication context for API endpoints.
Supports both required and optional authentication modes.
"""

import os
from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from ..services.auth.jwt_auth import JWTError, verify_token


@dataclass
class AuthContext:
    """Authentication context containing user information."""

    user_id: str
    is_authenticated: bool
    token_type: str | None = None  # "jwt" or None for default

    @property
    def is_default_user(self) -> bool:
        """Check if using default (unauthenticated) user."""
        return self.user_id == "default" and not self.is_authenticated


# Default user for unauthenticated requests
DEFAULT_USER_ID = "default"


def get_auth_context(
    authorization: str | None = Header(None),
) -> AuthContext:
    """
    Get authentication context (optional auth).

    For endpoints that work both authenticated and unauthenticated.
    Returns default user if no valid auth provided.

    Usage:
        @router.get("/data")
        async def get_data(auth: AuthContext = Depends(get_auth_context)):
            return {"user_id": auth.user_id, "authenticated": auth.is_authenticated}
    """
    if not authorization:
        return AuthContext(
            user_id=DEFAULT_USER_ID,
            is_authenticated=False,
        )

    # Check for Bearer token format
    if not authorization.startswith("Bearer "):
        return AuthContext(
            user_id=DEFAULT_USER_ID,
            is_authenticated=False,
        )

    token = authorization.replace("Bearer ", "", 1)

    try:
        token_data = verify_token(token, expected_type="access")
        return AuthContext(
            user_id=token_data.sub,
            is_authenticated=True,
            token_type="jwt",
        )
    except JWTError:
        # Invalid token - fall back to default (don't expose error details)
        return AuthContext(
            user_id=DEFAULT_USER_ID,
            is_authenticated=False,
        )


def require_auth_context(
    authorization: str | None = Header(None),
) -> AuthContext:
    """
    Get authentication context (required auth).

    For endpoints that require authentication.
    Raises 401 if no valid auth provided.

    Usage:
        @router.get("/protected")
        async def protected_data(auth: AuthContext = Depends(require_auth_context)):
            return {"user_id": auth.user_id}
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization format (expected: Bearer <token>)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.replace("Bearer ", "", 1)

    try:
        token_data = verify_token(token, expected_type="access")
        return AuthContext(
            user_id=token_data.sub,
            is_authenticated=True,
            token_type="jwt",
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e!s}",
            headers={"WWW-Authenticate": "Bearer"},
        )
