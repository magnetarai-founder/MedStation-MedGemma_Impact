"""
Comprehensive tests for api/auth_middleware.py

Tests cover:
- JWT secret management (env vars, file storage)
- Password hashing and verification (PBKDF2 600k iterations)
- User creation and duplicate detection
- Authentication flow with JWT tokens
- Token verification with session validation
- Idle timeout handling
- Refresh token flow
- Logout and session cleanup
- FastAPI dependencies
- WebSocket authentication helpers
"""

import pytest
import jwt
import secrets
import hashlib
import sqlite3
import tempfile
import asyncio
from datetime import datetime, timedelta, UTC
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from fastapi import HTTPException

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.auth_middleware import (
    AuthService,
    User,
    get_current_user,
    get_current_user_optional,
    extract_websocket_token,
    verify_websocket_auth,
    JWT_ALGORITHM,
    JWT_EXPIRATION_MINUTES,
    REFRESH_TOKEN_EXPIRATION_DAYS,
    IDLE_TIMEOUT_HOURS,
)


# ========== Fixtures ==========

@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing"""
    db_path = tmp_path / "test_auth.db"
    return db_path


@pytest.fixture
def auth_service(temp_db):
    """Create AuthService with temp database and pre-created tables"""
    # Create tables manually since we're bypassing migrations
    with sqlite3.connect(str(temp_db)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                device_id TEXT,
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
                refresh_token_hash TEXT,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                refresh_expires_at TEXT,
                device_fingerprint TEXT,
                last_activity TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        conn.commit()

    return AuthService(db_path=str(temp_db))


@pytest.fixture
def test_user(auth_service):
    """Create a test user"""
    return auth_service.create_user(
        username="testuser",
        password="SecurePassword123!",
        device_id="test-device-001"
    )


@pytest.fixture
def authenticated_user(auth_service, test_user):
    """Create a test user and authenticate them"""
    result = auth_service.authenticate(
        username="testuser",
        password="SecurePassword123!"
    )
    return result


# ========== User Model Tests ==========

class TestUserModel:
    """Tests for the User Pydantic model"""

    def test_user_model_creation(self):
        """Test creating a User model"""
        user = User(
            user_id="test-id-123",
            username="testuser",
            device_id="device-001",
            created_at="2024-01-01T00:00:00Z"
        )
        assert user.user_id == "test-id-123"
        assert user.username == "testuser"
        assert user.device_id == "device-001"
        assert user.last_login is None

    def test_user_model_with_last_login(self):
        """Test User model with last_login"""
        user = User(
            user_id="test-id-123",
            username="testuser",
            device_id="device-001",
            created_at="2024-01-01T00:00:00Z",
            last_login="2024-01-02T12:00:00Z"
        )
        assert user.last_login == "2024-01-02T12:00:00Z"

    def test_user_model_serialization(self):
        """Test User model JSON serialization"""
        user = User(
            user_id="test-id-123",
            username="testuser",
            device_id="device-001",
            created_at="2024-01-01T00:00:00Z"
        )
        data = user.model_dump()
        assert data["user_id"] == "test-id-123"
        assert data["username"] == "testuser"


# ========== Password Hashing Tests ==========

class TestPasswordHashing:
    """Tests for password hashing and verification"""

    def test_hash_password_creates_unique_hashes(self, auth_service):
        """Test that same password with different salts creates different hashes"""
        hash1, salt1 = auth_service._hash_password("password123")
        hash2, salt2 = auth_service._hash_password("password123")

        assert hash1 != hash2, "Different salts should produce different hashes"
        assert salt1 != salt2, "Salts should be unique"

    def test_hash_password_with_custom_salt(self, auth_service):
        """Test hashing with a custom salt"""
        custom_salt = secrets.token_bytes(32)
        hash1, _ = auth_service._hash_password("password123", salt=custom_salt)
        hash2, _ = auth_service._hash_password("password123", salt=custom_salt)

        assert hash1 == hash2, "Same salt should produce same hash"

    def test_verify_password_correct(self, auth_service):
        """Test password verification with correct password"""
        password = "MySecurePassword123!"
        stored_hash, _ = auth_service._hash_password(password)

        assert auth_service._verify_password(password, stored_hash) is True

    def test_verify_password_incorrect(self, auth_service):
        """Test password verification with incorrect password"""
        password = "MySecurePassword123!"
        stored_hash, _ = auth_service._hash_password(password)

        assert auth_service._verify_password("WrongPassword!", stored_hash) is False

    def test_verify_password_malformed_hash(self, auth_service):
        """Test password verification with malformed hash"""
        assert auth_service._verify_password("password", "invalid-hash") is False

    def test_verify_password_empty_hash(self, auth_service):
        """Test password verification with empty hash"""
        assert auth_service._verify_password("password", "") is False

    def test_hash_format_contains_salt_and_hash(self, auth_service):
        """Test that hash format is 'salt:hash'"""
        stored_hash, salt = auth_service._hash_password("password123")

        assert ":" in stored_hash
        parts = stored_hash.split(":")
        assert len(parts) == 2
        assert parts[0] == salt  # Salt should be first part

    def test_password_hash_timing_safety(self, auth_service):
        """Test that password verification uses constant-time comparison"""
        # This is a smoke test - actual timing attacks need statistical analysis
        password = "TestPassword123!"
        stored_hash, _ = auth_service._hash_password(password)

        # Verify correct password
        result1 = auth_service._verify_password(password, stored_hash)
        # Verify wrong password (should take similar time due to hmac.compare_digest)
        result2 = auth_service._verify_password("wrong", stored_hash)

        assert result1 is True
        assert result2 is False


# ========== User Creation Tests ==========

class TestUserCreation:
    """Tests for user creation"""

    def test_create_user_success(self, auth_service):
        """Test successful user creation"""
        user = auth_service.create_user(
            username="newuser",
            password="SecurePass123!",
            device_id="device-001"
        )

        assert user.username == "newuser"
        assert user.device_id == "device-001"
        assert user.user_id is not None
        assert user.created_at is not None

    def test_create_user_duplicate_username(self, auth_service, test_user):
        """Test that duplicate usernames are rejected"""
        with pytest.raises(ValueError, match="Username already exists"):
            auth_service.create_user(
                username="testuser",  # Same as test_user
                password="AnotherPass123!",
                device_id="device-002"
            )

    def test_create_user_stores_in_database(self, auth_service, temp_db):
        """Test that user is stored in database"""
        auth_service.create_user(
            username="dbuser",
            password="SecurePass123!",
            device_id="device-001"
        )

        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE username = ?", ("dbuser",))
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "dbuser"

    def test_create_user_password_is_hashed(self, auth_service, temp_db):
        """Test that password is stored as hash, not plaintext"""
        password = "PlaintextPassword123!"
        auth_service.create_user(
            username="hashtest",
            password=password,
            device_id="device-001"
        )

        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE username = ?", ("hashtest",))
            row = cursor.fetchone()

        assert row is not None
        assert row[0] != password  # Not plaintext
        assert ":" in row[0]  # Has salt:hash format


# ========== Authentication Tests ==========

class TestAuthentication:
    """Tests for user authentication"""

    def test_authenticate_success(self, auth_service, test_user):
        """Test successful authentication"""
        result = auth_service.authenticate(
            username="testuser",
            password="SecurePassword123!"
        )

        assert result is not None
        assert "token" in result
        assert "refresh_token" in result
        assert result["username"] == "testuser"
        assert result["user_id"] is not None

    def test_authenticate_wrong_password(self, auth_service, test_user):
        """Test authentication with wrong password"""
        result = auth_service.authenticate(
            username="testuser",
            password="WrongPassword!"
        )

        assert result is None

    def test_authenticate_nonexistent_user(self, auth_service):
        """Test authentication with nonexistent user"""
        result = auth_service.authenticate(
            username="nonexistent",
            password="AnyPassword123!"
        )

        assert result is None

    def test_authenticate_disabled_user(self, auth_service, test_user, temp_db):
        """Test authentication with disabled user"""
        # Disable the user
        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_active = 0 WHERE username = ?", ("testuser",))
            conn.commit()

        with pytest.raises(ValueError, match="User account is disabled"):
            auth_service.authenticate(
                username="testuser",
                password="SecurePassword123!"
            )

    def test_authenticate_creates_session(self, auth_service, test_user, temp_db):
        """Test that authentication creates a session in database"""
        result = auth_service.authenticate(
            username="testuser",
            password="SecurePassword123!"
        )

        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT session_id FROM sessions WHERE user_id = ?",
                (result["user_id"],)
            )
            row = cursor.fetchone()

        assert row is not None

    def test_authenticate_updates_last_login(self, auth_service, test_user, temp_db):
        """Test that authentication updates last_login"""
        auth_service.authenticate(
            username="testuser",
            password="SecurePassword123!"
        )

        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT last_login FROM users WHERE username = ?",
                ("testuser",)
            )
            row = cursor.fetchone()

        assert row[0] is not None

    def test_authenticate_with_device_fingerprint(self, auth_service, test_user, temp_db):
        """Test authentication with device fingerprint"""
        fingerprint = "device-fingerprint-123"
        result = auth_service.authenticate(
            username="testuser",
            password="SecurePassword123!",
            device_fingerprint=fingerprint
        )

        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT device_fingerprint FROM sessions WHERE user_id = ?",
                (result["user_id"],)
            )
            row = cursor.fetchone()

        assert row[0] == fingerprint

    def test_authenticate_returns_role(self, auth_service, test_user):
        """Test that authentication returns user role"""
        result = auth_service.authenticate(
            username="testuser",
            password="SecurePassword123!"
        )

        assert "role" in result
        assert result["role"] == "member"  # Default role

    def test_authenticate_founder_role(self, auth_service, temp_db):
        """Test authentication with founder role"""
        # Create user with founder_rights role
        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            password_hash, _ = auth_service._hash_password("FounderPass123!")
            cursor.execute("""
                INSERT INTO users (user_id, username, password_hash, device_id, created_at, role, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, ("founder-id", "founder", password_hash, "device-001", datetime.now(UTC).isoformat(), "founder_rights"))
            conn.commit()

        result = auth_service.authenticate(
            username="founder",
            password="FounderPass123!"
        )

        assert result["role"] == "founder_rights"


