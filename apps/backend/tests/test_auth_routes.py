"""
Comprehensive tests for api/auth_routes.py

Tests cover:
- Setup check endpoint
- User registration with rate limiting
- Login with JWT and refresh tokens
- Forced password change after reset
- Token refresh flow
- Logout (including expired tokens)
- Current user info and token verification
- Session cleanup
- Permissions endpoint
- Rate limiting behavior
- Error handling
"""

import pytest
import sqlite3
import jwt
import secrets
import os
from datetime import datetime, timedelta, UTC
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.auth_routes import router
from api.auth_middleware import AuthService, JWT_SECRET, JWT_ALGORITHM


# ========== Fixtures ==========

@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing"""
    db_path = tmp_path / "test_auth.db"

    # Create tables
    conn = sqlite3.connect(str(db_path))
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
            role TEXT DEFAULT 'member',
            must_change_password INTEGER DEFAULT 0
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
    conn.close()

    return db_path


@pytest.fixture
def auth_service(temp_db):
    """Create AuthService with temp database"""
    return AuthService(db_path=str(temp_db))


@pytest.fixture
def app(auth_service):
    """Create FastAPI app with auth routes"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app, auth_service):
    """Create test client with mocked auth service"""
    with patch('api.auth.routes.auth_service', auth_service):
        with patch('api.auth.routes.rate_limiter') as mock_rate_limiter:
            # Default: allow all requests
            mock_rate_limiter.check_rate_limit.return_value = True
            yield TestClient(app)


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
    """Create and authenticate a test user"""
    return auth_service.authenticate(
        username="testuser",
        password="SecurePassword123!"
    )


@pytest.fixture
def auth_headers(authenticated_user):
    """Get authorization headers for authenticated requests"""
    return {"Authorization": f"Bearer {authenticated_user['token']}"}


# ========== Setup Check Tests ==========

