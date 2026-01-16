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
from datetime import datetime, timedelta, UTC
from pathlib import Path
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from api.utils import sanitize_for_log
from api.audit.logger import get_audit_logger
from api.audit.actions import AuditAction

logger = logging.getLogger(__name__)

# JWT configuration
# Persist JWT secret to disk for offline resilience
_jwt_secret_warning_shown = False

def _get_or_create_jwt_secret() -> str:
    """
    Get or create persistent JWT secret.
    In offline deployments, losing the JWT secret would invalidate all sessions.
    """
    global _jwt_secret_warning_shown

    # Check env vars first (production override)
    # Preferred: ELOHIMOS_JWT_SECRET_KEY (standardized)
    env_secret = os.getenv("ELOHIMOS_JWT_SECRET_KEY")
    if env_secret:
        return env_secret

    # Backwards-compat: ELOHIM_JWT_SECRET (deprecated)
    legacy_secret = os.getenv("ELOHIM_JWT_SECRET")
    if legacy_secret:
        # Only warn once per session
        if not _jwt_secret_warning_shown:
            logger.warning("Using deprecated env var ELOHIM_JWT_SECRET; prefer ELOHIMOS_JWT_SECRET_KEY")
            _jwt_secret_warning_shown = True
        return legacy_secret

    # Use persistent file storage
    from api.config_paths import get_config_paths

    config_paths = get_config_paths()
    jwt_secret_file = config_paths.data_dir / ".jwt_secret"

    # Try to read existing secret
    if jwt_secret_file.exists():
        try:
            secret = jwt_secret_file.read_text().strip()
            if secret and len(secret) >= 32:
                return secret
            else:
                logger.warning("⚠️  JWT secret file corrupted, regenerating")
        except Exception as e:
            logger.error(f"Failed to read JWT secret: {e}, regenerating")

    # Generate new secret and persist
    secret = secrets.token_urlsafe(32)
    try:
        jwt_secret_file.parent.mkdir(parents=True, exist_ok=True)
        jwt_secret_file.write_text(secret)
        jwt_secret_file.chmod(0o600)  # Owner read/write only
        logger.info(f"✅ Generated and persisted new JWT secret to {jwt_secret_file}")
    except Exception as e:
        logger.error(f"Failed to persist JWT secret: {e}")
        if os.getenv("ELOHIM_ENV") != "development":
            raise RuntimeError("Cannot persist JWT secret in production - sessions would reset on restart")

    return secret

JWT_SECRET = _get_or_create_jwt_secret()

# ===== AUTH-P3: Token & Session Configuration =====
# These constants define the security boundaries for authentication tokens and sessions.
# Changing these values affects all new logins (existing sessions honor their original expiry).

JWT_ALGORITHM = "HS256"

# MED-05: Access token lifetime configurable via ELOHIMOS_JWT_ACCESS_TOKEN_EXPIRE_MINUTES
# Short-lived access tokens reduce window of compromise if token is leaked
# Use refresh token endpoint (/api/v1/auth/refresh) to get new access token
# Default: 60 minutes (1 hour, OWASP recommended: 15min-1hr)
try:
    from api.config import get_settings
    _settings = get_settings()
    JWT_EXPIRATION_MINUTES = _settings.jwt_access_token_expire_minutes
except (ImportError, AttributeError):
    JWT_EXPIRATION_MINUTES = 60  # Fallback if config not available

# Refresh token lifetime: 30 days absolute expiry (used for token refresh without re-login)
REFRESH_TOKEN_EXPIRATION_DAYS = 30  # 30 days (longer-lived)

# Idle timeout: Maximum inactivity period before session expires
# Sessions with no activity for longer than this are invalidated even if not expired
IDLE_TIMEOUT_HOURS = 1  # 1 hour of inactivity

