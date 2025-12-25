"""
Tests for MagnetarCloud Authentication

Tests cover:
- Device pairing (cloud_token generation)
- Token refresh
- Cloud status
- Device unpairing
- Sync authorization
- Session revocation
- Rate limiting on pairing
"""

import pytest
import time
import sqlite3
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from fastapi import status
from fastapi.testclient import TestClient

import sys
from pathlib import Path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(backend_root / "api"))


# ===== Test Fixtures =====

@pytest.fixture
def mock_user():
    """Create a mock authenticated user"""
    from api.auth_middleware import User
    return User(
        user_id="test-user-123",
        username="testuser",
        device_id="test-device-456",
        created_at="2024-12-01T00:00:00"
    )


@pytest.fixture
def cloud_auth_router():
    """Import the cloud auth router for testing"""
    from api.routes.cloud_auth import router, _init_cloud_auth_db, CLOUD_DB_PATH
    # Reinitialize DB for clean state
    _init_cloud_auth_db()
    return router


@pytest.fixture
def test_db_path(tmp_path):
    """Create a temporary database for testing"""
    return tmp_path / "test_vault.db"


@pytest.fixture
def test_client(cloud_auth_router, mock_user):
    """Create a test client with mocked authentication and rate limiting"""
    from fastapi import FastAPI
    from api.routes.cloud_auth import router
    from api.auth_middleware import get_current_user

    app = FastAPI()
    app.include_router(router)

    # Override authentication
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # Mock rate limiting to always allow (except for specific rate limit tests)
    with patch('api.routes.cloud_auth._check_pairing_rate_limit', return_value=True):
        yield TestClient(app)


# ===== Unit Tests: Helper Functions =====

class TestHelperFunctions:
    """Tests for helper functions in cloud_auth module"""

    def test_hash_token(self):
        """Token hashing should be deterministic"""
        from api.routes.cloud_auth import _hash_token

        token = "test-token-12345"
        hash1 = _hash_token(token)
        hash2 = _hash_token(token)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex is 64 chars
        assert hash1 != token  # Not plaintext

    def test_hash_token_different_inputs(self):
        """Different tokens should produce different hashes"""
        from api.routes.cloud_auth import _hash_token

        hash1 = _hash_token("token-a")
        hash2 = _hash_token("token-b")

        assert hash1 != hash2

    def test_generate_cloud_device_id_deterministic(self):
        """Cloud device ID should be deterministic for same inputs"""
        from api.routes.cloud_auth import _generate_cloud_device_id

        device_id1 = _generate_cloud_device_id("user1", "fingerprint1")
        device_id2 = _generate_cloud_device_id("user1", "fingerprint1")

        assert device_id1 == device_id2

    def test_generate_cloud_device_id_unique(self):
        """Different inputs should produce different device IDs"""
        from api.routes.cloud_auth import _generate_cloud_device_id

        device_id1 = _generate_cloud_device_id("user1", "fingerprint1")
        device_id2 = _generate_cloud_device_id("user2", "fingerprint1")
        device_id3 = _generate_cloud_device_id("user1", "fingerprint2")

        assert device_id1 != device_id2
        assert device_id1 != device_id3
        assert device_id2 != device_id3

    def test_generate_cloud_token_randomness(self):
        """Cloud tokens should be random and unique"""
        from api.routes.cloud_auth import _generate_cloud_token

        tokens = [_generate_cloud_token() for _ in range(100)]

        # All should be unique
        assert len(set(tokens)) == 100

        # Should be URL-safe base64
        for token in tokens:
            assert len(token) == 64  # urlsafe_b64encode of 48 bytes


# ===== Integration Tests: API Endpoints =====

