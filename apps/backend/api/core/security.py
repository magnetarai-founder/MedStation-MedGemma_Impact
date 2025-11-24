"""
Security utilities: JWT handling, password hashing, token validation.

Provides:
- JWT token creation and validation
- Password hashing with bcrypt
- Secure token generation
- Device fingerprinting
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
JWT_SECRET_KEY_FILE = ".jwt_secret"
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 7 * 24 * 60  # 7 days
JWT_REFRESH_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days


def get_jwt_secret() -> str:
    """
    Get or create JWT secret key.
    Persists to disk for offline resilience.
    """
    if os.path.exists(JWT_SECRET_KEY_FILE):
        with open(JWT_SECRET_KEY_FILE, 'r') as f:
            return f.read().strip()
    else:
        # Generate new secret
        secret = secrets.token_urlsafe(32)
        with open(JWT_SECRET_KEY_FILE, 'w') as f:
            f.write(secret)
        return secret


JWT_SECRET_KEY = get_jwt_secret()


# Password utilities
def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# JWT utilities
def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data (user_id, username, role, etc.)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Payload data (user_id, username)

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=JWT_REFRESH_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Verify an access token and return payload.

    Args:
        token: JWT access token

    Returns:
        Token payload

    Raises:
        HTTPException: If token is invalid or not an access token
    """
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    return payload


def verify_refresh_token(token: str) -> Dict[str, Any]:
    """
    Verify a refresh token and return payload.

    Args:
        token: JWT refresh token

    Returns:
        Token payload

    Raises:
        HTTPException: If token is invalid or not a refresh token
    """
    payload = decode_token(token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    return payload


def generate_device_fingerprint() -> str:
    """Generate a unique device identifier."""
    return secrets.token_urlsafe(16)
