"""
Comprehensive tests for api/routes/vault/sharing.py

Tests vault file sharing, ACL, invitations, and user management endpoints.

Coverage targets:
- Share link creation with password/expiry/one-time
- Share link access (public endpoint) with rate limiting
- User registration and login
- ACL permission grant/check/revoke
- Sharing invitations lifecycle
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, UTC
import sqlite3
import tempfile
import os
import base64

# Import router and app
from api.routes.vault.sharing import router


# ========== Fixtures ==========

@pytest.fixture
def mock_current_user():
    """Mock authenticated user"""
    return {"user_id": "user_123", "username": "testuser"}


@pytest.fixture
def mock_vault_service():
    """Mock vault service"""
    service = MagicMock()
    service.db_path = ":memory:"
    return service


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter that always allows requests"""
    limiter = MagicMock()
    limiter.check_rate_limit.return_value = True
    return limiter


@pytest.fixture
def mock_request():
    """Mock FastAPI request"""
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    return request


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database with schema"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create vault_users table
    cursor.execute("""
        CREATE TABLE vault_users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)

    # Create vault_file_acl table
    cursor.execute("""
        CREATE TABLE vault_file_acl (
            id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            permission TEXT NOT NULL,
            granted_by TEXT NOT NULL,
            granted_at TEXT NOT NULL,
            expires_at TEXT,
            UNIQUE(file_id, user_id, permission)
        )
    """)

    # Create vault_share_invitations table
    cursor.execute("""
        CREATE TABLE vault_share_invitations (
            id TEXT PRIMARY KEY,
            resource_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            from_user_id TEXT NOT NULL,
            to_user_email TEXT NOT NULL,
            permission TEXT NOT NULL,
            invitation_token TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            expires_at TEXT,
            accepted_at TEXT
        )
    """)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


# ========== Share Link Creation Tests ==========

class TestCreateShareLink:
    """Tests for create share link endpoint"""

    @pytest.mark.asyncio
    async def test_create_share_link_success(self, mock_request, mock_current_user):
        """Test successful share link creation"""
        from api.routes.vault.sharing import create_share_link_endpoint

        mock_service = MagicMock()
        mock_service.create_share_link.return_value = {
            "id": "share_123",
            "token": "abc123token",
            "expires_at": "2025-01-02T00:00:00Z"
        }

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service), \
             patch('api.routes.vault.sharing.rate_limiter') as mock_limiter, \
             patch('api.routes.vault.sharing.get_client_ip', return_value="127.0.0.1"), \
             patch('api.routes.vault.sharing.audit_logger'):
            mock_limiter.check_rate_limit.return_value = True

            result = await create_share_link_endpoint(
                request=mock_request,
                file_id="file_123",
                vault_type="real",
                password=None,
                expires_at=None,
                max_downloads=None,
                permissions="download",
                one_time=False,
                current_user=mock_current_user
            )

            assert result.data["id"] == "share_123"
            mock_service.create_share_link.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_share_link_one_time(self, mock_request, mock_current_user):
        """Test one-time share link sets max_downloads=1"""
        from api.routes.vault.sharing import create_share_link_endpoint

        mock_service = MagicMock()
        mock_service.create_share_link.return_value = {"id": "share_123"}

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service), \
             patch('api.routes.vault.sharing.rate_limiter') as mock_limiter, \
             patch('api.routes.vault.sharing.get_client_ip', return_value="127.0.0.1"), \
             patch('api.routes.vault.sharing.audit_logger'):
            mock_limiter.check_rate_limit.return_value = True

            await create_share_link_endpoint(
                request=mock_request,
                file_id="file_123",
                vault_type="real",
                password=None,
                expires_at=None,
                max_downloads=None,
                permissions="download",
                one_time=True,
                current_user=mock_current_user
            )

            # Verify max_downloads was set to 1
            call_args = mock_service.create_share_link.call_args
            assert call_args[0][5] == 1  # max_downloads parameter

    @pytest.mark.asyncio
    async def test_create_share_link_rate_limited(self, mock_request, mock_current_user):
        """Test rate limiting on share link creation"""
        from api.routes.vault.sharing import create_share_link_endpoint

        with patch('api.routes.vault.sharing.rate_limiter') as mock_limiter, \
             patch('api.routes.vault.sharing.get_client_ip', return_value="127.0.0.1"):
            mock_limiter.check_rate_limit.return_value = False

            with pytest.raises(HTTPException) as exc:
                await create_share_link_endpoint(
                    request=mock_request,
                    file_id="file_123",
                    vault_type="real",
                    password=None,
                    expires_at=None,
                    max_downloads=None,
                    permissions="download",
                    one_time=False,
                    current_user=mock_current_user
                )

            assert exc.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS


# ========== Get File Shares Tests ==========

class TestGetFileShares:
    """Tests for get file shares endpoint"""

    @pytest.mark.asyncio
    async def test_get_file_shares_success(self, mock_request, mock_current_user):
        """Test successful retrieval of file shares"""
        from api.routes.vault.sharing import get_file_shares_endpoint

        mock_service = MagicMock()
        mock_service.get_file_shares.return_value = [
            {"id": "share_1", "token": "token1"},
            {"id": "share_2", "token": "token2"}
        ]

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service), \
             patch('api.routes.vault.sharing.rate_limiter') as mock_limiter, \
             patch('api.routes.vault.sharing.get_client_ip', return_value="127.0.0.1"):
            mock_limiter.check_rate_limit.return_value = True

            result = await get_file_shares_endpoint(
                request=mock_request,
                file_id="file_123",
                vault_type="real",
                current_user=mock_current_user
            )

            assert len(result.data["shares"]) == 2
            assert "Retrieved 2 share links" in result.message

    @pytest.mark.asyncio
    async def test_get_file_shares_empty(self, mock_request, mock_current_user):
        """Test retrieval when no shares exist"""
        from api.routes.vault.sharing import get_file_shares_endpoint

        mock_service = MagicMock()
        mock_service.get_file_shares.return_value = []

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service), \
             patch('api.routes.vault.sharing.rate_limiter') as mock_limiter, \
             patch('api.routes.vault.sharing.get_client_ip', return_value="127.0.0.1"):
            mock_limiter.check_rate_limit.return_value = True

            result = await get_file_shares_endpoint(
                request=mock_request,
                file_id="file_123",
                vault_type="real",
                current_user=mock_current_user
            )

            assert len(result.data["shares"]) == 0


# ========== Revoke Share Link Tests ==========

class TestRevokeShareLink:
    """Tests for revoke share link endpoint"""

    @pytest.mark.asyncio
    async def test_revoke_share_link_success(self, mock_request, mock_current_user):
        """Test successful share link revocation"""
        from api.routes.vault.sharing import revoke_share_link_endpoint

        mock_service = MagicMock()
        mock_service.revoke_share_link.return_value = True

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service), \
             patch('api.routes.vault.sharing.rate_limiter') as mock_limiter, \
             patch('api.routes.vault.sharing.get_client_ip', return_value="127.0.0.1"), \
             patch('api.routes.vault.sharing.audit_logger'):
            mock_limiter.check_rate_limit.return_value = True

            result = await revoke_share_link_endpoint(
                request=mock_request,
                share_id="share_123",
                vault_type="real",
                current_user=mock_current_user
            )

            assert result.data["success"] is True

    @pytest.mark.asyncio
    async def test_revoke_share_link_not_found(self, mock_request, mock_current_user):
        """Test revocation of non-existent share link"""
        from api.routes.vault.sharing import revoke_share_link_endpoint

        mock_service = MagicMock()
        mock_service.revoke_share_link.return_value = False

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service), \
             patch('api.routes.vault.sharing.rate_limiter') as mock_limiter, \
             patch('api.routes.vault.sharing.get_client_ip', return_value="127.0.0.1"):
            mock_limiter.check_rate_limit.return_value = True

            with pytest.raises(HTTPException) as exc:
                await revoke_share_link_endpoint(
                    request=mock_request,
                    share_id="nonexistent",
                    vault_type="real",
                    current_user=mock_current_user
                )

            assert exc.value.status_code == status.HTTP_404_NOT_FOUND


# ========== Access Share Link Tests ==========

class TestAccessShareLink:
    """Tests for public share link access endpoint"""

    @pytest.mark.asyncio
    async def test_access_share_link_success(self, mock_request):
        """Test successful share link access"""
        from api.routes.vault.sharing import access_share_link_endpoint

        mock_service = MagicMock()
        mock_service.get_share_link.return_value = {
            "file_id": "file_123",
            "requires_password": False,
            "expires_at": "2025-12-31T00:00:00Z"
        }

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service), \
             patch('api.routes.vault.sharing.rate_limiter') as mock_limiter, \
             patch('api.routes.vault.sharing.get_client_ip', return_value="127.0.0.1"):
            mock_limiter.check_rate_limit.return_value = True

            result = await access_share_link_endpoint(
                request=mock_request,
                share_token="valid_token",
                password=None
            )

            assert result.data["file_id"] == "file_123"

    @pytest.mark.asyncio
    async def test_access_share_link_password_required(self, mock_request):
        """Test share link that requires password"""
        from api.routes.vault.sharing import access_share_link_endpoint

        mock_service = MagicMock()
        mock_service.get_share_link.return_value = {
            "file_id": "file_123",
            "requires_password": True
        }

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service), \
             patch('api.routes.vault.sharing.rate_limiter') as mock_limiter, \
             patch('api.routes.vault.sharing.get_client_ip', return_value="127.0.0.1"):
            mock_limiter.check_rate_limit.return_value = True

            with pytest.raises(HTTPException) as exc:
                await access_share_link_endpoint(
                    request=mock_request,
                    share_token="valid_token",
                    password=None
                )

            assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "password_required" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_access_share_link_wrong_password(self, mock_request):
        """Test share link with incorrect password"""
        from api.routes.vault.sharing import access_share_link_endpoint

        mock_service = MagicMock()
        mock_service.get_share_link.return_value = {
            "file_id": "file_123",
            "requires_password": True
        }
        mock_service.verify_share_password.return_value = False

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service), \
             patch('api.routes.vault.sharing.rate_limiter') as mock_limiter, \
             patch('api.routes.vault.sharing.get_client_ip', return_value="127.0.0.1"):
            mock_limiter.check_rate_limit.return_value = True

            with pytest.raises(HTTPException) as exc:
                await access_share_link_endpoint(
                    request=mock_request,
                    share_token="valid_token",
                    password="wrong_password"
                )

            assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "password_incorrect" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_access_share_link_expired(self, mock_request):
        """Test expired share link"""
        from api.routes.vault.sharing import access_share_link_endpoint

        mock_service = MagicMock()
        mock_service.get_share_link.side_effect = ValueError("Share link expired")

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service), \
             patch('api.routes.vault.sharing.rate_limiter') as mock_limiter, \
             patch('api.routes.vault.sharing.get_client_ip', return_value="127.0.0.1"):
            mock_limiter.check_rate_limit.return_value = True

            with pytest.raises(HTTPException) as exc:
                await access_share_link_endpoint(
                    request=mock_request,
                    share_token="expired_token",
                    password=None
                )

            assert exc.value.status_code == status.HTTP_410_GONE
            assert "expired" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_access_share_link_max_downloads(self, mock_request):
        """Test share link with max downloads reached"""
        from api.routes.vault.sharing import access_share_link_endpoint

        mock_service = MagicMock()
        mock_service.get_share_link.side_effect = ValueError("Max download limit reached")

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service), \
             patch('api.routes.vault.sharing.rate_limiter') as mock_limiter, \
             patch('api.routes.vault.sharing.get_client_ip', return_value="127.0.0.1"):
            mock_limiter.check_rate_limit.return_value = True

            with pytest.raises(HTTPException) as exc:
                await access_share_link_endpoint(
                    request=mock_request,
                    share_token="max_downloads_token",
                    password=None
                )

            assert exc.value.status_code == status.HTTP_410_GONE
            assert "max_downloads_reached" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_access_share_link_rate_limited_minute(self, mock_request):
        """Test per-minute rate limiting"""
        from api.routes.vault.sharing import access_share_link_endpoint

        with patch('api.routes.vault.sharing.rate_limiter') as mock_limiter, \
             patch('api.routes.vault.sharing.get_client_ip', return_value="127.0.0.1"):
            mock_limiter.check_rate_limit.return_value = False

            with pytest.raises(HTTPException) as exc:
                await access_share_link_endpoint(
                    request=mock_request,
                    share_token="token",
                    password=None
                )

            assert exc.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS


# ========== User Registration Tests ==========

class TestUserRegistration:
    """Tests for user registration endpoint"""

    @pytest.mark.asyncio
    async def test_register_user_success(self, temp_db):
        """Test successful user registration"""
        from api.routes.vault.sharing import register_user

        mock_service = MagicMock()
        mock_service.db_path = temp_db
        mock_service._get_encryption_key.return_value = (b"key" * 8, b"salt" * 8)

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            result = await register_user(
                username="newuser",
                email="newuser@example.com",
                password="password123"
            )

            assert "user_id" in result.data
            assert result.data["username"] == "newuser"
            assert result.data["email"] == "newuser@example.com"

    @pytest.mark.asyncio
    async def test_register_user_duplicate(self, temp_db):
        """Test registration with duplicate username"""
        from api.routes.vault.sharing import register_user

        mock_service = MagicMock()
        mock_service.db_path = temp_db
        mock_service._get_encryption_key.return_value = (b"key" * 8, b"salt" * 8)

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            # Register first user
            await register_user(
                username="duplicate",
                email="first@example.com",
                password="password123"
            )

            # Try to register duplicate
            with pytest.raises(HTTPException) as exc:
                await register_user(
                    username="duplicate",
                    email="second@example.com",
                    password="password123"
                )

            assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


# ========== User Login Tests ==========

class TestUserLogin:
    """Tests for user login endpoint"""

    @pytest.mark.asyncio
    async def test_login_user_success(self, temp_db):
        """Test successful user login"""
        from api.routes.vault.sharing import register_user, login_user

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        # Use deterministic key generation for testing
        def get_key(password, salt=None):
            if salt is None:
                salt = b"testsalt" * 2
            key = b"testkey!" * 4  # 32 bytes
            return (key, salt)

        mock_service._get_encryption_key.side_effect = get_key

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            # Register user
            await register_user(
                username="logintest",
                email="login@example.com",
                password="password123"
            )

            # Login
            result = await login_user(
                username="logintest",
                password="password123"
            )

            assert result.data["username"] == "logintest"
            assert "last_login" in result.data

    @pytest.mark.asyncio
    async def test_login_user_invalid_credentials(self, temp_db):
        """Test login with wrong password"""
        from api.routes.vault.sharing import register_user, login_user

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        call_count = [0]
        def get_key(password, salt=None):
            call_count[0] += 1
            if salt is None:
                salt = b"testsalt" * 2
            # Return different key on login attempt
            if call_count[0] > 1:
                key = b"wrongkey" * 4
            else:
                key = b"testkey!" * 4
            return (key, salt)

        mock_service._get_encryption_key.side_effect = get_key

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            # Register user
            await register_user(
                username="wrongpass",
                email="wrong@example.com",
                password="password123"
            )

            # Try login with wrong password
            with pytest.raises(HTTPException) as exc:
                await login_user(
                    username="wrongpass",
                    password="wrongpassword"
                )

            assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, temp_db):
        """Test login with non-existent user"""
        from api.routes.vault.sharing import login_user

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            with pytest.raises(HTTPException) as exc:
                await login_user(
                    username="nonexistent",
                    password="password123"
                )

            assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


# ========== ACL Grant Permission Tests ==========

class TestGrantPermission:
    """Tests for ACL grant permission endpoint"""

    @pytest.mark.asyncio
    async def test_grant_file_permission_success(self, temp_db):
        """Test successful permission grant"""
        from api.routes.vault.sharing import grant_file_permission

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            result = await grant_file_permission(
                file_id="file_123",
                user_id="user_456",
                permission="read",
                granted_by="user_123",
                expires_at=None
            )

            assert "acl_id" in result.data
            assert result.data["permission"] == "read"

    @pytest.mark.asyncio
    async def test_grant_file_permission_invalid_type(self, temp_db):
        """Test grant with invalid permission type"""
        from api.routes.vault.sharing import grant_file_permission

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            with pytest.raises(HTTPException) as exc:
                await grant_file_permission(
                    file_id="file_123",
                    user_id="user_456",
                    permission="invalid_permission",
                    granted_by="user_123",
                    expires_at=None
                )

            assert exc.value.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_grant_file_permission_all_types(self, temp_db):
        """Test grant with all valid permission types"""
        from api.routes.vault.sharing import grant_file_permission

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            for perm in ['read', 'write', 'delete', 'share']:
                result = await grant_file_permission(
                    file_id=f"file_{perm}",
                    user_id="user_456",
                    permission=perm,
                    granted_by="user_123",
                    expires_at=None
                )

                assert result.data["permission"] == perm


# ========== ACL Check Permission Tests ==========

class TestCheckPermission:
    """Tests for ACL check permission endpoint"""

    @pytest.mark.asyncio
    async def test_check_file_permission_granted(self, temp_db):
        """Test check returns true when permission granted"""
        from api.routes.vault.sharing import grant_file_permission, check_file_permission

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            # Grant permission
            await grant_file_permission(
                file_id="file_check",
                user_id="user_check",
                permission="read",
                granted_by="admin",
                expires_at=None
            )

            # Check permission
            result = await check_file_permission(
                file_id="file_check",
                user_id="user_check",
                permission="read"
            )

            assert result.data["has_permission"] is True

    @pytest.mark.asyncio
    async def test_check_file_permission_not_granted(self, temp_db):
        """Test check returns false when permission not granted"""
        from api.routes.vault.sharing import check_file_permission

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            result = await check_file_permission(
                file_id="file_no_perm",
                user_id="user_no_perm",
                permission="write"
            )

            assert result.data["has_permission"] is False


# ========== ACL Get File Permissions Tests ==========

class TestGetFilePermissions:
    """Tests for get file permissions endpoint"""

    @pytest.mark.asyncio
    async def test_get_file_permissions_success(self, temp_db):
        """Test get all permissions for a file"""
        from api.routes.vault.sharing import grant_file_permission, get_file_permissions

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        # First create a user in the database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vault_users (user_id, username, email, password_hash, salt, created_at, updated_at)
            VALUES ('user_perm', 'permuser', 'perm@example.com', 'hash', 'salt', '2025-01-01', '2025-01-01')
        """)
        conn.commit()
        conn.close()

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            # Grant permission
            await grant_file_permission(
                file_id="file_multi",
                user_id="user_perm",
                permission="read",
                granted_by="admin",
                expires_at=None
            )

            # Get permissions
            result = await get_file_permissions(file_id="file_multi")

            assert "permissions" in result.data
            assert len(result.data["permissions"]) == 1