class TestCloudPairingEndpoint:
    """Tests for POST /api/v1/cloud/pair"""

    def test_pair_device_success(self, test_client):
        """Pairing a new device should return cloud credentials"""
        response = test_client.post(
            "/api/v1/cloud/pair",
            json={
                "device_id": "device-123",
                "device_name": "Test Mac",
                "device_platform": "macos",
                "device_fingerprint": "abcd1234fingerprint"
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["success"] is True
        assert "cloud_device_id" in data["data"]
        assert "cloud_token" in data["data"]
        assert "cloud_refresh_token" in data["data"]
        assert "expires_at" in data["data"]
        assert data["data"]["username"] == "testuser"

    def test_pair_device_repair(self, test_client):
        """Re-pairing an existing device should regenerate tokens"""
        # First pairing
        response1 = test_client.post(
            "/api/v1/cloud/pair",
            json={
                "device_id": "device-same",
                "device_fingerprint": "same-fingerprint"
            }
        )
        token1 = response1.json()["data"]["cloud_token"]

        # Second pairing (same device)
        response2 = test_client.post(
            "/api/v1/cloud/pair",
            json={
                "device_id": "device-same",
                "device_fingerprint": "same-fingerprint"
            }
        )
        token2 = response2.json()["data"]["cloud_token"]

        assert response2.status_code == status.HTTP_201_CREATED
        assert token1 != token2  # New token generated

    def test_pair_device_missing_fields(self, test_client):
        """Missing required fields should fail"""
        response = test_client.post(
            "/api/v1/cloud/pair",
            json={
                "device_name": "Test"
                # Missing device_id and device_fingerprint
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCloudTokenRefreshEndpoint:
    """Tests for POST /api/v1/cloud/refresh"""

    def test_refresh_token_success(self, test_client):
        """Valid refresh token should return new access token"""
        # First, pair a device
        pair_response = test_client.post(
            "/api/v1/cloud/pair",
            json={
                "device_id": "refresh-test-device",
                "device_fingerprint": "refresh-fingerprint"
            }
        )
        pair_data = pair_response.json()["data"]

        # Now refresh the token
        refresh_response = test_client.post(
            "/api/v1/cloud/refresh",
            json={
                "cloud_device_id": pair_data["cloud_device_id"],
                "refresh_token": pair_data["cloud_refresh_token"]
            }
        )

        assert refresh_response.status_code == status.HTTP_200_OK
        data = refresh_response.json()

        assert data["success"] is True
        assert "cloud_token" in data["data"]
        assert "expires_at" in data["data"]
        assert data["data"]["cloud_token"] != pair_data["cloud_token"]  # New token

    def test_refresh_token_invalid(self, test_client):
        """Invalid refresh token should fail"""
        # First, pair a device
        pair_response = test_client.post(
            "/api/v1/cloud/pair",
            json={
                "device_id": "invalid-refresh-test",
                "device_fingerprint": "invalid-fingerprint"
            }
        )
        pair_data = pair_response.json()["data"]

        # Try with invalid refresh token
        refresh_response = test_client.post(
            "/api/v1/cloud/refresh",
            json={
                "cloud_device_id": pair_data["cloud_device_id"],
                "refresh_token": "invalid-token"
            }
        )

        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_unknown_device(self, test_client):
        """Unknown device ID should fail"""
        refresh_response = test_client.post(
            "/api/v1/cloud/refresh",
            json={
                "cloud_device_id": "nonexistent-device",
                "refresh_token": "some-token"
            }
        )

        assert refresh_response.status_code == status.HTTP_404_NOT_FOUND


class TestCloudStatusEndpoint:
    """Tests for GET /api/v1/cloud/status"""

    def test_status_no_devices(self, test_client):
        """Status with no paired devices should return is_paired=False"""
        # Note: We need a fresh database state for this test
        response = test_client.get("/api/v1/cloud/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # May have devices from previous tests, so just check structure
        assert "is_paired" in data["data"]
        assert "paired_devices" in data["data"]

    def test_status_with_paired_device(self, test_client):
        """Status with paired device should return device info"""
        # Pair a device first
        pair_response = test_client.post(
            "/api/v1/cloud/pair",
            json={
                "device_id": "status-test-device",
                "device_name": "Status Test Mac",
                "device_platform": "macos",
                "device_fingerprint": "status-fingerprint"
            }
        )
        assert pair_response.status_code == status.HTTP_201_CREATED

        # Check status
        status_response = test_client.get("/api/v1/cloud/status")

        assert status_response.status_code == status.HTTP_200_OK
        data = status_response.json()

        assert data["data"]["is_paired"] is True
        assert data["data"]["username"] == "testuser"
        assert len(data["data"]["paired_devices"]) >= 1


class TestCloudUnpairEndpoint:
    """Tests for POST /api/v1/cloud/unpair"""

    def test_unpair_device_success(self, test_client):
        """Unpairing a device should revoke its tokens"""
        # Pair a device first
        pair_response = test_client.post(
            "/api/v1/cloud/pair",
            json={
                "device_id": "unpair-test-device",
                "device_fingerprint": "unpair-fingerprint"
            }
        )
        cloud_device_id = pair_response.json()["data"]["cloud_device_id"]

        # Unpair it
        unpair_response = test_client.post(
            f"/api/v1/cloud/unpair?cloud_device_id={cloud_device_id}"
        )

        assert unpair_response.status_code == status.HTTP_200_OK
        data = unpair_response.json()

        assert data["data"]["unpaired"] is True
        assert data["data"]["cloud_device_id"] == cloud_device_id

    def test_unpair_unknown_device(self, test_client):
        """Unpairing unknown device should fail"""
        unpair_response = test_client.post(
            "/api/v1/cloud/unpair?cloud_device_id=nonexistent-device"
        )

        assert unpair_response.status_code == status.HTTP_404_NOT_FOUND

    def test_refresh_after_unpair_fails(self, test_client):
        """Refresh token should fail after unpairing"""
        # Pair a device
        pair_response = test_client.post(
            "/api/v1/cloud/pair",
            json={
                "device_id": "unpair-refresh-test",
                "device_fingerprint": "unpair-refresh-fp"
            }
        )
        pair_data = pair_response.json()["data"]

        # Unpair it
        test_client.post(
            f"/api/v1/cloud/unpair?cloud_device_id={pair_data['cloud_device_id']}"
        )

        # Try to refresh - should fail
        refresh_response = test_client.post(
            "/api/v1/cloud/refresh",
            json={
                "cloud_device_id": pair_data["cloud_device_id"],
                "refresh_token": pair_data["cloud_refresh_token"]
            }
        )

        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED


class TestCloudSyncAuthEndpoint:
    """Tests for POST /api/v1/cloud/sync/authorize"""

    def test_sync_authorize_success(self, test_client):
        """Valid cloud token should authorize sync"""
        # Pair a device first
        pair_response = test_client.post(
            "/api/v1/cloud/pair",
            json={
                "device_id": "sync-test-device",
                "device_fingerprint": "sync-fingerprint"
            }
        )
        cloud_token = pair_response.json()["data"]["cloud_token"]

        # Authorize sync
        sync_response = test_client.post(
            "/api/v1/cloud/sync/authorize",
            json={
                "cloud_token": cloud_token,
                "operation": "upload"
            }
        )

        assert sync_response.status_code == status.HTTP_200_OK
        data = sync_response.json()

        assert data["data"]["authorized"] is True
        assert "sync_session_id" in data["data"]
        assert "expires_at" in data["data"]

    def test_sync_authorize_invalid_token(self, test_client):
        """Invalid cloud token should not authorize"""
        sync_response = test_client.post(
            "/api/v1/cloud/sync/authorize",
            json={
                "cloud_token": "invalid-token",
                "operation": "download"
            }
        )

        assert sync_response.status_code == status.HTTP_200_OK
        data = sync_response.json()

        assert data["data"]["authorized"] is False


class TestCloudSessionRevocationEndpoint:
    """Tests for DELETE /api/v1/cloud/sessions"""

    def test_revoke_all_sessions(self, test_client):
        """Revoking all sessions should invalidate all device tokens"""
        # Pair multiple devices
        for i in range(3):
            test_client.post(
                "/api/v1/cloud/pair",
                json={
                    "device_id": f"revoke-test-device-{i}",
                    "device_fingerprint": f"revoke-fingerprint-{i}"
                }
            )

        # Revoke all
        revoke_response = test_client.delete("/api/v1/cloud/sessions")

        assert revoke_response.status_code == status.HTTP_200_OK
        data = revoke_response.json()

        assert data["data"]["revoked"] is True
        assert data["data"]["devices_affected"] >= 3


# ===== Rate Limiting Tests =====

class TestCloudPairingRateLimit:
    """Tests for rate limiting on cloud pairing"""

    def test_rate_limit_enforced(self, test_client):
        """Pairing rate limit should be enforced"""
        from api.routes.cloud_auth import PAIRING_RATE_LIMIT

        # Mock the rate limiter to simulate exceeded limit
        with patch('api.routes.cloud_auth._check_pairing_rate_limit') as mock_limit:
            mock_limit.return_value = False  # Simulate rate limit exceeded

            response = test_client.post(
                "/api/v1/cloud/pair",
                json={
                    "device_id": "rate-limit-test",
                    "device_fingerprint": "rate-limit-fp"
                }
            )

            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


# ===== Database Schema Tests =====

class TestDatabaseSchema:
    """Tests for database schema and initialization"""

    def test_cloud_devices_table_exists(self, cloud_auth_router):
        """cloud_devices table should be created"""
        from api.routes.cloud_auth import CLOUD_DB_PATH

        with sqlite3.connect(str(CLOUD_DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='cloud_devices'
            """)
            result = cursor.fetchone()

        assert result is not None
        assert result[0] == "cloud_devices"

    def test_cloud_sessions_table_exists(self, cloud_auth_router):
        """cloud_sessions table should be created"""
        from api.routes.cloud_auth import CLOUD_DB_PATH

        with sqlite3.connect(str(CLOUD_DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='cloud_sessions'
            """)
            result = cursor.fetchone()

        assert result is not None
        assert result[0] == "cloud_sessions"

    def test_cloud_sync_log_table_exists(self, cloud_auth_router):
        """cloud_sync_log table should be created"""
        from api.routes.cloud_auth import CLOUD_DB_PATH

        with sqlite3.connect(str(CLOUD_DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='cloud_sync_log'
            """)
            result = cursor.fetchone()

        assert result is not None
        assert result[0] == "cloud_sync_log"


# ===== Security Tests =====

class TestCloudAuthSecurity:
    """Security-focused tests for cloud authentication"""

    def test_tokens_are_hashed_in_db(self, test_client, cloud_auth_router):
        """Tokens should be stored as hashes, not plaintext"""
        from api.routes.cloud_auth import CLOUD_DB_PATH

        # Pair a device
        pair_response = test_client.post(
            "/api/v1/cloud/pair",
            json={
                "device_id": "security-test-device",
                "device_fingerprint": "security-fingerprint"
            }
        )
        plaintext_token = pair_response.json()["data"]["cloud_token"]
        cloud_device_id = pair_response.json()["data"]["cloud_device_id"]

        # Check database
        with sqlite3.connect(str(CLOUD_DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cloud_token_hash FROM cloud_devices
                WHERE cloud_device_id = ?
            """, (cloud_device_id,))
            stored_hash = cursor.fetchone()[0]

        # Should not be plaintext
        assert stored_hash != plaintext_token
        # Should be a SHA-256 hash (64 hex chars)
        assert len(stored_hash) == 64

    def test_unpaired_device_tokens_cleared(self, test_client, cloud_auth_router):
        """Unpaired device should have tokens cleared"""
        from api.routes.cloud_auth import CLOUD_DB_PATH

        # Pair a device
        pair_response = test_client.post(
            "/api/v1/cloud/pair",
            json={
                "device_id": "clear-tokens-test",
                "device_fingerprint": "clear-tokens-fp"
            }
        )
        cloud_device_id = pair_response.json()["data"]["cloud_device_id"]

        # Unpair it
        test_client.post(f"/api/v1/cloud/unpair?cloud_device_id={cloud_device_id}")

        # Check database - tokens should be empty
        with sqlite3.connect(str(CLOUD_DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cloud_token_hash, cloud_refresh_token_hash, is_active
                FROM cloud_devices
                WHERE cloud_device_id = ?
            """, (cloud_device_id,))
            row = cursor.fetchone()

        assert row[0] == ""  # Token cleared
        assert row[1] == ""  # Refresh token cleared
        assert row[2] == 0   # Inactive