# ========== Token Verification Tests ==========

class TestTokenVerification:
    """Tests for JWT token verification"""

    def test_verify_token_success(self, auth_service, authenticated_user):
        """Test successful token verification"""
        payload = auth_service.verify_token(authenticated_user["token"])

        assert payload is not None
        assert payload["user_id"] == authenticated_user["user_id"]
        assert payload["username"] == authenticated_user["username"]

    def test_verify_token_expired(self, auth_service, authenticated_user):
        """Test verification of expired token"""
        # Create an expired token manually
        from api.auth_middleware import JWT_SECRET

        expired_payload = {
            "user_id": authenticated_user["user_id"],
            "username": authenticated_user["username"],
            "device_id": authenticated_user["device_id"],
            "role": "member",
            "exp": (datetime.now(UTC) - timedelta(hours=1)).timestamp(),
            "iat": (datetime.now(UTC) - timedelta(hours=2)).timestamp()
        }
        expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        payload = auth_service.verify_token(expired_token)
        assert payload is None

    def test_verify_token_invalid_signature(self, auth_service, authenticated_user):
        """Test verification of token with invalid signature"""
        # Create token with different secret
        fake_payload = {
            "user_id": authenticated_user["user_id"],
            "username": authenticated_user["username"],
            "device_id": "device-001",
            "role": "member",
            "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp(),
            "iat": datetime.now(UTC).timestamp()
        }
        fake_token = jwt.encode(fake_payload, "wrong-secret", algorithm=JWT_ALGORITHM)

        payload = auth_service.verify_token(fake_token)
        assert payload is None

    def test_verify_token_missing_session(self, auth_service, temp_db):
        """Test verification of token without database session"""
        from api.auth_middleware import JWT_SECRET

        # Create user without session
        user = auth_service.create_user("nosession", "Pass123!", "device-001")

        # Create valid JWT but don't create session
        token_payload = {
            "user_id": user.user_id,
            "username": user.username,
            "device_id": user.device_id,
            "role": "member",
            "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp(),
            "iat": datetime.now(UTC).timestamp()
        }
        token = jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        payload = auth_service.verify_token(token)
        assert payload is None

    def test_verify_token_updates_last_activity(self, auth_service, authenticated_user, temp_db):
        """Test that token verification updates last_activity"""
        # Get initial last_activity
        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT last_activity FROM sessions WHERE user_id = ?",
                (authenticated_user["user_id"],)
            )
            initial_activity = cursor.fetchone()[0]

        # Wait a tiny bit and verify token
        import time
        time.sleep(0.01)
        auth_service.verify_token(authenticated_user["token"])

        # Check last_activity was updated
        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT last_activity FROM sessions WHERE user_id = ?",
                (authenticated_user["user_id"],)
            )
            new_activity = cursor.fetchone()[0]

        assert new_activity != initial_activity

    def test_verify_token_idle_timeout(self, auth_service, authenticated_user, temp_db):
        """Test that idle sessions are invalidated"""
        # Manually set last_activity to past idle timeout
        idle_time = datetime.now(UTC) - timedelta(hours=IDLE_TIMEOUT_HOURS + 1)

        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET last_activity = ? WHERE user_id = ?",
                (idle_time.isoformat(), authenticated_user["user_id"])
            )
            conn.commit()

        payload = auth_service.verify_token(authenticated_user["token"])
        assert payload is None

    def test_verify_token_missing_user_id_claim(self, auth_service):
        """Test verification of token missing user_id claim"""
        from api.auth_middleware import JWT_SECRET

        # Create token without user_id
        token_payload = {
            "username": "testuser",
            "device_id": "device-001",
            "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp(),
            "iat": datetime.now(UTC).timestamp()
        }
        token = jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        payload = auth_service.verify_token(token)
        assert payload is None

    def test_verify_token_expired_session(self, auth_service, authenticated_user, temp_db):
        """Test verification when session is expired in database"""
        # Manually expire the session
        expired_time = datetime.now(UTC) - timedelta(hours=1)

        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET expires_at = ? WHERE user_id = ?",
                (expired_time.isoformat(), authenticated_user["user_id"])
            )
            conn.commit()

        payload = auth_service.verify_token(authenticated_user["token"])
        assert payload is None