# ========== ACL Revoke Permission Tests ==========

class TestRevokePermission:
    """Tests for revoke permission endpoint"""

    @pytest.mark.asyncio
    async def test_revoke_permission_success(self, temp_db):
        """Test successful permission revocation"""
        from api.routes.vault.sharing import grant_file_permission, revoke_permission

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            # Grant permission
            grant_result = await grant_file_permission(
                file_id="file_revoke",
                user_id="user_revoke",
                permission="read",
                granted_by="admin",
                expires_at=None
            )

            acl_id = grant_result.data["acl_id"]

            # Revoke permission
            result = await revoke_permission(acl_id=acl_id)

            assert result.data["success"] is True

    @pytest.mark.asyncio
    async def test_revoke_permission_not_found(self, temp_db):
        """Test revocation of non-existent permission"""
        from api.routes.vault.sharing import revoke_permission

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            with pytest.raises(HTTPException) as exc:
                await revoke_permission(acl_id="nonexistent_acl")

            assert exc.value.status_code == status.HTTP_404_NOT_FOUND


# ========== Sharing Invitation Tests ==========

class TestSharingInvitations:
    """Tests for sharing invitation endpoints"""

    @pytest.mark.asyncio
    async def test_create_invitation_success(self, temp_db):
        """Test successful invitation creation"""
        from api.routes.vault.sharing import create_sharing_invitation

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            result = await create_sharing_invitation(
                resource_type="file",
                resource_id="file_123",
                from_user_id="user_sender",
                to_user_email="recipient@example.com",
                permission="read",
                expires_in_days=7
            )

            assert "invitation_id" in result.data
            assert "invitation_token" in result.data
            assert "share_url" in result.data
            assert result.data["to_user_email"] == "recipient@example.com"

    @pytest.mark.asyncio
    async def test_create_invitation_invalid_resource_type(self, temp_db):
        """Test invitation with invalid resource type"""
        from api.routes.vault.sharing import create_sharing_invitation

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            with pytest.raises(HTTPException) as exc:
                await create_sharing_invitation(
                    resource_type="invalid",
                    resource_id="file_123",
                    from_user_id="user_sender",
                    to_user_email="recipient@example.com",
                    permission="read",
                    expires_in_days=7
                )

            assert exc.value.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_create_invitation_invalid_permission(self, temp_db):
        """Test invitation with invalid permission"""
        from api.routes.vault.sharing import create_sharing_invitation

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            with pytest.raises(HTTPException) as exc:
                await create_sharing_invitation(
                    resource_type="file",
                    resource_id="file_123",
                    from_user_id="user_sender",
                    to_user_email="recipient@example.com",
                    permission="invalid_perm",
                    expires_in_days=7
                )

            assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


