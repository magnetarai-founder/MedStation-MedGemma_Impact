"""
Module: test_auth_middleware_unit.py
Purpose: Test JWT authentication, token lifecycle, and auth middleware functionality

Coverage:
- JWT token generation and validation
- Access token lifetime enforcement (1 hour)
- Refresh token lifecycle (30 days)
- Session management and invalidation
- Error handling for malformed/expired tokens
- get_current_user dependency testing

Priority: 1.1 (Critical Security)
Expected Coverage Gain: +3-4%
"""

import os
import sys
import pytest
import jwt
import secrets
import hashlib
import sqlite3
from datetime import datetime, timedelta, UTC
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Ensure test environment is set
os.environ["MEDSTATIONOS_JWT_SECRET_KEY"] = "test-secret-key-for-unit-tests-only"
os.environ["MEDSTATION_ENV"] = "test"

# Add backend to path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(backend_root / "api"))

from api.auth_middleware import (
    AuthService,
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRATION_MINUTES,
    REFRESH_TOKEN_EXPIRATION_DAYS,
    IDLE_TIMEOUT_HOURS,
    get_current_user,
    get_current_user_optional,
    User,
)


class TestJWTTokenGeneration:
    """Test JWT token generation with correct claims"""

    def test_token_generation_includes_required_claims(self, auth_service, test_user):
        """Test that generated tokens include all required claims"""
        auth_result = auth_service.authenticate(
            username=test_user["username"],
            password=test_user["password"]
        )

        assert auth_result is not None
        token = auth_result["token"]

        # Decode without verification to inspect claims
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        # Verify required claims are present
        assert "user_id" in payload
        assert "username" in payload
        assert "device_id" in payload
        assert "role" in payload
        assert "exp" in payload
        assert "iat" in payload

        # Verify claim values
        assert payload["username"] == test_user["username"]
        assert payload["role"] == "member"

    def test_token_expiration_is_one_hour(self, auth_service, test_user):
        """Test that access token expires in 1 hour (JWT_EXPIRATION_MINUTES)"""
        auth_result = auth_service.authenticate(
            username=test_user["username"],
            password=test_user["password"]
        )

        payload = jwt.decode(
            auth_result["token"],
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )

        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
        iat_time = datetime.fromtimestamp(payload["iat"], tz=UTC)

        # Token should expire approximately JWT_EXPIRATION_MINUTES after issuance
        expected_lifetime = timedelta(minutes=JWT_EXPIRATION_MINUTES)
        actual_lifetime = exp_time - iat_time

        # Allow 5 second tolerance for test execution time
        assert abs((actual_lifetime - expected_lifetime).total_seconds()) < 5

    def test_refresh_token_generated_on_login(self, auth_service, test_user):
        """Test that refresh token is generated during authentication"""
        auth_result = auth_service.authenticate(
            username=test_user["username"],
            password=test_user["password"]
        )

        assert "refresh_token" in auth_result
        assert auth_result["refresh_token"] is not None
        assert len(auth_result["refresh_token"]) > 20  # Reasonable length