class TestSetupNeeded:
    """Tests for /auth/setup-needed endpoint"""

    def test_setup_needed_no_users(self, client, temp_db):
        """Test setup needed when no users exist"""
        with patch('api.auth.routes.auth_service') as mock_service:
            mock_service.db_path = temp_db

            response = client.get("/api/v1/auth/setup-needed")

        assert response.status_code == 200
        data = response.json()
        assert "setup_needed" in data

    def test_setup_needed_users_exist(self, client, auth_service, test_user, temp_db):
        """Test setup not needed when users exist"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.get("/api/v1/auth/setup-needed")

        assert response.status_code == 200
        data = response.json()
        assert data["setup_needed"] is False

    def test_setup_needed_db_error(self, client):
        """Test setup needed returns True on database error"""
        with patch('api.auth.routes.auth_service') as mock_service:
            mock_service.db_path = Path("/nonexistent/path.db")

            response = client.get("/api/v1/auth/setup-needed")

        assert response.status_code == 200
        assert response.json()["setup_needed"] is True


# ========== Registration Tests ==========

class TestRegister:
    """Tests for /auth/register endpoint"""

    def test_register_success(self, client, auth_service, temp_db):
        """Test successful user registration"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "newuser",
                    "password": "SecurePassword123!",
                    "device_id": "device-001"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert "user_id" in data

    def test_register_duplicate_username(self, client, auth_service, test_user):
        """Test registration with duplicate username"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "testuser",  # Already exists
                    "password": "AnotherPassword123!",
                    "device_id": "device-002"
                }
            )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]["message"].lower()

    def test_register_short_username(self, client, auth_service):
        """Test registration with too short username"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "ab",  # Less than 3 chars
                    "password": "SecurePassword123!",
                    "device_id": "device-001"
                }
            )

        assert response.status_code == 422  # Validation error

    def test_register_short_password(self, client, auth_service):
        """Test registration with too short password"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "newuser",
                    "password": "short",  # Less than 8 chars
                    "device_id": "device-001"
                }
            )

        assert response.status_code == 422  # Validation error

    def test_register_rate_limited(self, app, auth_service):
        """Test registration rate limiting"""
        with patch('api.auth.routes.auth_service', auth_service):
            with patch('api.auth.routes.rate_limiter') as mock_limiter:
                mock_limiter.check_rate_limit.return_value = False

                client = TestClient(app)
                response = client.post(
                    "/api/v1/auth/register",
                    json={
                        "username": "newuser",
                        "password": "SecurePassword123!",
                        "device_id": "device-001"
                    }
                )

        assert response.status_code == 429


# ========== Login Tests ==========

class TestLogin:
    """Tests for /auth/login endpoint"""

    def test_login_success(self, client, auth_service, test_user):
        """Test successful login"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "username": "testuser",
                    "password": "SecurePassword123!"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "refresh_token" in data
        assert data["username"] == "testuser"

    def test_login_wrong_password(self, client, auth_service, test_user):
        """Test login with wrong password"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "username": "testuser",
                    "password": "WrongPassword!"
                }
            )

        assert response.status_code == 401

    def test_login_nonexistent_user(self, client, auth_service):
        """Test login with nonexistent user"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "username": "nonexistent",
                    "password": "AnyPassword123!"
                }
            )

        assert response.status_code == 401

    def test_login_disabled_account(self, client, auth_service, test_user, temp_db):
        """Test login with disabled account"""
        # Disable the user
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_active = 0 WHERE username = ?", ("testuser",))
        conn.commit()
        conn.close()

        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "username": "testuser",
                    "password": "SecurePassword123!"
                }
            )

        assert response.status_code == 403

    def test_login_rate_limited(self, app, auth_service, test_user):
        """Test login rate limiting"""
        with patch('api.auth.routes.auth_service', auth_service):
            with patch('api.auth.routes.rate_limiter') as mock_limiter:
                mock_limiter.check_rate_limit.return_value = False

                client = TestClient(app)
                response = client.post(
                    "/api/v1/auth/login",
                    json={
                        "username": "testuser",
                        "password": "SecurePassword123!"
                    }
                )

        assert response.status_code == 429

    def test_login_must_change_password(self, client, auth_service, test_user, temp_db):
        """Test login when must_change_password is set"""
        # Set must_change_password flag
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET must_change_password = 1 WHERE username = ?",
            ("testuser",)
        )
        conn.commit()
        conn.close()

        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "username": "testuser",
                    "password": "SecurePassword123!"
                }
            )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["error_code"] == "AUTH_PASSWORD_CHANGE_REQUIRED"

    def test_login_with_device_fingerprint(self, client, auth_service, test_user):
        """Test login with device fingerprint"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "username": "testuser",
                    "password": "SecurePassword123!",
                    "device_fingerprint": "fingerprint-123"
                }
            )

        assert response.status_code == 200


# ========== Password Change Tests ==========

class TestChangePasswordFirstLogin:
    """Tests for /auth/change-password-first-login endpoint"""

    def test_change_password_success(self, client, auth_service, test_user, temp_db):
        """Test successful password change after reset"""
        # Set must_change_password flag
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET must_change_password = 1 WHERE username = ?",
            ("testuser",)
        )
        conn.commit()
        conn.close()

        with patch('api.auth.routes.auth_service', auth_service):
            # Patch at source module since import happens inside the function
            with patch('password_breach_checker.check_password_breach', new_callable=AsyncMock) as mock_breach:
                mock_breach.return_value = (False, 0)  # Not breached

                response = client.post(
                    "/api/v1/auth/change-password-first-login",
                    json={
                        "username": "testuser",
                        "temp_password": "SecurePassword123!",
                        "new_password": "NewSecure@Password1",
                        "confirm_password": "NewSecure@Password1"
                    }
                )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_change_password_mismatch(self, client, auth_service, test_user, temp_db):
        """Test password change with mismatched passwords"""
        # Set must_change_password flag
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET must_change_password = 1 WHERE username = ?",
            ("testuser",)
        )
        conn.commit()
        conn.close()

        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/change-password-first-login",
                json={
                    "username": "testuser",
                    "temp_password": "SecurePassword123!",
                    "new_password": "NewSecure@Password1",
                    "confirm_password": "DifferentPassword1!"
                }
            )

        assert response.status_code == 400
        # Error details are in 'suggestion' and 'context.errors' fields
        detail = response.json()["detail"]
        error_text = (
            detail.get("message", "") +
            detail.get("suggestion", "") +
            str(detail.get("context", {}).get("errors", ""))
        )
        assert "do not match" in error_text.lower() or "match" in error_text.lower()

    def test_change_password_too_short(self, client, auth_service, test_user, temp_db):
        """Test password change with too short password

        Note: Pydantic validates min_length=12 before route logic runs,
        so this returns 422 (Unprocessable Entity) not 400.
        """
        # Set must_change_password flag
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET must_change_password = 1 WHERE username = ?",
            ("testuser",)
        )
        conn.commit()
        conn.close()

        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/change-password-first-login",
                json={
                    "username": "testuser",
                    "temp_password": "SecurePassword123!",
                    "new_password": "Short1!",
                    "confirm_password": "Short1!"
                }
            )

        # Pydantic min_length=12 validation returns 422
        assert response.status_code == 422

    def test_change_password_missing_uppercase(self, client, auth_service, test_user, temp_db):
        """Test password change missing uppercase"""
        # Set must_change_password flag
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET must_change_password = 1 WHERE username = ?",
            ("testuser",)
        )
        conn.commit()
        conn.close()

        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/change-password-first-login",
                json={
                    "username": "testuser",
                    "temp_password": "SecurePassword123!",
                    "new_password": "alllowercase123!",
                    "confirm_password": "alllowercase123!"
                }
            )

        assert response.status_code == 400
        detail = response.json()["detail"]
        error_text = (
            detail.get("message", "") +
            detail.get("suggestion", "") +
            str(detail.get("context", {}).get("errors", ""))
        )
        assert "uppercase" in error_text.lower()

    def test_change_password_missing_lowercase(self, client, auth_service, test_user, temp_db):
        """Test password change missing lowercase"""
        # Set must_change_password flag
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET must_change_password = 1 WHERE username = ?",
            ("testuser",)
        )
        conn.commit()
        conn.close()

        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/change-password-first-login",
                json={
                    "username": "testuser",
                    "temp_password": "SecurePassword123!",
                    "new_password": "ALLUPPERCASE123!",
                    "confirm_password": "ALLUPPERCASE123!"
                }
            )

        assert response.status_code == 400
        detail = response.json()["detail"]
        error_text = (
            detail.get("message", "") +
            detail.get("suggestion", "") +
            str(detail.get("context", {}).get("errors", ""))
        )
        assert "lowercase" in error_text.lower()

    def test_change_password_missing_digit(self, client, auth_service, test_user, temp_db):
        """Test password change missing digit"""
        # Set must_change_password flag
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET must_change_password = 1 WHERE username = ?",
            ("testuser",)
        )
        conn.commit()
        conn.close()

        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/change-password-first-login",
                json={
                    "username": "testuser",
                    "temp_password": "SecurePassword123!",
                    "new_password": "NoDigitsHere!!!",
                    "confirm_password": "NoDigitsHere!!!"
                }
            )

        assert response.status_code == 400
        detail = response.json()["detail"]
        error_text = (
            detail.get("message", "") +
            detail.get("suggestion", "") +
            str(detail.get("context", {}).get("errors", ""))
        )
        assert "digit" in error_text.lower()

    def test_change_password_missing_special(self, client, auth_service, test_user, temp_db):
        """Test password change missing special character"""
        # Set must_change_password flag
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET must_change_password = 1 WHERE username = ?",
            ("testuser",)
        )
        conn.commit()
        conn.close()

        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/change-password-first-login",
                json={
                    "username": "testuser",
                    "temp_password": "SecurePassword123!",
                    "new_password": "NoSpecialChar123",
                    "confirm_password": "NoSpecialChar123"
                }
            )

        assert response.status_code == 400
        detail = response.json()["detail"]
        error_text = (
            detail.get("message", "") +
            detail.get("suggestion", "") +
            str(detail.get("context", {}).get("errors", ""))
        )
        assert "special" in error_text.lower()

    def test_change_password_wrong_temp_password(self, client, auth_service, test_user, temp_db):
        """Test password change with wrong temp password"""
        # Set must_change_password flag
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET must_change_password = 1 WHERE username = ?",
            ("testuser",)
        )
        conn.commit()
        conn.close()

        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/change-password-first-login",
                json={
                    "username": "testuser",
                    "temp_password": "WrongTempPassword!",
                    "new_password": "NewSecure@Password1",
                    "confirm_password": "NewSecure@Password1"
                }
            )

        assert response.status_code == 401

    def test_change_password_already_changed(self, client, auth_service, test_user):
        """Test password change when flag not set"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/change-password-first-login",
                json={
                    "username": "testuser",
                    "temp_password": "SecurePassword123!",
                    "new_password": "NewSecure@Password1",
                    "confirm_password": "NewSecure@Password1"
                }
            )

        assert response.status_code == 400
        detail = response.json()["detail"]
        error_text = (
            detail.get("message", "") +
            detail.get("suggestion", "") +
            str(detail.get("context", {}).get("errors", ""))
        )
        assert "already" in error_text.lower() or "changed" in error_text.lower()