# ========== Accept Invitation Tests ==========

class TestAcceptInvitation:
    """Tests for accept invitation endpoint"""

    @pytest.mark.asyncio
    async def test_accept_invitation_success(self, temp_db):
        """Test successful invitation acceptance"""
        from api.routes.vault.sharing import create_sharing_invitation, accept_sharing_invitation

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            # Create invitation
            create_result = await create_sharing_invitation(
                resource_type="file",
                resource_id="file_accept",
                from_user_id="sender",
                to_user_email="accepter@example.com",
                permission="read",
                expires_in_days=7
            )

            token = create_result.data["invitation_token"]

            # Accept invitation
            result = await accept_sharing_invitation(
                invitation_token=token,
                user_id="accepter_user"
            )

            assert result.data["success"] is True
            assert result.data["resource_type"] == "file"

    @pytest.mark.asyncio
    async def test_accept_invitation_not_found(self, temp_db):
        """Test accepting non-existent invitation"""
        from api.routes.vault.sharing import accept_sharing_invitation

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            with pytest.raises(HTTPException) as exc:
                await accept_sharing_invitation(
                    invitation_token="nonexistent_token",
                    user_id="user"
                )

            assert exc.value.status_code == status.HTTP_404_NOT_FOUND


# ========== Decline Invitation Tests ==========