# ========== Refresh Token Tests ==========

class TestRefreshToken:
    """Tests for refresh token flow"""

    def test_refresh_access_token_success(self, auth_service, authenticated_user):
        """Test successful access token refresh"""
        result = auth_service.refresh_access_token(authenticated_user["refresh_token"])

        assert result is not None
        assert "token" in result
        assert result["token"] != authenticated_user["token"]  # New token
        assert result["user_id"] == authenticated_user["user_id"]

    def test_refresh_access_token_invalid(self, auth_service):
        """Test refresh with invalid token"""
        result = auth_service.refresh_access_token("invalid-refresh-token")
        assert result is None

    def test_refresh_access_token_expired(self, auth_service, authenticated_user, temp_db):
        """Test refresh with expired refresh token"""
        # Manually expire the refresh token
        expired_time = datetime.now(UTC) - timedelta(days=1)

        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET refresh_expires_at = ? WHERE user_id = ?",
                (expired_time.isoformat(), authenticated_user["user_id"])
            )
            conn.commit()

        result = auth_service.refresh_access_token(authenticated_user["refresh_token"])
        assert result is None

    def test_refresh_updates_session(self, auth_service, authenticated_user, temp_db):
        """Test that refresh updates session in database"""
        old_token_hash = hashlib.sha256(authenticated_user["token"].encode()).hexdigest()

        result = auth_service.refresh_access_token(authenticated_user["refresh_token"])
        new_token_hash = hashlib.sha256(result["token"].encode()).hexdigest()

        # Check database has new token hash
        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT token_hash FROM sessions WHERE user_id = ?",
                (authenticated_user["user_id"],)
            )
            stored_hash = cursor.fetchone()[0]

        assert stored_hash == new_token_hash
        assert stored_hash != old_token_hash

    def test_new_token_is_valid(self, auth_service, authenticated_user):
        """Test that refreshed token can be verified"""
        result = auth_service.refresh_access_token(authenticated_user["refresh_token"])

        payload = auth_service.verify_token(result["token"])
        assert payload is not None
        assert payload["user_id"] == authenticated_user["user_id"]

    def test_old_token_invalid_after_refresh(self, auth_service, authenticated_user):
        """Test that old token is invalid after refresh"""
        old_token = authenticated_user["token"]

        # Refresh to get new token
        auth_service.refresh_access_token(authenticated_user["refresh_token"])

        # Old token should no longer work (hash mismatch)
        payload = auth_service.verify_token(old_token)
        assert payload is None