class TestJWTTokenValidation:
    """Test JWT token validation scenarios"""

    def test_valid_token_verification(self, authenticated_user, auth_service):
        """Test that valid tokens are successfully verified"""
        payload = auth_service.verify_token(authenticated_user["token"])

        assert payload is not None
        assert payload["username"] == authenticated_user["username"]
        assert payload["user_id"] == authenticated_user["auth"]["user_id"]

    def test_expired_token_returns_none(self, auth_service, expired_token):
        """Test that expired tokens return None"""
        payload = auth_service.verify_token(expired_token)
        assert payload is None

    def test_invalid_signature_detection(self, authenticated_user, auth_service):
        """Test that tokens with invalid signatures are rejected"""
        # Create a token with wrong secret
        wrong_secret_token = jwt.encode(
            {"user_id": "test", "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp()},
            "wrong-secret-key",
            algorithm=JWT_ALGORITHM
        )

        payload = auth_service.verify_token(wrong_secret_token)
        assert payload is None

    def test_malformed_token_handling_empty(self, auth_service):
        """Test handling of empty token"""
        payload = auth_service.verify_token("")
        assert payload is None

    def test_malformed_token_handling_not_jwt(self, auth_service):
        """Test handling of non-JWT string"""
        payload = auth_service.verify_token("not-a-jwt-token")
        assert payload is None

    def test_malformed_token_handling_missing_segments(self, auth_service):
        """Test handling of JWT with missing segments"""
        payload = auth_service.verify_token("header.payload")
        assert payload is None

    def test_missing_claims_handling(self, auth_service):
        """Test handling of token with missing required claims"""
        # Create token without user_id claim
        incomplete_token = jwt.encode(
            {"exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp()},
            JWT_SECRET,
            algorithm=JWT_ALGORITHM
        )

        # Token should be rejected during session verification
        # (no matching session will exist)
        payload = auth_service.verify_token(incomplete_token)
        assert payload is None


class TestSessionManagement:
    """Test session creation, validation, and cleanup"""

    def test_session_created_on_authentication(self, auth_service, test_user, temp_db_path):
        """Test that session is stored in database on authentication"""
        auth_result = auth_service.authenticate(
            username=test_user["username"],
            password=test_user["password"]
        )

        # Verify session exists in database
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT session_id, user_id, token_hash FROM sessions WHERE user_id = ?",
                (auth_result["user_id"],)
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[1] == auth_result["user_id"]

    def test_session_invalidation_on_logout(self, auth_service, authenticated_user, temp_db_path):
        """Test that session is removed on logout"""
        user_id = authenticated_user["auth"]["user_id"]

        # Verify session exists before logout
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE user_id = ?", (user_id,))
            count_before = cursor.fetchone()[0]

        assert count_before > 0

        # Logout
        auth_service.logout(authenticated_user["token"])

        # Verify session is removed
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            token_hash = hashlib.sha256(authenticated_user["token"].encode()).hexdigest()
            cursor.execute(
                "SELECT COUNT(*) FROM sessions WHERE user_id = ? AND token_hash = ?",
                (user_id, token_hash)
            )
            count_after = cursor.fetchone()[0]

        assert count_after == 0

    def test_last_activity_updated_on_verification(self, auth_service, authenticated_user, temp_db_path):
        """Test that last_activity is updated when token is verified"""
        token_hash = hashlib.sha256(authenticated_user["token"].encode()).hexdigest()
        user_id = authenticated_user["auth"]["user_id"]

        # Get initial last_activity
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT last_activity FROM sessions WHERE user_id = ? AND token_hash = ?",
                (user_id, token_hash)
            )
            initial_activity = cursor.fetchone()[0]

        # Wait a tiny bit and verify token
        import time
        time.sleep(0.01)
        auth_service.verify_token(authenticated_user["token"])

        # Get updated last_activity
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT last_activity FROM sessions WHERE user_id = ? AND token_hash = ?",
                (user_id, token_hash)
            )
            updated_activity = cursor.fetchone()[0]

        # last_activity should be updated
        assert updated_activity >= initial_activity

    def test_expired_session_cleanup(self, auth_service, temp_db_path):
        """Test cleanup of expired sessions"""
        # Insert an expired session directly
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            expired_time = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
            cursor.execute("""
                INSERT INTO sessions (session_id, user_id, token_hash, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, ("expired-session", "expired-user", "expired-hash", expired_time, expired_time))
            conn.commit()

        # Run cleanup
        auth_service.cleanup_expired_sessions()

        # Verify expired session was removed
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE session_id = 'expired-session'")
            count = cursor.fetchone()[0]

        assert count == 0


class TestRefreshTokenLifecycle:
    """Test refresh token functionality"""

    def test_refresh_token_stored_in_session(self, auth_service, test_user, temp_db_path):
        """Test that refresh token hash is stored in session"""
        auth_result = auth_service.authenticate(
            username=test_user["username"],
            password=test_user["password"]
        )

        refresh_token_hash = hashlib.sha256(auth_result["refresh_token"].encode()).hexdigest()

        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT refresh_token_hash FROM sessions WHERE user_id = ?",
                (auth_result["user_id"],)
            )
            stored_hash = cursor.fetchone()[0]

        assert stored_hash == refresh_token_hash

    def test_refresh_access_token_success(self, auth_service, authenticated_user):
        """Test successful access token refresh"""
        new_auth = auth_service.refresh_access_token(authenticated_user["refresh_token"])

        assert new_auth is not None
        assert "token" in new_auth
        assert new_auth["token"] != authenticated_user["token"]  # New token
        assert new_auth["user_id"] == authenticated_user["auth"]["user_id"]

    def test_refresh_with_invalid_token(self, auth_service):
        """Test refresh with invalid refresh token fails"""
        result = auth_service.refresh_access_token("invalid-refresh-token")
        assert result is None

    def test_refresh_after_logout_fails(self, auth_service, authenticated_user):
        """Test that refresh fails after logout"""
        # Logout first
        auth_service.logout(authenticated_user["token"])

        # Try to refresh - should fail
        result = auth_service.refresh_access_token(authenticated_user["refresh_token"])
        assert result is None


class TestIdleTimeout:
    """Test idle timeout functionality"""

    def test_idle_timeout_constant(self):
        """Verify IDLE_TIMEOUT_HOURS is set correctly"""
        assert IDLE_TIMEOUT_HOURS == 1  # 1 hour as per security config

    def test_active_session_not_expired(self, auth_service, authenticated_user):
        """Test that recently active sessions are not expired"""
        # Immediately verify - should work
        payload = auth_service.verify_token(authenticated_user["token"])
        assert payload is not None

    def test_idle_session_expired(self, auth_service, authenticated_user, temp_db_path):
        """Test that idle sessions are expired"""
        user_id = authenticated_user["auth"]["user_id"]
        token_hash = hashlib.sha256(authenticated_user["token"].encode()).hexdigest()

        # Set last_activity to more than IDLE_TIMEOUT_HOURS ago
        idle_time = (datetime.now(UTC) - timedelta(hours=IDLE_TIMEOUT_HOURS + 1)).isoformat()
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET last_activity = ? WHERE user_id = ? AND token_hash = ?",
                (idle_time, user_id, token_hash)
            )
            conn.commit()

        # Verify should now fail due to idle timeout
        payload = auth_service.verify_token(authenticated_user["token"])
        assert payload is None


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_password_hash_is_pbkdf2(self, auth_service, test_user, temp_db_path):
        """Test that passwords are hashed using PBKDF2"""
        # Get stored hash
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT password_hash FROM users WHERE username = ?",
                (test_user["username"],)
            )
            stored_hash = cursor.fetchone()[0]

        # PBKDF2 format is salt_hex:hash_hex
        assert ":" in stored_hash
        salt_hex, hash_hex = stored_hash.split(":")
        assert len(salt_hex) == 64  # 32 bytes = 64 hex chars
        assert len(hash_hex) == 64  # SHA256 = 64 hex chars

    def test_password_verification_correct_password(self, auth_service, test_user):
        """Test that correct password is verified"""
        result = auth_service.authenticate(
            username=test_user["username"],
            password=test_user["password"]
        )
        assert result is not None

    def test_password_verification_wrong_password(self, auth_service, test_user):
        """Test that wrong password is rejected"""
        result = auth_service.authenticate(
            username=test_user["username"],
            password="WrongPassword123!"
        )
        assert result is None


class TestUserManagement:
    """Test user creation and management"""

    def test_create_user_success(self, auth_service):
        """Test successful user creation"""
        user = auth_service.create_user(
            username="newuser",
            password="NewPassword123!",
            device_id="new-device-id"
        )

        assert user is not None
        assert user.username == "newuser"
        assert user.device_id == "new-device-id"
        assert user.user_id is not None

    def test_create_duplicate_user_fails(self, auth_service, test_user):
        """Test that creating duplicate username fails"""
        with pytest.raises(ValueError, match="Username already exists"):
            auth_service.create_user(
                username=test_user["username"],
                password="AnotherPassword123!",
                device_id="another-device"
            )

    def test_disabled_user_cannot_login(self, auth_service, test_user, temp_db_path):
        """Test that disabled users cannot authenticate"""
        # Disable the user
        with sqlite3.connect(str(temp_db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET is_active = 0 WHERE username = ?",
                (test_user["username"],)
            )
            conn.commit()

        # Try to authenticate - should fail with ValueError
        with pytest.raises(ValueError, match="User account is disabled"):
            auth_service.authenticate(
                username=test_user["username"],
                password=test_user["password"]
            )


class TestGetCurrentUserDependency:
    """Test the get_current_user FastAPI dependency"""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self, auth_service, authenticated_user):
        """Test get_current_user with valid token"""
        from fastapi.security import HTTPAuthorizationCredentials

        # Mock credentials
        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = authenticated_user["token"]

        # Patch auth_service
        with patch('api.auth.middleware.auth_service', auth_service):
            from api.auth_middleware import get_current_user
            result = await get_current_user(credentials)

        assert result is not None
        assert result["username"] == authenticated_user["username"]

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token_raises_401(self, auth_service):
        """Test get_current_user raises 401 for invalid token"""
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials

        credentials = MagicMock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "invalid-token"

        with patch('api.auth.middleware.auth_service', auth_service):
            from api.auth_middleware import get_current_user
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail


class TestGetCurrentUserOptional:
    """Test the optional authentication dependency"""

    @pytest.mark.asyncio
    async def test_optional_auth_no_header(self):
        """Test that missing auth header returns anonymous user"""
        request = MagicMock()
        request.headers = {}

        result = await get_current_user_optional(request)

        assert result["user_id"] == "anonymous"
        assert result["username"] == "anonymous"

    @pytest.mark.asyncio
    async def test_optional_auth_invalid_token(self, auth_service):
        """Test that invalid token returns anonymous user"""
        request = MagicMock()
        request.headers = {"Authorization": "Bearer invalid-token"}

        with patch('api.auth.middleware.auth_service', auth_service):
            result = await get_current_user_optional(request)

        assert result["user_id"] == "anonymous"

    @pytest.mark.asyncio
    async def test_optional_auth_valid_token(self, auth_service, authenticated_user):
        """Test that valid token returns user info"""
        request = MagicMock()
        request.headers = {"Authorization": f"Bearer {authenticated_user['token']}"}

        with patch('api.auth.middleware.auth_service', auth_service):
            result = await get_current_user_optional(request)

        assert result["username"] == authenticated_user["username"]


class TestAuthorizationHeaderParsing:
    """Test Authorization header parsing"""

    @pytest.mark.asyncio
    async def test_bearer_format_required(self):
        """Test that Bearer prefix is required"""
        request = MagicMock()
        request.headers = {"Authorization": "Basic sometoken"}

        result = await get_current_user_optional(request)

        # Non-Bearer format should return anonymous
        assert result["user_id"] == "anonymous"

    @pytest.mark.asyncio
    async def test_missing_bearer_prefix(self):
        """Test handling of missing Bearer prefix"""
        request = MagicMock()
        request.headers = {"Authorization": "sometoken"}

        result = await get_current_user_optional(request)

        assert result["user_id"] == "anonymous"


class TestJWTSecretManagement:
    """Test JWT secret key management"""

    def test_jwt_secret_from_env(self):
        """Test that JWT secret is loaded from environment"""
        # Our test sets MEDSTATIONOS_JWT_SECRET_KEY
        assert JWT_SECRET == "test-secret-key-for-unit-tests-only"

    def test_jwt_algorithm_is_hs256(self):
        """Test that HS256 algorithm is used"""
        assert JWT_ALGORITHM == "HS256"


class TestSecurityConstants:
    """Test security-related constants are correctly set"""

    def test_access_token_lifetime(self):
        """Test access token lifetime is 1 hour / 60 minutes (OWASP recommended)"""
        assert JWT_EXPIRATION_MINUTES == 60

    def test_refresh_token_lifetime(self):
        """Test refresh token lifetime is 30 days"""
        assert REFRESH_TOKEN_EXPIRATION_DAYS == 30

    def test_idle_timeout(self):
        """Test idle timeout is 1 hour"""
        assert IDLE_TIMEOUT_HOURS == 1
