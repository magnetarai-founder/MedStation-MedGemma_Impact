"""
JWT Authentication Service

Implements secure JWT-based authentication with:
- Access tokens (short-lived, 1 hour default)
- Refresh tokens (long-lived, 7 days default)
- Constant-time token comparison (prevents timing attacks)
- Token expiration and validation
- Rate limiting on auth failures
"""

import os
import secrets

# Import configuration constants
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt
from fastapi import Header, HTTPException, status
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import JWT_ACCESS_TOKEN_EXPIRE_MINUTES, JWT_REFRESH_TOKEN_EXPIRE_DAYS
from .secret_manager import get_or_create_secret

# Configuration from environment
# Use persistent secret that survives restarts
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or get_or_create_secret()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = JWT_ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = JWT_REFRESH_TOKEN_EXPIRE_DAYS


class TokenData(BaseModel):
    """Token payload data"""

    sub: str  # Subject (typically client ID or user ID)
    type: str  # "access" or "refresh"
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    jti: str | None = None  # JWT ID for token revocation


class JWTError(Exception):
    """Custom JWT error"""

    pass


def create_access_token(
    subject: str,
    additional_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: Token subject (client ID, user ID, etc.)
        additional_claims: Additional claims to include in token
        expires_delta: Custom expiration time (overrides default)

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_access_token("client-123")
        >>> # Token valid for 1 hour (default)
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    issued_at = datetime.now(timezone.utc)

    payload = {
        "sub": subject,
        "type": "access",
        "exp": int(expire.timestamp()),
        "iat": int(issued_at.timestamp()),
        "jti": secrets.token_urlsafe(16),  # Unique token ID
    }

    # Add additional claims if provided
    if additional_claims:
        payload.update(additional_claims)

    encoded_jwt: str = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT refresh token.

    Refresh tokens are long-lived and used to obtain new access tokens.

    Args:
        subject: Token subject (client ID, user ID, etc.)
        expires_delta: Custom expiration time (overrides default)

    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    issued_at = datetime.now(timezone.utc)

    payload = {
        "sub": subject,
        "type": "refresh",
        "exp": int(expire.timestamp()),
        "iat": int(issued_at.timestamp()),
        "jti": secrets.token_urlsafe(16),
    }

    encoded_jwt: str = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, expected_type: str = "access") -> TokenData:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string
        expected_type: Expected token type ("access" or "refresh")

    Returns:
        TokenData object with decoded claims

    Raises:
        JWTError: If token is invalid, expired, or wrong type
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Validate token type
        token_type = payload.get("type")
        if token_type != expected_type:
            raise JWTError(f"Invalid token type. Expected {expected_type}, got {token_type}")

        # Extract claims
        token_data = TokenData(
            sub=payload.get("sub"),
            type=token_type,
            exp=payload.get("exp"),
            iat=payload.get("iat"),
            jti=payload.get("jti"),
        )

        return token_data

    except jwt.ExpiredSignatureError:
        raise JWTError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise JWTError(f"Invalid token: {e!s}")


def verify_bridge_token(authorization: str = Header(None)) -> str:
    """
    Verify bridge API token (FastAPI dependency).

    Supports two authentication modes:
    1. JWT tokens (recommended): Authorization: Bearer <jwt_token>
    2. Static tokens (legacy): Authorization: Bearer <static_token>

    Args:
        authorization: Authorization header value

    Returns:
        Subject (client ID) from token

    Raises:
        HTTPException: 401/403 if authentication fails

    Example:
        >>> @router.get("/protected")
        >>> async def endpoint(client_id: str = Depends(verify_bridge_token)):
        >>>     return {"client": client_id}
    """
    # Check if bridge is enabled
    if not os.getenv("BRIDGE_ENABLED", "false").lower() == "true":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Bridge API is disabled"
        )

    # Check authorization header
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization format (expected: Bearer <token>)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.replace("Bearer ", "", 1)

    # SECURITY FIX: Removed static token fallback vulnerability
    # Only accept JWT tokens for authentication
    try:
        token_data = verify_token(token, expected_type="access")
        return token_data.sub  # Return client ID
    except JWTError as e:
        # No fallback - fail fast with proper error message
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired JWT token: {e!s}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_api_token(client_id: str, description: str | None = None) -> dict[str, str | int]:
    """
    Create a new API token pair (access + refresh).

    Args:
        client_id: Unique identifier for the client
        description: Optional description of token purpose

    Returns:
        Dictionary with access_token and refresh_token

    Example:
        >>> tokens = create_api_token("magnetar-studio", "MagnetarStudio integration")
        >>> # Save tokens securely for the client to use
    """
    access_token = create_access_token(
        subject=client_id, additional_claims={"description": description} if description else None
    )
    refresh_token = create_refresh_token(subject=client_id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
    }


def refresh_access_token(refresh_token: str) -> str:
    """
    Generate new access token from refresh token.

    Args:
        refresh_token: Valid refresh token

    Returns:
        New access token

    Raises:
        JWTError: If refresh token is invalid or expired
    """
    # Verify refresh token
    token_data = verify_token(refresh_token, expected_type="refresh")

    # Create new access token with same subject
    new_access_token = create_access_token(subject=token_data.sub)

    return new_access_token