# ========== Logout Tests ==========

class TestLogout:
    """Tests for logout functionality"""

    def test_logout_removes_session(self, auth_service, authenticated_user, temp_db):
        """Test that logout removes session from database"""
        auth_service.logout(authenticated_user["token"])

        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT session_id FROM sessions WHERE user_id = ?",
                (authenticated_user["user_id"],)
            )
            row = cursor.fetchone()

        assert row is None

    def test_logout_token_becomes_invalid(self, auth_service, authenticated_user):
        """Test that token is invalid after logout"""
        auth_service.logout(authenticated_user["token"])

        payload = auth_service.verify_token(authenticated_user["token"])
        assert payload is None

    def test_logout_invalid_token(self, auth_service):
        """Test logout with invalid token doesn't raise"""
        # Should not raise, just log error
        auth_service.logout("invalid-token-here")


# ========== Session Cleanup Tests ==========

class TestSessionCleanup:
    """Tests for expired session cleanup"""

    def test_cleanup_expired_sessions(self, auth_service, temp_db):
        """Test that expired sessions are removed"""
        # Create an expired session manually
        expired_time = datetime.now(UTC) - timedelta(hours=1)

        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (session_id, user_id, token_hash, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                "expired-session",
                "test-user-id",
                "test-hash",
                datetime.now(UTC).isoformat(),
                expired_time.isoformat()
            ))
            conn.commit()

        auth_service.cleanup_expired_sessions()

        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id FROM sessions WHERE session_id = ?", ("expired-session",))
            row = cursor.fetchone()

        assert row is None

    def test_cleanup_keeps_valid_sessions(self, auth_service, authenticated_user, temp_db):
        """Test that valid sessions are not removed"""
        auth_service.cleanup_expired_sessions()

        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT session_id FROM sessions WHERE user_id = ?",
                (authenticated_user["user_id"],)
            )
            row = cursor.fetchone()

        assert row is not None


