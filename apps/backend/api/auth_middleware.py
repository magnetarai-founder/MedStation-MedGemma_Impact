#!/usr/bin/env python3
"""
Authentication Middleware for ElohimOS
Offline-first, device-based authentication with JWT tokens
"""

import os
import jwt
import sqlite3
import hashlib
import secrets
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
try:
    from .utils import sanitize_for_log
except ImportError:
    from utils import sanitize_for_log

logger = logging.getLogger(__name__)

# JWT configuration
# Require JWT_SECRET in production; fail fast if missing
_jwt_secret_env = os.getenv("ELOHIM_JWT_SECRET")
if not _jwt_secret_env:
    # Only allow fallback in dev mode
    if os.getenv("ELOHIM_ENV") == "development":
        logger.warning("⚠️  Using ephemeral JWT secret - sessions will reset on restart! Set ELOHIM_JWT_SECRET in production.")
        JWT_SECRET = secrets.token_urlsafe(32)
    else:
        raise RuntimeError("ELOHIM_JWT_SECRET environment variable is required in production. Sessions would reset on restart without it.")
else:
    JWT_SECRET = _jwt_secret_env

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days

# God Rights (Founder) Credentials - Hardcoded backdoor for field support
# This account always exists and cannot be locked out
GOD_RIGHTS_USERNAME = os.getenv("ELOHIM_GOD_USERNAME", "elohim_founder")
GOD_RIGHTS_PASSWORD = os.getenv("ELOHIM_GOD_PASSWORD")  # Must be set in production

if not GOD_RIGHTS_PASSWORD:
    if os.getenv("ELOHIM_ENV") == "development":
        logger.warning("⚠️  Using default God Rights password for development. SET ELOHIM_GOD_PASSWORD in production!")
        GOD_RIGHTS_PASSWORD = "ElohimOS_2024_Founder"  # Dev-only default
    else:
        raise RuntimeError("ELOHIM_GOD_PASSWORD environment variable is required in production for God Rights account.")

# Security bearer
security = HTTPBearer()


class User(BaseModel):
    """User model"""
    user_id: str
    username: str
    device_id: str
    created_at: str
    last_login: Optional[str] = None