class TestDeclineInvitation:
    """Tests for decline invitation endpoint"""

    @pytest.mark.asyncio
    async def test_decline_invitation_success(self, temp_db):
        """Test successful invitation decline"""
        from api.routes.vault.sharing import create_sharing_invitation, decline_sharing_invitation

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            # Create invitation
            create_result = await create_sharing_invitation(
                resource_type="file",
                resource_id="file_decline",
                from_user_id="sender",
                to_user_email="decliner@example.com",
                permission="read",
                expires_in_days=7
            )

            token = create_result.data["invitation_token"]

            # Decline invitation
            result = await decline_sharing_invitation(invitation_token=token)

            assert result.data["success"] is True

    @pytest.mark.asyncio
    async def test_decline_invitation_not_found(self, temp_db):
        """Test declining non-existent invitation"""
        from api.routes.vault.sharing import decline_sharing_invitation

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            with pytest.raises(HTTPException) as exc:
                await decline_sharing_invitation(invitation_token="nonexistent")

            assert exc.value.status_code == status.HTTP_404_NOT_FOUND


# ========== Get My Invitations Tests ==========

class TestGetMyInvitations:
    """Tests for get my invitations endpoint"""

    @pytest.mark.asyncio
    async def test_get_my_invitations_success(self, temp_db):
        """Test getting pending invitations"""
        from api.routes.vault.sharing import create_sharing_invitation, get_my_invitations

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        # Create sender user
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vault_users (user_id, username, email, password_hash, salt, created_at, updated_at)
            VALUES ('sender_user', 'sender', 'sender@example.com', 'hash', 'salt', '2025-01-01', '2025-01-01')
        """)
        conn.commit()
        conn.close()

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            # Create invitation
            await create_sharing_invitation(
                resource_type="file",
                resource_id="file_invite",
                from_user_id="sender_user",
                to_user_email="myinvites@example.com",
                permission="read",
                expires_in_days=7
            )

            # Get invitations
            result = await get_my_invitations(user_email="myinvites@example.com")

            assert "invitations" in result.data
            assert len(result.data["invitations"]) == 1

    @pytest.mark.asyncio
    async def test_get_my_invitations_empty(self, temp_db):
        """Test getting invitations when none exist"""
        from api.routes.vault.sharing import get_my_invitations

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            result = await get_my_invitations(user_email="noinvites@example.com")

            assert result.data["invitations"] == []


# ========== Router Configuration Tests ==========

class TestRouterConfig:
    """Tests for router configuration"""

    def test_router_has_correct_endpoints(self):
        """Test router has expected endpoints"""
        routes = {route.path for route in router.routes}

        expected_endpoints = [
            "/files/{file_id}/share",
            "/files/{file_id}/shares",
            "/shares/{share_id}",
            "/share/{share_token}",
            "/users/register",
            "/users/login",
            "/acl/grant-file-permission",
            "/acl/check-permission",
            "/acl/file-permissions/{file_id}",
            "/acl/revoke-permission/{acl_id}",
            "/sharing/create-invitation",
            "/sharing/accept/{invitation_token}",
            "/sharing/decline/{invitation_token}",
            "/sharing/my-invitations",
        ]

        for endpoint in expected_endpoints:
            assert endpoint in routes, f"Missing endpoint: {endpoint}"


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    @pytest.mark.asyncio
    async def test_unicode_in_invitation_email(self, temp_db):
        """Test invitation with unicode email"""
        from api.routes.vault.sharing import create_sharing_invitation

        mock_service = MagicMock()
        mock_service.db_path = temp_db

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service):
            result = await create_sharing_invitation(
                resource_type="file",
                resource_id="file_unicode",
                from_user_id="sender",
                to_user_email="用户@example.com",
                permission="read",
                expires_in_days=7
            )

            assert result.data["to_user_email"] == "用户@example.com"

    @pytest.mark.asyncio
    async def test_share_link_with_all_options(self, mock_request, mock_current_user):
        """Test share link with all options set"""
        from api.routes.vault.sharing import create_share_link_endpoint

        mock_service = MagicMock()
        mock_service.create_share_link.return_value = {"id": "share_full"}

        with patch('api.routes.vault.sharing.get_vault_service', return_value=mock_service), \
             patch('api.routes.vault.sharing.rate_limiter') as mock_limiter, \
             patch('api.routes.vault.sharing.get_client_ip', return_value="127.0.0.1"), \
             patch('api.routes.vault.sharing.audit_logger'):
            mock_limiter.check_rate_limit.return_value = True

            result = await create_share_link_endpoint(
                request=mock_request,
                file_id="file_full",
                vault_type="decoy",
                password="secret123",
                expires_at="2026-01-01T00:00:00Z",
                max_downloads=5,
                permissions="view",
                one_time=False,
                current_user=mock_current_user
            )

            assert result.data["id"] == "share_full"