# AUTH-P2: Founder credentials removed from auth_middleware
# Founder is now a DB-backed user with role='founder_rights'
# Bootstrap handled by auth_bootstrap.py in development mode
# Production setup requires explicit Founder creation via setup wizard

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
            from api.config_paths import get_config_paths
            db_path = get_config_paths().auth_db
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """
        Initialize authentication database with optimized settings for concurrency.

        AUTH-P1 COMPLETE: Schema creation is now handled by migrations/auth/ module.
        Migrations run at startup via startup_migrations.py before this method is called.
        This method now only sets SQLite pragmas for performance optimization.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()

            # Enable WAL mode for better concurrent read/write performance
            cursor.execute("PRAGMA journal_mode=WAL")
            # Reduce fsync overhead (safe for offline deployment with UPS)
            cursor.execute("PRAGMA synchronous=NORMAL")
            # Use memory for temporary tables
            cursor.execute("PRAGMA temp_store=MEMORY")
            # Set busy timeout to 30 seconds (handles write contention)
            cursor.execute("PRAGMA busy_timeout=30000")

            # Verify migrations have run (tables should exist)
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name IN ('users', 'sessions')
            """)
            tables = {row[0] for row in cursor.fetchall()}

            if 'users' not in tables or 'sessions' not in tables:
                # This should only happen if startup_migrations.py wasn't called
                raise RuntimeError(
                    "Auth tables missing - run startup_migrations.py first. "
                    "Schema is managed by migrations/auth/ module."
                )

            conn.commit()

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

            # SECURITY: Use constant-time comparison to prevent timing attacks
            import hmac
            return hmac.compare_digest(pwd_hash.hex(), hash_hex)
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False

    def create_user(self, username: str, password: str, device_id: str) -> User:
        """Create a new user"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()

            # Check if username already exists
            cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                raise ValueError("Username already exists")

            user_id = secrets.token_urlsafe(16)
            password_hash, _ = self._hash_password(password)
            created_at = datetime.now(UTC).isoformat()

            cursor.execute("""
                INSERT INTO users (user_id, username, password_hash, device_id, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, password_hash, device_id, created_at))

            conn.commit()

        logger.info(f"Created user: {username} (device: {device_id})")

        return User(
            user_id=user_id,
            username=username,
            device_id=device_id,
            created_at=created_at
        )

    def get_all_users(self) -> list[User]:
        """Get all users from the database.

        Returns:
            List of User objects (without passwords)
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, device_id, created_at
                FROM users
                ORDER BY created_at ASC
            """)
            rows = cursor.fetchall()

        return [
            User(
                user_id=row[0],
                username=row[1],
                device_id=row[2],
                created_at=row[3]
            )
            for row in rows
        ]

    def authenticate(self, username: str, password: str, device_fingerprint: Optional[str] = None) -> Optional[Dict]:
        """
        Authenticate user and return JWT token with user info

        AUTH-P2: Founder is now a DB-backed user with role='founder_rights'
        instead of a hardcoded env-based backdoor.
        """

        # AUTH-P2: All users (including Founder) authenticate via DB
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT user_id, password_hash, device_id, is_active, role
                FROM users
                WHERE username = ?
            """, (username,))

            row = cursor.fetchone()
            if not row:
                return None

            user_id, password_hash, device_id, is_active, role = row

            # Check if user is active
            if not is_active:
                raise ValueError("User account is disabled")

            # Verify password
            if not self._verify_password(password, password_hash):
                return None

            # Update last login
            last_login = datetime.now(UTC).isoformat()
            cursor.execute("""
                UPDATE users SET last_login = ? WHERE user_id = ?
            """, (last_login, user_id))

            # Create JWT token
            expiration = datetime.now(UTC) + timedelta(minutes=JWT_EXPIRATION_MINUTES)
            token_payload = {
                "user_id": user_id,
                "username": username,
                "device_id": device_id,
                "role": role or "member",  # Default to member if role is None
                "exp": expiration.timestamp(),
                "iat": datetime.now(UTC).timestamp()
            }

            token = jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

            # LOW-02: Generate refresh token (longer-lived)
            refresh_expiration = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRATION_DAYS)
            refresh_token = secrets.token_urlsafe(32)  # Longer random token
            refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

            # Store session
            session_id = secrets.token_urlsafe(16)
            token_hash = hashlib.sha256(token.encode()).hexdigest()

            # Store session with refresh token
            cursor.execute("""
                INSERT INTO sessions (session_id, user_id, token_hash, refresh_token_hash, created_at, expires_at, refresh_expires_at, device_fingerprint, last_activity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                user_id,
                token_hash,
                refresh_token_hash,
                datetime.now(UTC).isoformat(),
                expiration.isoformat(),
                refresh_expiration.isoformat(),
                device_fingerprint,
                datetime.now(UTC).isoformat()  # Initial last_activity
            ))

            conn.commit()

        logger.info(f"User authenticated: {username}")

        # Return both token and user info to avoid re-decoding
        # LOW-02: Include refresh token in response
        return {
            "token": token,
            "refresh_token": refresh_token,  # LOW-02: New field
            "user_id": user_id,
            "username": username,
            "device_id": device_id,
            "role": role or "member"
        }

    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Verify JWT token and return payload

        AUTH-P3: All users (including Founder) go through session checks for hardening.
        Validates:
        1. JWT signature and expiry
        2. Session exists in database
        3. Session not expired (expires_at)
        4. Session not idle (last_activity within IDLE_TIMEOUT_HOURS)
        5. Updates last_activity on successful verification
        """
        try:
            # SECURITY: Enable iat verification with adequate leeway for clock skew
            payload = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                options={'verify_iat': True},
                leeway=120  # 2 minutes handles clock skew between client/server
            )

            # AUTH-P3: No more Founder bypass - all users go through session checks
            # This ensures Founder tokens can be revoked and idle timeout applies

            # Validate required claims are present
            if 'user_id' not in payload:
                logger.warning("Token missing required claim: user_id")
                return None

            # Check if session exists and is valid
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                token_hash = hashlib.sha256(token.encode()).hexdigest()

                cursor.execute("""
                    SELECT session_id, expires_at, last_activity
                    FROM sessions
                    WHERE user_id = ? AND token_hash = ?
                """, (payload['user_id'], token_hash))

                row = cursor.fetchone()

                if not row:
                    safe_username = sanitize_for_log(payload.get('username', 'unknown'))
                    logger.warning(f"Token not found in sessions: {safe_username}")
                    return None

                session_id, expires_at, last_activity = row

                # Check expiration
                if datetime.fromisoformat(expires_at) < datetime.now(UTC):
                    safe_username = sanitize_for_log(payload.get('username', 'unknown'))
                    logger.warning(f"Token expired: {safe_username}")
                    return None

                # AUTH-P3: Check idle timeout using module-level constant
                if last_activity:
                    last_active = datetime.fromisoformat(last_activity)
                    idle_time = datetime.now(UTC) - last_active
                    if idle_time > timedelta(hours=IDLE_TIMEOUT_HOURS):
                        safe_username = sanitize_for_log(payload.get('username', 'unknown'))
                        logger.warning(f"Session idle timeout for user: {safe_username} (idle for {idle_time})")
                        # Delete expired session
                        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                        conn.commit()
                        return None

                # Update last_activity timestamp
                cursor.execute("""
                    UPDATE sessions
                    SET last_activity = ?
                    WHERE session_id = ?
                """, (datetime.now(UTC).isoformat(), session_id))
                conn.commit()

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[Dict]:
        """
        LOW-02: Refresh access token using refresh token

        Args:
            refresh_token: The refresh token from login

        Returns:
            New access token and user info, or None if invalid
        """
        try:
            refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Find session with matching refresh token
                cursor.execute("""
                    SELECT user_id, session_id, refresh_expires_at, device_fingerprint
                    FROM sessions
                    WHERE refresh_token_hash = ?
                """, (refresh_token_hash,))

                row = cursor.fetchone()
                if not row:
                    logger.warning("Invalid refresh token")
                    return None

                user_id, session_id, refresh_expires_at, device_fingerprint = row

                # Check if refresh token expired
                if datetime.fromisoformat(refresh_expires_at) < datetime.now(UTC):
                    logger.warning(f"Refresh token expired for user: {user_id}")
                    # Delete expired session
                    cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                    conn.commit()
                    return None

                # Get user details
                cursor.execute("""
                    SELECT username, device_id, role
                    FROM users
                    WHERE user_id = ?
                """, (user_id,))

                user_row = cursor.fetchone()
                if not user_row:
                    return None

                username, device_id, role = user_row

                # Generate new access token
                expiration = datetime.now(UTC) + timedelta(minutes=JWT_EXPIRATION_MINUTES)
                token_payload = {
                    "user_id": user_id,
                    "username": username,
                    "device_id": device_id,
                    "role": role or "member",
                    "exp": expiration.timestamp(),
                    "iat": datetime.now(UTC).timestamp()
                }

                new_token = jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
                new_token_hash = hashlib.sha256(new_token.encode()).hexdigest()

                # Update session with new access token
                cursor.execute("""
                    UPDATE sessions
                    SET token_hash = ?, expires_at = ?, last_activity = ?
                    WHERE session_id = ?
                """, (new_token_hash, expiration.isoformat(), datetime.now(UTC).isoformat(), session_id))

                conn.commit()

            logger.info(f"Access token refreshed for user: {username}")

            return {
                "token": new_token,
                "user_id": user_id,
                "username": username,
                "device_id": device_id,
                "role": role or "member"
            }

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return None

    def logout(self, token: str) -> None:
        """Logout user by removing session"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                token_hash = hashlib.sha256(token.encode()).hexdigest()

                cursor.execute("""
                    DELETE FROM sessions
                    WHERE user_id = ? AND token_hash = ?
                """, (payload['user_id'], token_hash))

                conn.commit()

            safe_username = sanitize_for_log(payload.get('username', 'unknown'))
            logger.info(f"User logged out: {safe_username}")

        except Exception as e:
            logger.error(f"Logout failed: {e}")

    def cleanup_expired_sessions(self) -> None:
        """Remove expired sessions"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM sessions
                WHERE datetime(expires_at) < datetime('now')
            """)

            deleted = cursor.rowcount
            conn.commit()

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