# ========== Token Refresh Tests ==========

class TestRefreshToken:
    """Tests for /auth/refresh endpoint"""

    def test_refresh_success(self, client, auth_service, authenticated_user):
        """Test successful token refresh"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": authenticated_user["refresh_token"]}
            )

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["token"] != authenticated_user["token"]  # New token

    def test_refresh_invalid_token(self, client, auth_service):
        """Test refresh with invalid token"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "invalid-refresh-token"}
            )

        assert response.status_code == 401

    def test_refresh_rate_limited(self, app, auth_service, authenticated_user):
        """Test refresh rate limiting"""
        with patch('api.auth.routes.auth_service', auth_service):
            with patch('api.auth.routes.rate_limiter') as mock_limiter:
                mock_limiter.check_rate_limit.return_value = False

                client = TestClient(app)
                response = client.post(
                    "/api/v1/auth/refresh",
                    json={"refresh_token": authenticated_user["refresh_token"]}
                )

        assert response.status_code == 429


# ========== Logout Tests ==========

class TestLogout:
    """Tests for /auth/logout endpoint"""

    def test_logout_success(self, client, auth_service, auth_headers):
        """Test successful logout"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post("/api/v1/auth/logout", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"

    def test_logout_no_token(self, client, auth_service):
        """Test logout without token"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post("/api/v1/auth/logout")

        assert response.status_code == 401

    def test_logout_expired_token(self, client, auth_service, authenticated_user):
        """Test logout with expired token still works"""
        # Create an expired token
        expired_payload = {
            "user_id": authenticated_user["user_id"],
            "username": authenticated_user["username"],
            "device_id": authenticated_user["device_id"],
            "role": "member",
            "exp": (datetime.now(UTC) - timedelta(hours=1)).timestamp(),
            "iat": (datetime.now(UTC) - timedelta(hours=2)).timestamp()
        }
        expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {expired_token}"}
            )

        # Should succeed even with expired token
        assert response.status_code == 200

    def test_logout_invalid_signature(self, client, auth_service):
        """Test logout with invalid signature returns success"""
        fake_token = jwt.encode(
            {"user_id": "fake", "username": "fake"},
            "wrong-secret",
            algorithm=JWT_ALGORITHM
        )

        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {fake_token}"}
            )

        # Should succeed (treated as already logged out)
        assert response.status_code == 200