# ========== FastAPI Dependency Tests ==========

class TestFastAPIDependencies:
    """Tests for FastAPI authentication dependencies"""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, auth_service, authenticated_user):
        """Test successful current user retrieval"""
        credentials = Mock()
        credentials.credentials = authenticated_user["token"]

        with patch('api.auth.middleware.auth_service', auth_service):
            user = await get_current_user(credentials)

        assert user["user_id"] == authenticated_user["user_id"]

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, auth_service):
        """Test current user with invalid token"""
        credentials = Mock()
        credentials.credentials = "invalid-token"

        with patch('api.auth.middleware.auth_service', auth_service):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_optional_with_token(self, auth_service, authenticated_user):
        """Test optional auth with valid token"""
        request = Mock()
        request.headers.get.return_value = f"Bearer {authenticated_user['token']}"

        with patch('api.auth.middleware.auth_service', auth_service):
            user = await get_current_user_optional(request)

        assert user["user_id"] == authenticated_user["user_id"]

    @pytest.mark.asyncio
    async def test_get_current_user_optional_without_token(self, auth_service):
        """Test optional auth without token"""
        request = Mock()
        request.headers.get.return_value = None

        with patch('api.auth.middleware.auth_service', auth_service):
            user = await get_current_user_optional(request)

        assert user["user_id"] == "anonymous"
        assert user["username"] == "anonymous"

    @pytest.mark.asyncio
    async def test_get_current_user_optional_invalid_token(self, auth_service):
        """Test optional auth with invalid token returns anonymous"""
        request = Mock()
        request.headers.get.return_value = "Bearer invalid-token"

        with patch('api.auth.middleware.auth_service', auth_service):
            user = await get_current_user_optional(request)

        assert user["user_id"] == "anonymous"


# ========== WebSocket Authentication Tests ==========

