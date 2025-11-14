"""
Forced Password Change Flow Tests

Tests the authentication flow that enforces password change on first login
or when must_change_password flag is set.
"""

import hashlib
import secrets
import sqlite3
import pytest
from fastapi.testclient import TestClient


class TestForcedPasswordChange:
    """Test forced password change flow on first login"""

    @pytest.fixture
    def test_user_with_temp_password(self, db_connection):
        """
        Create a test user with must_change_password=1 and a temp password.
        Uses PBKDF2 hashing matching the auth_service implementation.
        """
        username = "temp_password_user"
        temp_password = "Temp!Password123"

        # Hash password using PBKDF2 (matching auth_service._hash_password)
        salt = secrets.token_bytes(32)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', temp_password.encode(), salt, 600_000)
        combined = salt.hex() + ':' + pwd_hash.hex()

        # Insert user with must_change_password=1
        cursor = db_connection.cursor()
        cursor.execute("""
            INSERT INTO users (username, password_hash, must_change_password, is_active, role)
            VALUES (?, ?, 1, 1, 'member')
        """, (username, combined))
        db_connection.commit()

        yield {"username": username, "temp_password": temp_password}

        # Cleanup
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        db_connection.commit()

    def test_login_requires_password_change(self, client: TestClient, test_user_with_temp_password):
        """
        Test that login with temp password returns 403 with
        AUTH_PASSWORD_CHANGE_REQUIRED error code.
        """
        username = test_user_with_temp_password["username"]
        temp_password = test_user_with_temp_password["temp_password"]

        # Attempt login with temp password
        login_data = {
            "username": username,
            "password": temp_password
        }

        response = client.post("/api/v1/auth/login", data=login_data)

        # Should return 403 requiring password change
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"

        response_data = response.json()

        # Check for error code indicating password change required
        # Accept either nested error_code or top-level code field
        error_code = (
            response_data.get("detail", {}).get("error_code")
            or response_data.get("error_code")
            or response_data.get("code")
        )

        assert error_code == "AUTH_PASSWORD_CHANGE_REQUIRED", \
            f"Expected AUTH_PASSWORD_CHANGE_REQUIRED, got: {error_code}"

    def test_change_password_first_login_and_login_succeeds(
        self, client: TestClient, test_user_with_temp_password
    ):
        """
        Test the complete forced password change flow:
        1. Change password using /change-password-first-login
        2. Login with new password succeeds and returns token
        """
        username = test_user_with_temp_password["username"]
        temp_password = test_user_with_temp_password["temp_password"]
        new_password = "NewSecure!Password456"

        # 1. Change password
        change_data = {
            "username": username,
            "temp_password": temp_password,
            "new_password": new_password,
            "confirm_password": new_password
        }

        change_response = client.post(
            "/api/v1/auth/change-password-first-login",
            data=change_data
        )

        # Should succeed
        assert change_response.status_code == 200, \
            f"Password change failed: {change_response.text}"

        change_result = change_response.json()
        assert change_result.get("success") is True, \
            f"Expected success=true, got: {change_result}"

        # 2. Try normal login with new password
        login_data = {
            "username": username,
            "password": new_password
        }

        login_response = client.post("/api/v1/auth/login", data=login_data)

        # Should succeed and return token
        assert login_response.status_code == 200, \
            f"Login with new password failed: {login_response.text}"

        login_result = login_response.json()

        # Check for token in response (could be "token" or "access_token")
        assert (
            "token" in login_result or "access_token" in login_result
        ), f"Expected token in response, got: {login_result.keys()}"

    def test_old_password_fails_after_change(
        self, client: TestClient, test_user_with_temp_password
    ):
        """
        Test that old temp password no longer works after password change.
        """
        username = test_user_with_temp_password["username"]
        temp_password = test_user_with_temp_password["temp_password"]
        new_password = "AnotherSecure!Pass789"

        # Change password
        change_data = {
            "username": username,
            "temp_password": temp_password,
            "new_password": new_password,
            "confirm_password": new_password
        }

        client.post("/api/v1/auth/change-password-first-login", data=change_data)

        # Try to login with old temp password
        login_data = {
            "username": username,
            "password": temp_password
        }

        response = client.post("/api/v1/auth/login", data=login_data)

        # Should fail with 401 (invalid credentials)
        assert response.status_code == 401, \
            f"Expected old password to fail, got {response.status_code}"