# ===== WebSocket Authentication Helpers =====

def extract_websocket_token(websocket, query_token: Optional[str] = None) -> Optional[str]:
    """
    Extract JWT token from WebSocket request.

    SECURITY: Only accepts token via Sec-WebSocket-Protocol header.
    Query param fallback has been REMOVED to prevent token leakage
    in server logs, browser history, and referrer headers.

    Protocol format: "jwt-<token>" or "bearer.<token>"

    Args:
        websocket: FastAPI WebSocket instance
        query_token: DEPRECATED - Ignored for security reasons

    Returns:
        JWT token string or None
    """
    # Only accept Sec-WebSocket-Protocol header (secure method)
    protocols = websocket.headers.get("sec-websocket-protocol", "")
    for protocol in protocols.split(","):
        protocol = protocol.strip()
        # Support both "jwt-<token>" and "bearer.<token>" formats
        if protocol.startswith("jwt-"):
            return protocol[4:]  # Remove "jwt-" prefix
        if protocol.startswith("bearer."):
            return protocol[7:]  # Remove "bearer." prefix

    # SECURITY: Query param fallback REMOVED
    # Token in query params is a security risk:
    # - Logged in server access logs
    # - Stored in browser history
    # - Leaked via Referer header
    if query_token:
        logger.warning(
            "SECURITY: WebSocket query param token rejected. "
            "Use Sec-WebSocket-Protocol header instead."
        )
        # Return None instead of accepting the token
        return None

    return None


async def verify_websocket_auth(websocket, query_token: Optional[str] = None) -> Optional[Dict]:
    """
    Verify WebSocket authentication and return user payload.

    SECURITY: query_token parameter is DEPRECATED and ignored.
    Clients must use Sec-WebSocket-Protocol header for authentication.

    Args:
        websocket: FastAPI WebSocket instance
        query_token: DEPRECATED - Ignored for security reasons

    Returns:
        User payload dict if authenticated, None otherwise
    """
    token = extract_websocket_token(websocket, query_token)
    if not token:
        return None

    return auth_service.verify_token(token)