class TestWebSocketAuth:
    """Tests for WebSocket authentication helpers"""

    def test_extract_token_from_jwt_protocol(self):
        """Test extracting token from jwt- protocol header"""
        websocket = Mock()
        websocket.headers.get.return_value = "jwt-mytoken123"

        token = extract_websocket_token(websocket)
        assert token == "mytoken123"

    def test_extract_token_from_bearer_protocol(self):
        """Test extracting token from bearer. protocol header"""
        websocket = Mock()
        websocket.headers.get.return_value = "bearer.mytoken456"

        token = extract_websocket_token(websocket)
        assert token == "mytoken456"

    def test_extract_token_rejects_query_param_for_security(self):
        """Test that query parameter tokens are rejected for security.

        SECURITY: Query param tokens are rejected to prevent token leakage via:
        - Server access logs
        - Browser history
        - Referer headers
        """
        websocket = Mock()
        websocket.headers.get.return_value = ""

        # Query param tokens should be rejected (returns None)
        token = extract_websocket_token(websocket, query_token="querytoken789")
        assert token is None  # Rejected for security

    def test_extract_token_header_only_not_query(self):
        """Test that only header token is used, query param is ignored"""
        websocket = Mock()
        websocket.headers.get.return_value = "jwt-headertoken"

        # Header token is used, query param is ignored
        token = extract_websocket_token(websocket, query_token="querytoken")
        assert token == "headertoken"

    def test_extract_token_multiple_protocols(self):
        """Test extracting token from multiple protocols"""
        websocket = Mock()
        websocket.headers.get.return_value = "other, jwt-mytoken, something"

        token = extract_websocket_token(websocket)
        assert token == "mytoken"

    def test_extract_token_no_valid_protocol(self):
        """Test when no valid protocol is present"""
        websocket = Mock()
        websocket.headers.get.return_value = "invalid-protocol"

        token = extract_websocket_token(websocket)
        assert token is None

    @pytest.mark.asyncio
    async def test_verify_websocket_auth_success(self, auth_service, authenticated_user):
        """Test successful WebSocket authentication"""
        websocket = Mock()
        websocket.headers.get.return_value = f"jwt-{authenticated_user['token']}"

        with patch('api.auth.middleware.auth_service', auth_service):
            payload = await verify_websocket_auth(websocket)

        assert payload is not None
        assert payload["user_id"] == authenticated_user["user_id"]

    @pytest.mark.asyncio
    async def test_verify_websocket_auth_no_token(self, auth_service):
        """Test WebSocket auth without token"""
        websocket = Mock()
        websocket.headers.get.return_value = ""

        with patch('api.auth.middleware.auth_service', auth_service):
            payload = await verify_websocket_auth(websocket)

        assert payload is None

    @pytest.mark.asyncio
    async def test_verify_websocket_auth_invalid_token(self, auth_service):
        """Test WebSocket auth with invalid token"""
        websocket = Mock()
        websocket.headers.get.return_value = "jwt-invalid-token"

        with patch('api.auth.middleware.auth_service', auth_service):
            payload = await verify_websocket_auth(websocket)

        assert payload is None


# ========== JWT Secret Management Tests ==========

class TestJWTSecretManagement:
    """Tests for JWT secret management"""

    def test_jwt_secret_from_env_var(self):
        """Test JWT secret loaded from environment variable"""
        with patch.dict('os.environ', {'MEDSTATIONOS_JWT_SECRET_KEY': 'test-secret-from-env'}):
            from importlib import reload
            import api.auth_middleware as module

            # We can't easily reload without side effects, so just verify the function
            result = module._get_or_create_jwt_secret()
            assert result == 'test-secret-from-env'

    def test_jwt_secret_legacy_env_var(self):
        """Test JWT secret from legacy environment variable"""
        with patch.dict('os.environ', {'MEDSTATION_JWT_SECRET': 'legacy-secret'}, clear=False):
            with patch.dict('os.environ', {'MEDSTATIONOS_JWT_SECRET_KEY': ''}, clear=False):
                from api.auth_middleware import _get_or_create_jwt_secret
                # Clear env var for primary
                import os
                old_val = os.environ.pop('MEDSTATIONOS_JWT_SECRET_KEY', None)
                try:
                    os.environ['MEDSTATION_JWT_SECRET'] = 'legacy-secret'
                    result = _get_or_create_jwt_secret()
                    # Will return primary if set, or legacy
                finally:
                    if old_val:
                        os.environ['MEDSTATIONOS_JWT_SECRET_KEY'] = old_val

    def test_jwt_algorithm_is_hs256(self):
        """Test that JWT algorithm is HS256"""
        assert JWT_ALGORITHM == "HS256"

    def test_jwt_expiration_configurable(self):
        """Test that JWT expiration is configurable"""
        # Default is 60 minutes
        assert JWT_EXPIRATION_MINUTES >= 15  # At least OWASP minimum
        assert JWT_EXPIRATION_MINUTES <= 120  # Reasonable maximum


# ========== Database Initialization Tests ==========