# ========== Current User Tests ==========

class TestCurrentUser:
    """Tests for /auth/me endpoint"""

    def test_get_current_user_success(self, app, auth_service, authenticated_user, auth_headers):
        """Test getting current user info"""
        from api.auth_routes import get_current_user

        # Override the dependency to return our mock user
        mock_user = {
            "user_id": authenticated_user["user_id"],
            "username": authenticated_user["username"],
            "device_id": authenticated_user["device_id"],
            "role": authenticated_user["role"]
        }
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            with patch('api.auth.routes.auth_service', auth_service):
                client = TestClient(app)
                response = client.get("/api/v1/auth/me", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["username"] == authenticated_user["username"]
        finally:
            app.dependency_overrides.clear()

    def test_get_current_user_no_auth(self, client, auth_service):
        """Test getting current user without auth"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.get("/api/v1/auth/me")

        assert response.status_code in [401, 403]


# ========== Token Verification Tests ==========

class TestVerifyToken:
    """Tests for /auth/verify endpoint"""

    def test_verify_valid_token(self, app, auth_service, authenticated_user, auth_headers):
        """Test verifying valid token"""
        from api.auth_routes import get_current_user

        # Override the dependency
        mock_user = {
            "user_id": authenticated_user["user_id"],
            "username": authenticated_user["username"]
        }
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            with patch('api.auth.routes.auth_service', auth_service):
                client = TestClient(app)
                response = client.get("/api/v1/auth/verify", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
        finally:
            app.dependency_overrides.clear()

    def test_verify_invalid_token(self, client, auth_service):
        """Test verifying invalid token"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.get(
                "/api/v1/auth/verify",
                headers={"Authorization": "Bearer invalid-token"}
            )

        assert response.status_code in [401, 403]


