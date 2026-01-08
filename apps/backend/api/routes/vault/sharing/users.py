"""
Vault User Management Routes

User registration and login for vault access.
"""

import base64
import hashlib
import logging
import os
import sqlite3
import uuid
from datetime import datetime, UTC
from typing import Dict

from fastapi import APIRouter, HTTPException, Form, status

from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from api.services.vault.core import get_vault_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/users/register",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="vault_register_user",
    summary="Register user",
    description="Register a new user"
)
async def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
) -> SuccessResponse[Dict]:
    """Register a new user"""
    try:
        service = get_vault_service()

        # Generate user ID
        user_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        # Hash password with PBKDF2 (OWASP 2023: 600k iterations)
        salt = os.urandom(32)  # Unique salt per user
        password_key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            600000,  # OWASP 2023 recommended iterations
            dklen=32
        )
        password_hash = base64.b64encode(password_key).decode('utf-8')
        salt_b64 = base64.b64encode(salt).decode('utf-8')

        conn = sqlite3.connect(service.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO vault_users (user_id, username, email, password_hash, salt, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, email, password_hash, salt_b64, now, now))

            conn.commit()

            user_data = {
                "user_id": user_id,
                "username": username,
                "email": email,
                "created_at": now
            }

            return SuccessResponse(
                data=user_data,
                message="User registered successfully"
            )

        except sqlite3.IntegrityError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=f"User already exists: {str(e)}"
                ).model_dump()
            )
        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to register user", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to register user"
            ).model_dump()
        )


@router.post(
    "/users/login",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_login_user",
    summary="Login user",
    description="Login user and return user info"
)
async def login_user(
    username: str = Form(...),
    password: str = Form(...)
) -> SuccessResponse[Dict]:
    """Login user and return user info"""
    try:
        service = get_vault_service()

        conn = sqlite3.connect(service.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM vault_users WHERE username = ? AND is_active = 1
            """, (username,))

            user = cursor.fetchone()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=ErrorResponse(
                        error_code=ErrorCode.UNAUTHORIZED,
                        message="Invalid credentials"
                    ).model_dump()
                )

            # Verify password with PBKDF2
            stored_salt = base64.b64decode(user['salt'])
            password_key = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                stored_salt,
                600000,  # Must match registration iterations
                dklen=32
            )
            password_hash = base64.b64encode(password_key).decode('utf-8')

            if password_hash != user['password_hash']:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=ErrorResponse(
                        error_code=ErrorCode.UNAUTHORIZED,
                        message="Invalid credentials"
                    ).model_dump()
                )

            # Update last login
            now = datetime.now(UTC).isoformat()
            cursor.execute("""
                UPDATE vault_users SET last_login = ? WHERE user_id = ?
            """, (now, user['user_id']))
            conn.commit()

            user_data = {
                "user_id": user['user_id'],
                "username": user['username'],
                "email": user['email'],
                "last_login": now
            }

            return SuccessResponse(
                data=user_data,
                message="User logged in successfully"
            )

        finally:
            conn.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to login user", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to login user"
            ).model_dump()
        )