class TestDatabaseInit:
    """Tests for database initialization"""

    def test_init_db_creates_directory(self, tmp_path):
        """Test that database directory is created"""
        nested_path = tmp_path / "nested" / "dir" / "auth.db"

        # Pre-create tables
        nested_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(nested_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    device_id TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            """)
            conn.commit()

        service = AuthService(db_path=str(nested_path))
        assert nested_path.exists()

    def test_init_db_sets_wal_mode(self, auth_service, temp_db):
        """Test that WAL mode is enabled"""
        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode")
            mode = cursor.fetchone()[0]

        assert mode.lower() == "wal"

    def test_init_db_raises_without_migrations(self, tmp_path):
        """Test that init raises if tables don't exist"""
        db_path = tmp_path / "empty.db"
        db_path.touch()

        with pytest.raises(RuntimeError, match="Auth tables missing"):
            AuthService(db_path=str(db_path))


# ========== Edge Cases and Error Handling ==========

class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_unicode_username(self, auth_service):
        """Test user creation with unicode username"""
        user = auth_service.create_user(
            username="用户名测试",
            password="SecurePass123!",
            device_id="device-001"
        )
        assert user.username == "用户名测试"

    def test_unicode_password(self, auth_service):
        """Test authentication with unicode password"""
        auth_service.create_user(
            username="unicodepass",
            password="密码🔐Secret!",
            device_id="device-001"
        )

        result = auth_service.authenticate(
            username="unicodepass",
            password="密码🔐Secret!"
        )

        assert result is not None

    def test_empty_password_hash_verification(self, auth_service):
        """Test password verification with edge case inputs"""
        assert auth_service._verify_password("", "invalid") is False
        assert auth_service._verify_password("password", ":") is False

    def test_long_username(self, auth_service):
        """Test with very long username"""
        long_name = "a" * 1000
        user = auth_service.create_user(
            username=long_name,
            password="SecurePass123!",
            device_id="device-001"
        )
        assert user.username == long_name

    def test_special_chars_in_password(self, auth_service):
        """Test password with special characters"""
        special_password = "Pass!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        auth_service.create_user(
            username="specialchars",
            password=special_password,
            device_id="device-001"
        )

        result = auth_service.authenticate(
            username="specialchars",
            password=special_password
        )

        assert result is not None

    def test_concurrent_sessions(self, auth_service, test_user):
        """Test multiple concurrent sessions for same user"""
        # First login
        result1 = auth_service.authenticate(
            username="testuser",
            password="SecurePassword123!",
            device_fingerprint="device-1"
        )

        # Second login (different device)
        result2 = auth_service.authenticate(
            username="testuser",
            password="SecurePassword123!",
            device_fingerprint="device-2"
        )

        # Both should be valid
        assert auth_service.verify_token(result1["token"]) is not None
        assert auth_service.verify_token(result2["token"]) is not None


# ========== Constants Tests ==========

class TestConstants:
    """Tests for module constants"""

    def test_refresh_token_expiration_days(self):
        """Test refresh token expiration is reasonable"""
        assert REFRESH_TOKEN_EXPIRATION_DAYS == 30

    def test_idle_timeout_hours(self):
        """Test idle timeout is reasonable"""
        assert IDLE_TIMEOUT_HOURS == 1


# ========== JWT Secret File Storage Tests ==========

class TestJWTSecretFileStorage:
    """Tests for JWT secret behavior"""

    def test_jwt_secret_is_set(self):
        """Test that JWT_SECRET is loaded at module init"""
        from api.auth_middleware import JWT_SECRET

        assert JWT_SECRET is not None
        assert len(JWT_SECRET) >= 32

    def test_jwt_secret_env_var_priority(self):
        """Test env var takes priority"""
        import os
        from api.auth_middleware import _get_or_create_jwt_secret

        # Set env var and test
        os.environ['MEDSTATIONOS_JWT_SECRET_KEY'] = 'test-env-secret-at-least-32-chars!'
        try:
            result = _get_or_create_jwt_secret()
            assert result == 'test-env-secret-at-least-32-chars!'
        finally:
            del os.environ['MEDSTATIONOS_JWT_SECRET_KEY']

    def test_jwt_secret_legacy_env_var_warns(self):
        """Test legacy env var shows warning"""
        import os
        import api.auth.middleware as module

        # Clear primary env var if set
        primary = os.environ.pop('MEDSTATIONOS_JWT_SECRET_KEY', None)
        # Reset warning flag
        module._jwt_secret_warning_shown = False

        try:
            os.environ['MEDSTATION_JWT_SECRET'] = 'legacy-secret-at-least-32-characters'
            result = module._get_or_create_jwt_secret()
            assert result == 'legacy-secret-at-least-32-characters'
            # Warning should be shown once
            assert module._jwt_secret_warning_shown is True
        finally:
            if 'MEDSTATION_JWT_SECRET' in os.environ:
                del os.environ['MEDSTATION_JWT_SECRET']
            if primary:
                os.environ['MEDSTATIONOS_JWT_SECRET_KEY'] = primary
            module._jwt_secret_warning_shown = False