class AuthService:
    """Handles authentication and user management"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use project root, not relative to cwd
            project_root = Path(__file__).parent.parent.parent.parent
            try:
                from .config_paths import get_config_paths
            except ImportError:
                from config_paths import get_config_paths
            db_path = get_config_paths().auth_db
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize authentication database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                device_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_login TEXT,
                is_active INTEGER DEFAULT 1,
                role TEXT DEFAULT 'member'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                device_fingerprint TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_user
            ON sessions(user_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_expires
            ON sessions(expires_at)
        """)

        conn.commit()
        conn.close()

        logger.info(f"Auth database initialized at {self.db_path}")

    def _hash_password(self, password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
        """Hash password using PBKDF2"""
        if salt is None:
            salt = secrets.token_bytes(32)

        # Use PBKDF2 with 600,000 iterations (OWASP recommendation 2023)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600_000)

        # Store salt + hash together
        combined = salt.hex() + ':' + pwd_hash.hex()
        return combined, salt.hex()

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash"""
        try:
            salt_hex, hash_hex = stored_hash.split(':')
            salt = bytes.fromhex(salt_hex)

            # Recreate hash with same salt
            pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600_000)

            return pwd_hash.hex() == hash_hex
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False

    def create_user(self, username: str, password: str, device_id: str) -> User:
        """Create a new user"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Check if username already exists
        cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            raise ValueError("Username already exists")

        user_id = secrets.token_urlsafe(16)
        password_hash, _ = self._hash_password(password)
        created_at = datetime.utcnow().isoformat()

        cursor.execute("""
            INSERT INTO users (user_id, username, password_hash, device_id, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, password_hash, device_id, created_at))

        conn.commit()
        conn.close()

        logger.info(f"Created user: {username} (device: {device_id})")

        return User(
            user_id=user_id,
            username=username,
            device_id=device_id,
            created_at=created_at
        )

    def authenticate(self, username: str, password: str, device_fingerprint: Optional[str] = None) -> Optional[Dict]:
        """Authenticate user and return JWT token with user info"""

        # Check if this is God Rights (Founder) login
        if username == GOD_RIGHTS_USERNAME:
            if password == GOD_RIGHTS_PASSWORD:
                # God Rights login successful
                logger.info("🔐 God Rights (Founder) login")

                # Create JWT token with god_rights flag
                expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
                token_payload = {
                    "user_id": "god_rights",
                    "username": GOD_RIGHTS_USERNAME,
                    "device_id": "founder_device",
                    "role": "god_rights",
                    "exp": expiration.timestamp(),
                    "iat": datetime.utcnow().timestamp()
                }

                token = jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

                return {
                    "token": token,
                    "user_id": "god_rights",
                    "username": GOD_RIGHTS_USERNAME,
                    "device_id": "founder_device",
                    "role": "god_rights"
                }
            else:
                logger.warning("❌ Failed God Rights login attempt")
                return None

        # Regular user authentication
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, password_hash, device_id, is_active, role
            FROM users
            WHERE username = ?
        """, (username,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        user_id, password_hash, device_id, is_active, role = row

        # Check if user is active
        if not is_active:
            conn.close()
            raise ValueError("User account is disabled")

        # Verify password
        if not self._verify_password(password, password_hash):
            conn.close()
            return None

        # Update last login
        last_login = datetime.utcnow().isoformat()
        cursor.execute("""
            UPDATE users SET last_login = ? WHERE user_id = ?
        """, (last_login, user_id))

        # Create JWT token
        expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        token_payload = {
            "user_id": user_id,
            "username": username,
            "device_id": device_id,
            "role": role or "member",  # Default to member if role is None
            "exp": expiration.timestamp(),
            "iat": datetime.utcnow().timestamp()
        }

        token = jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        # Store session
        session_id = secrets.token_urlsafe(16)
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        cursor.execute("""
            INSERT INTO sessions (session_id, user_id, token_hash, created_at, expires_at, device_fingerprint)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            user_id,
            token_hash,
            datetime.utcnow().isoformat(),
            expiration.isoformat(),
            device_fingerprint
        ))

        conn.commit()
        conn.close()

        logger.info(f"User authenticated: {username}")

        # Return both token and user info to avoid re-decoding
        return {
            "token": token,
            "user_id": user_id,
            "username": username,
            "device_id": device_id,
            "role": role or "member"
        }

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token and return payload"""
        try:
            # Disable iat validation for development to avoid clock skew issues
            payload = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                options={'verify_iat': False},
                leeway=60
            )

            # God Rights bypass - no session check needed
            if payload.get('role') == 'god_rights':
                return payload

            # Check if session exists and is valid
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            token_hash = hashlib.sha256(token.encode()).hexdigest()

            cursor.execute("""
                SELECT session_id, expires_at
                FROM sessions
                WHERE user_id = ? AND token_hash = ?
            """, (payload['user_id'], token_hash))

            row = cursor.fetchone()
            conn.close()

            if not row:
                safe_username = sanitize_for_log(payload.get('username', 'unknown'))
                logger.warning(f"Token not found in sessions: {safe_username}")
                return None

            session_id, expires_at = row

            # Check expiration
            if datetime.fromisoformat(expires_at) < datetime.utcnow():
                safe_username = sanitize_for_log(payload.get('username', 'unknown'))
                logger.warning(f"Token expired: {safe_username}")
                return None

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def logout(self, token: str):
        """Logout user by removing session"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            token_hash = hashlib.sha256(token.encode()).hexdigest()

            cursor.execute("""
                DELETE FROM sessions
                WHERE user_id = ? AND token_hash = ?
            """, (payload['user_id'], token_hash))

            conn.commit()
            conn.close()

            safe_username = sanitize_for_log(payload.get('username', 'unknown'))
            logger.info(f"User logged out: {safe_username}")

        except Exception as e:
            logger.error(f"Logout failed: {e}")

    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM sessions
            WHERE datetime(expires_at) < datetime('now')
        """)

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} expired sessions")


# Global auth service instance
auth_service = AuthService()


# Dependency for protected endpoints
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """FastAPI dependency to get current authenticated user"""
    token = credentials.credentials

    payload = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return payload


# Optional dependency (allows both authenticated and anonymous)
async def get_current_user_optional(request: Request) -> Optional[Dict]:
    """FastAPI dependency for optional authentication"""
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return {"user_id": "anonymous", "username": "anonymous"}

    token = auth_header.replace("Bearer ", "")
    payload = auth_service.verify_token(token)

    return payload if payload else {"user_id": "anonymous", "username": "anonymous"}