# ========== Session Cleanup Tests ==========

class TestSessionCleanup:
    """Tests for /auth/cleanup-sessions endpoint"""

    def test_cleanup_sessions_success(self, client, auth_service):
        """Test session cleanup endpoint"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post("/api/v1/auth/cleanup-sessions")

        assert response.status_code == 200
        assert "cleaned up" in response.json()["message"].lower()


# ========== Permissions Tests ==========

class TestPermissions:
    """Tests for /auth/permissions endpoint"""

    def test_get_permissions_success(self, app, auth_service, authenticated_user, auth_headers):
        """Test getting user permissions"""
        from api.auth_routes import get_current_user

        mock_context = Mock()
        mock_context.user_id = authenticated_user["user_id"]
        mock_context.username = authenticated_user["username"]
        mock_context.role = "member"
        mock_context.effective_permissions = {"vault.read": True, "vault.write": False}
        mock_context.profiles = []
        mock_context.permission_sets = []

        # Override the dependency
        mock_user = {
            "user_id": authenticated_user["user_id"],
            "username": authenticated_user["username"]
        }
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            with patch('api.auth.routes.auth_service', auth_service):
                with patch('permission_engine.get_permission_engine') as mock_engine:
                    engine_instance = Mock()
                    engine_instance.load_user_context.return_value = mock_context
                    mock_engine.return_value = engine_instance

                    with patch('api.auth.routes.cache_query') as mock_cache:
                        # Execute the fetch function directly
                        mock_cache.side_effect = lambda key, func, ttl: func()

                        client = TestClient(app)
                        response = client.get("/api/v1/auth/permissions", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "permissions" in data
        finally:
            app.dependency_overrides.clear()

    def test_get_permissions_with_team(self, app, auth_service, authenticated_user, auth_headers):
        """Test getting permissions with team context"""
        from api.auth_routes import get_current_user

        mock_context = Mock()
        mock_context.user_id = authenticated_user["user_id"]
        mock_context.username = authenticated_user["username"]
        mock_context.role = "member"
        mock_context.effective_permissions = {}
        mock_context.profiles = []
        mock_context.permission_sets = []

        # Override the dependency
        mock_user = {
            "user_id": authenticated_user["user_id"],
            "username": authenticated_user["username"]
        }
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            with patch('api.auth.routes.auth_service', auth_service):
                with patch('permission_engine.get_permission_engine') as mock_engine:
                    engine_instance = Mock()
                    engine_instance.load_user_context.return_value = mock_context
                    mock_engine.return_value = engine_instance

                    with patch('api.auth.routes.cache_query') as mock_cache:
                        mock_cache.side_effect = lambda key, func, ttl: func()

                        client = TestClient(app)
                        response = client.get(
                            "/api/v1/auth/permissions?team_id=team-123",
                            headers=auth_headers
                        )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()


# ========== Rate Limiting Tests ==========

class TestRateLimiting:
    """Tests for rate limiting behavior"""

    def test_register_rate_limit_key(self, app, auth_service):
        """Test that registration uses correct rate limit key"""
        with patch('api.auth.routes.auth_service', auth_service):
            with patch('api.auth.routes.rate_limiter') as mock_limiter:
                mock_limiter.check_rate_limit.return_value = True
                with patch('api.auth.routes.get_client_ip', return_value="192.168.1.100"):
                    client = TestClient(app)
                    client.post(
                        "/api/v1/auth/register",
                        json={
                            "username": "newuser",
                            "password": "SecurePassword123!",
                            "device_id": "device-001"
                        }
                    )

                # Verify rate limiter was called with correct key
                mock_limiter.check_rate_limit.assert_called()
                call_args = mock_limiter.check_rate_limit.call_args
                assert "auth:register:" in call_args[0][0]

    def test_login_rate_limit_key(self, app, auth_service, test_user):
        """Test that login uses correct rate limit key"""
        with patch('api.auth.routes.auth_service', auth_service):
            with patch('api.auth.routes.rate_limiter') as mock_limiter:
                mock_limiter.check_rate_limit.return_value = True
                with patch('api.auth.routes.get_client_ip', return_value="192.168.1.100"):
                    client = TestClient(app)
                    client.post(
                        "/api/v1/auth/login",
                        json={
                            "username": "testuser",
                            "password": "SecurePassword123!"
                        }
                    )

                # Verify rate limiter was called with correct key
                mock_limiter.check_rate_limit.assert_called()
                call_args = mock_limiter.check_rate_limit.call_args
                assert "auth:login:" in call_args[0][0]


# ========== Pydantic Model Tests ==========

class TestRequestModels:
    """Tests for request model validation"""

    def test_register_request_validation(self):
        """Test RegisterRequest validation"""
        from api.auth_routes import RegisterRequest

        # Valid request
        req = RegisterRequest(
            username="validuser",
            password="ValidPass123!",
            device_id="device-001"
        )
        assert req.username == "validuser"

        # Invalid: short username
        with pytest.raises(Exception):
            RegisterRequest(
                username="ab",
                password="ValidPass123!",
                device_id="device-001"
            )

    def test_login_request_validation(self):
        """Test LoginRequest validation"""
        from api.auth_routes import LoginRequest

        # Valid request
        req = LoginRequest(
            username="testuser",
            password="password"
        )
        assert req.username == "testuser"
        assert req.device_fingerprint is None

        # With device fingerprint
        req2 = LoginRequest(
            username="testuser",
            password="password",
            device_fingerprint="fp-123"
        )
        assert req2.device_fingerprint == "fp-123"

    def test_refresh_request_validation(self):
        """Test RefreshRequest validation"""
        from api.auth_routes import RefreshRequest

        req = RefreshRequest(refresh_token="token-123")
        assert req.refresh_token == "token-123"

    def test_login_response_model(self):
        """Test LoginResponse model"""
        from api.auth_routes import LoginResponse

        resp = LoginResponse(
            token="jwt-token",
            refresh_token="refresh-token",
            user_id="user-123",
            username="testuser",
            device_id="device-001",
            role="member"
        )
        assert resp.token == "jwt-token"
        assert resp.role == "member"
        assert resp.expires_in == 7 * 24 * 60 * 60


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_login_unicode_username(self, client, auth_service, temp_db):
        """Test login with unicode username"""
        # Create user with unicode name
        auth_service.create_user(
            username="用户名",
            password="SecurePassword123!",
            device_id="device-001"
        )

        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "username": "用户名",
                    "password": "SecurePassword123!"
                }
            )

        assert response.status_code == 200

    def test_empty_authorization_header(self, client, auth_service):
        """Test logout with empty authorization header"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": ""}
            )

        assert response.status_code == 401

    def test_malformed_bearer_token(self, client, auth_service):
        """Test logout with malformed bearer token"""
        with patch('api.auth.routes.auth_service', auth_service):
            response = client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": "NotBearer token"}
            )

        assert response.status_code == 401