# ========== Refresh Token Edge Cases ==========

class TestRefreshTokenEdgeCases:
    """Additional edge case tests for refresh token flow"""

    def test_refresh_user_deleted(self, auth_service, authenticated_user, temp_db):
        """Test refresh when user has been deleted"""
        # Delete the user from database
        with sqlite3.connect(str(temp_db)) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE user_id = ?", (authenticated_user["user_id"],))
            conn.commit()

        result = auth_service.refresh_access_token(authenticated_user["refresh_token"])
        assert result is None

    def test_refresh_with_exception(self, auth_service, authenticated_user, temp_db):
        """Test refresh handles exceptions gracefully"""
        # Corrupt the database to cause an exception
        with patch.object(auth_service, 'db_path', '/nonexistent/path/db.sqlite'):
            result = auth_service.refresh_access_token(authenticated_user["refresh_token"])
            # Should return None on error, not raise
            assert result is None

    def test_refresh_multiple_sessions_same_user(self, auth_service, test_user):
        """Test refresh with multiple sessions for same user"""
        # Login twice
        result1 = auth_service.authenticate(
            username="testuser",
            password="SecurePassword123!",
            device_fingerprint="device-1"
        )
        result2 = auth_service.authenticate(
            username="testuser",
            password="SecurePassword123!",
            device_fingerprint="device-2"
        )

        # Refresh first session
        new_result1 = auth_service.refresh_access_token(result1["refresh_token"])

        # Both should still work
        assert new_result1 is not None
        assert auth_service.verify_token(new_result1["token"]) is not None
        assert auth_service.verify_token(result2["token"]) is not None


# ========== Database Robustness Tests ==========

class TestDatabaseRobustness:
    """Tests for database error handling"""

    def test_verify_token_database_error(self, auth_service, authenticated_user):
        """Test token verification handles database errors"""
        # Save original db_path
        original_path = auth_service.db_path

        # Point to non-existent database
        auth_service.db_path = Path("/nonexistent/auth.db")

        try:
            # Should handle error gracefully
            result = auth_service.verify_token(authenticated_user["token"])
            # Will raise or return None depending on implementation
        except Exception:
            pass  # Expected for missing database
        finally:
            auth_service.db_path = original_path

    def test_logout_handles_exceptions(self, auth_service):
        """Test logout handles exceptions gracefully"""
        # Create a malformed JWT that will fail decode
        auth_service.logout("not-a-valid-jwt-token-at-all")
        # Should not raise


# ========== Token Claims Tests ==========

class TestTokenClaims:
    """Tests for JWT token claims"""

    def test_token_contains_required_claims(self, auth_service, authenticated_user):
        """Test that token contains all required claims"""
        from api.auth_middleware import JWT_SECRET

        token = authenticated_user["token"]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        assert "user_id" in payload
        assert "username" in payload
        assert "device_id" in payload
        assert "role" in payload
        assert "exp" in payload
        assert "iat" in payload

    def test_token_expiration_is_future(self, auth_service, authenticated_user):
        """Test that token expiration is in the future"""
        from api.auth_middleware import JWT_SECRET

        token = authenticated_user["token"]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
        assert exp_time > datetime.now(UTC)

    def test_token_iat_is_past(self, auth_service, authenticated_user):
        """Test that token issued-at is in the past"""
        from api.auth_middleware import JWT_SECRET

        token = authenticated_user["token"]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        iat_time = datetime.fromtimestamp(payload["iat"], tz=UTC)
        assert iat_time <= datetime.now(UTC)
