"""
Tests for MagnetarCloud OAuth 2.0 Service

Tests cover:
- OAuth client registration
- OAuth client listing
- Authorization endpoint (PKCE)
- Token endpoint (authorization_code, refresh_token)
- Token introspection
- Token revocation
- Air-gap mode blocking
"""

import pytest
import json
import hashlib
import base64
import secrets
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, UTC
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
    """Create a mock authenticated user dict"""
    return {
        "user_id": "test-user-oauth-123",
        "username": "oauthuser",
        "device_id": "test-device-oauth-456",
        "created_at": "2024-12-01T00:00:00"
    }


@pytest.fixture
def test_client(mock_user, tmp_path):
    """Create a test client with mocked authentication and temp database"""
    from fastapi import FastAPI
    from api.auth_middleware import get_current_user

    test_db_path = tmp_path / "test_oauth.db"

    with patch('api.routes.cloud_oauth.OAUTH_DB_PATH', test_db_path):
        import importlib
        import api.routes.cloud_oauth as oauth_module
        importlib.reload(oauth_module)

        app = FastAPI()
        app.include_router(oauth_module.router)

        # Create a mock user object that has both dict access and .id attribute
        class MockUser:
            def __init__(self, user_dict):
                self._dict = user_dict
                self.id = user_dict["user_id"]

            def __getitem__(self, key):
                return self._dict[key]

        app.dependency_overrides[get_current_user] = lambda: MockUser(mock_user)

        yield TestClient(app)


@pytest.fixture
def test_client_airgap(mock_user, tmp_path):
    """Create a test client with air-gap mode enabled"""
    from fastapi import FastAPI
    from api.auth_middleware import get_current_user

    test_db_path = tmp_path / "test_oauth_airgap.db"

    with patch('api.config.is_airgap_mode', return_value=True):
        with patch('api.routes.cloud_oauth.OAUTH_DB_PATH', test_db_path):
            import importlib
            import api.routes.cloud_oauth as oauth_module
            importlib.reload(oauth_module)

            app = FastAPI()
            app.include_router(oauth_module.router)

            class MockUser:
                def __init__(self, user_dict):
                    self._dict = user_dict
                    self.id = user_dict["user_id"]

                def __getitem__(self, key):
                    return self._dict[key]

            app.dependency_overrides[get_current_user] = lambda: MockUser(mock_user)

            yield TestClient(app)


# ===== Helper Functions =====

def generate_pkce():
    """Generate PKCE code_verifier and code_challenge"""
    code_verifier = secrets.token_urlsafe(32)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode()
    return code_verifier, code_challenge


# ===== Client Registration Tests =====

class TestClientRegistration:
    """Tests for OAuth client registration"""

    def test_register_public_client(self, test_client):
        """Should register a public OAuth client"""
        response = test_client.post(
            "/api/v1/cloud/oauth/clients",
            json={
                "client_name": "Test App",
                "redirect_uris": ["http://localhost:8080/callback"],
                "client_type": "public"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["client_id"].startswith("mc_")
        assert data["data"]["client_name"] == "Test App"
        assert data["data"]["client_type"] == "public"
        # Public clients don't get a secret
        assert data["data"]["client_secret"] is None

    def test_register_confidential_client(self, test_client):
        """Should register a confidential OAuth client with secret"""
        response = test_client.post(
            "/api/v1/cloud/oauth/clients",
            json={
                "client_name": "Server App",
                "redirect_uris": ["https://myserver.com/callback"],
                "client_type": "confidential"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["client_type"] == "confidential"
        # Confidential clients get a secret
        assert data["data"]["client_secret"] is not None

    def test_register_client_with_scopes(self, test_client):
        """Should accept allowed scopes"""
        response = test_client.post(
            "/api/v1/cloud/oauth/clients",
            json={
                "client_name": "Scoped App",
                "redirect_uris": ["http://localhost/callback"],
                "allowed_scopes": ["vault:read", "vault:write", "profile:read"]
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "vault:read" in data["data"]["allowed_scopes"]
        assert "profile:read" in data["data"]["allowed_scopes"]

    def test_register_client_invalid_redirect(self, test_client):
        """Should reject invalid redirect URIs"""
        response = test_client.post(
            "/api/v1/cloud/oauth/clients",
            json={
                "client_name": "Bad App",
                "redirect_uris": ["not-a-valid-uri"]
            }
        )

        assert response.status_code == 400

    def test_register_client_requires_name(self, test_client):
        """Should require client_name"""
        response = test_client.post(
            "/api/v1/cloud/oauth/clients",
            json={
                "redirect_uris": ["http://localhost/callback"]
            }
        )

        assert response.status_code == 422


# ===== Client Listing Tests =====

class TestClientListing:
    """Tests for OAuth client listing"""

    def test_list_clients(self, test_client):
        """Should list registered clients"""
        # Register a client first
        test_client.post(
            "/api/v1/cloud/oauth/clients",
            json={
                "client_name": "List Test App",
                "redirect_uris": ["http://localhost/callback"]
            }
        )

        response = test_client.get("/api/v1/cloud/oauth/clients")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    def test_list_clients_returns_valid_structure(self, test_client):
        """Should return clients with correct structure"""
        # Register a client
        test_client.post(
            "/api/v1/cloud/oauth/clients",
            json={
                "client_name": "Structure Test App",
                "redirect_uris": ["http://localhost/callback"],
                "allowed_scopes": ["vault:read"]
            }
        )

        response = test_client.get("/api/v1/cloud/oauth/clients")

        data = response.json()
        for client in data["data"]:
            assert "client_id" in client
            assert "client_name" in client
            assert "redirect_uris" in client
            assert "allowed_scopes" in client


# ===== Authorization Tests =====

class TestAuthorization:
    """Tests for OAuth authorization endpoint"""

    def test_authorize_requires_client(self, test_client):
        """Should require valid client_id"""
        _, code_challenge = generate_pkce()

        response = test_client.get(
            "/api/v1/cloud/oauth/authorize",
            params={
                "client_id": "nonexistent",
                "redirect_uri": "http://localhost/callback",
                "response_type": "code",
                "code_challenge": code_challenge
            },
            follow_redirects=False
        )

        assert response.status_code == 400

    def test_authorize_requires_pkce_for_public(self, test_client):
        """Should require PKCE for public clients"""
        # Register a public client
        create_resp = test_client.post(
            "/api/v1/cloud/oauth/clients",
            json={
                "client_name": "PKCE Test",
                "redirect_uris": ["http://localhost/callback"],
                "client_type": "public"
            }
        )
        client_id = create_resp.json()["data"]["client_id"]

        # Try to authorize without PKCE
        response = test_client.get(
            "/api/v1/cloud/oauth/authorize",
            params={
                "client_id": client_id,
                "redirect_uri": "http://localhost/callback",
                "response_type": "code"
            },
            follow_redirects=False
        )

        assert response.status_code == 400
        assert "PKCE" in response.json()["detail"]

    def test_authorize_success_with_pkce(self, test_client):
        """Should redirect with auth code when PKCE provided"""
        # Register client
        create_resp = test_client.post(
            "/api/v1/cloud/oauth/clients",
            json={
                "client_name": "Auth Test",
                "redirect_uris": ["http://localhost:8080/callback"],
                "client_type": "public"
            }
        )
        client_id = create_resp.json()["data"]["client_id"]

        _, code_challenge = generate_pkce()

        response = test_client.get(
            "/api/v1/cloud/oauth/authorize",
            params={
                "client_id": client_id,
                "redirect_uri": "http://localhost:8080/callback",
                "response_type": "code",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "state": "test-state-123"
            },
            follow_redirects=False
        )

        assert response.status_code == 302
        location = response.headers.get("location", "")
        assert "code=" in location
        assert "state=test-state-123" in location

    def test_authorize_invalid_redirect_uri(self, test_client):
        """Should reject unregistered redirect URI"""
        # Register client with specific redirect
        create_resp = test_client.post(
            "/api/v1/cloud/oauth/clients",
            json={
                "client_name": "Redirect Test",
                "redirect_uris": ["http://localhost/valid"],
                "client_type": "public"
            }
        )
        client_id = create_resp.json()["data"]["client_id"]

        _, code_challenge = generate_pkce()

        response = test_client.get(
            "/api/v1/cloud/oauth/authorize",
            params={
                "client_id": client_id,
                "redirect_uri": "http://localhost/invalid",
                "response_type": "code",
                "code_challenge": code_challenge
            },
            follow_redirects=False
        )

        assert response.status_code == 400


# ===== Token Endpoint Tests =====

class TestTokenEndpoint:
    """Tests for OAuth token endpoint"""

    def test_token_requires_grant_type(self, test_client):
        """Should reject requests without grant_type"""
        response = test_client.post(
            "/api/v1/cloud/oauth/token",
            data={
                "client_id": "test"
            }
        )

        assert response.status_code == 422

    def test_token_invalid_grant_type(self, test_client):
        """Should reject unsupported grant_type"""
        response = test_client.post(
            "/api/v1/cloud/oauth/token",
            data={
                "grant_type": "password",
                "client_id": "test"
            }
        )

        assert response.status_code == 400

    def test_authorization_code_grant_requires_code(self, test_client):
        """Should require code for authorization_code grant"""
        response = test_client.post(
            "/api/v1/cloud/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": "test",
                "redirect_uri": "http://localhost/callback"
            }
        )

        assert response.status_code == 400

    def test_refresh_token_grant_requires_token(self, test_client):
        """Should require refresh_token for refresh_token grant"""
        response = test_client.post(
            "/api/v1/cloud/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": "test"
            }
        )

        assert response.status_code == 400


# ===== Token Introspection Tests =====

class TestTokenIntrospection:
    """Tests for token introspection"""

    def test_introspect_invalid_token(self, test_client):
        """Should return active=false for invalid token"""
        response = test_client.post(
            "/api/v1/cloud/oauth/introspect",
            data={
                "token": "invalid-token",
                "client_id": "test-client"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["active"] is False


# ===== Token Revocation Tests =====

class TestTokenRevocation:
    """Tests for token revocation"""

    def test_revoke_returns_ok(self, test_client):
        """Should return ok status for revocation"""
        response = test_client.post(
            "/api/v1/cloud/oauth/revoke",
            data={
                "token": "any-token",
                "client_id": "test-client"
            }
        )

        # RFC 7009 says revocation always succeeds
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


# ===== Air-Gap Mode Tests =====

class TestAirGapMode:
    """Tests for air-gap mode blocking"""

    def test_register_blocked_in_airgap(self, test_client_airgap):
        """Client registration should be blocked in air-gap mode"""
        response = test_client_airgap.post(
            "/api/v1/cloud/oauth/clients",
            json={
                "client_name": "Test",
                "redirect_uris": ["http://localhost/callback"]
            }
        )
        assert response.status_code == 503

    def test_list_blocked_in_airgap(self, test_client_airgap):
        """Client listing should be blocked in air-gap mode"""
        response = test_client_airgap.get("/api/v1/cloud/oauth/clients")
        assert response.status_code == 503

    def test_token_blocked_in_airgap(self, test_client_airgap):
        """Token endpoint should be blocked in air-gap mode"""
        response = test_client_airgap.post(
            "/api/v1/cloud/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": "test",
                "code": "test-code",
                "redirect_uri": "http://localhost/callback"
            }
        )
        assert response.status_code == 503


# ===== Integration Tests =====

class TestOAuthIntegration:
    """Integration tests for OAuth flow"""

    def test_full_authorization_flow(self, test_client):
        """Test complete OAuth authorization code flow with PKCE"""
        # 1. Register client
        create_resp = test_client.post(
            "/api/v1/cloud/oauth/clients",
            json={
                "client_name": "Integration Test App",
                "redirect_uris": ["http://localhost:3000/callback"],
                "client_type": "public",
                "allowed_scopes": ["vault:read", "profile:read", "offline_access"]
            }
        )
        assert create_resp.status_code == 201
        client_id = create_resp.json()["data"]["client_id"]

        # 2. Generate PKCE
        code_verifier, code_challenge = generate_pkce()

        # 3. Get authorization code
        auth_resp = test_client.get(
            "/api/v1/cloud/oauth/authorize",
            params={
                "client_id": client_id,
                "redirect_uri": "http://localhost:3000/callback",
                "response_type": "code",
                "scope": "vault:read profile:read offline_access",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "state": "xyz123"
            },
            follow_redirects=False
        )
        assert auth_resp.status_code == 302
        location = auth_resp.headers["location"]
        assert "code=" in location

        # Extract auth code from redirect URL
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(location)
        query = parse_qs(parsed.query)
        auth_code = query["code"][0]

        # 4. Exchange code for tokens
        token_resp = test_client.post(
            "/api/v1/cloud/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": "http://localhost:3000/callback",
                "client_id": client_id,
                "code_verifier": code_verifier
            }
        )
        assert token_resp.status_code == 200
        tokens = token_resp.json()
        assert "access_token" in tokens
        assert tokens["token_type"] == "Bearer"

        # 5. Introspect access token
        intro_resp = test_client.post(
            "/api/v1/cloud/oauth/introspect",
            data={
                "token": tokens["access_token"],
                "client_id": client_id
            }
        )
        assert intro_resp.status_code == 200
        intro_data = intro_resp.json()
        assert intro_data["active"] is True
        assert intro_data["client_id"] == client_id

        # 6. Revoke token
        revoke_resp = test_client.post(
            "/api/v1/cloud/oauth/revoke",
            data={
                "token": tokens["access_token"],
                "client_id": client_id
            }
        )
        assert revoke_resp.status_code == 200

        # 7. Verify token is revoked
        verify_resp = test_client.post(
            "/api/v1/cloud/oauth/introspect",
            data={
                "token": tokens["access_token"],
                "client_id": client_id
            }
        )
        assert verify_resp.json()["active"] is False
