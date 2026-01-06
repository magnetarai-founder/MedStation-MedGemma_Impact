"""
Comprehensive tests for api/routes/vault_auth.py

Tests vault authentication routes including:
- WebAuthn/biometric authentication
- Dual-password (decoy) mode for plausible deniability
- Challenge management
- Key derivation and wrapping
- Rate limiting
- Session management

Coverage targets:
- Challenge management functions
- Database initialization
- Key derivation and wrapping
- Endpoint handlers
- Rate limiting behavior
- Migration from XOR to AES-KW
"""

import pytest
import time
import secrets
import hashlib
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi import HTTPException, status


# ========== Fixtures ==========

@pytest.fixture
def mock_paths(tmp_path):
    """Mock config paths"""
    mock = MagicMock()
    mock.data_dir = tmp_path
    return mock


@pytest.fixture
def mock_user():
    """Create a mock authenticated user"""
    user = MagicMock()
    user.user_id = "test_user_123"
    return user


@pytest.fixture
def mock_request():
    """Create mock FastAPI request"""
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {}
    return request


@pytest.fixture
def temp_db(tmp_path):
    """Create temp database path"""
    return tmp_path / "vault.db"


@pytest.fixture
def reset_module_state():
    """Reset module-level state between tests"""
    import api.routes.vault_auth as module
    # Save original state
    orig_challenges = module.webauthn_challenges.copy()
    orig_sessions = module.vault_sessions.copy()

    yield module

    # Restore state
    module.webauthn_challenges.clear()
    module.webauthn_challenges.update(orig_challenges)
    module.vault_sessions.clear()
    module.vault_sessions.update(orig_sessions)


# ========== Challenge Management Tests ==========

class TestChallengeManagement:
    """Tests for WebAuthn challenge functions"""

    def test_generate_challenge(self, reset_module_state):
        """Test challenge generation"""
        module = reset_module_state

        challenge = module._generate_challenge("user1", "vault1")

        assert isinstance(challenge, bytes)
        assert len(challenge) == 32
        assert ("user1", "vault1") in module.webauthn_challenges

    def test_generate_challenge_stores_with_timestamp(self, reset_module_state):
        """Test challenge is stored with creation timestamp"""
        module = reset_module_state

        before = time.time()
        module._generate_challenge("user1", "vault1")
        after = time.time()

        entry = module.webauthn_challenges[("user1", "vault1")]
        assert 'challenge' in entry
        assert 'created_at' in entry
        assert before <= entry['created_at'] <= after

    def test_get_challenge_valid(self, reset_module_state):
        """Test retrieving valid challenge"""
        module = reset_module_state

        original = module._generate_challenge("user1", "vault1")
        retrieved = module._get_challenge("user1", "vault1")

        assert retrieved == original

    def test_get_challenge_not_found(self, reset_module_state):
        """Test getting non-existent challenge"""
        module = reset_module_state

        result = module._get_challenge("nonexistent", "vault")

        assert result is None

    def test_get_challenge_expired(self, reset_module_state):
        """Test expired challenge is removed"""
        module = reset_module_state

        # Create expired challenge
        module.webauthn_challenges[("user1", "vault1")] = {
            'challenge': secrets.token_bytes(32),
            'created_at': time.time() - 400  # 6+ minutes ago
        }

        result = module._get_challenge("user1", "vault1")

        assert result is None
        assert ("user1", "vault1") not in module.webauthn_challenges

    def test_consume_challenge_removes_challenge(self, reset_module_state):
        """Test consume removes challenge after retrieval"""
        module = reset_module_state

        original = module._generate_challenge("user1", "vault1")
        consumed = module._consume_challenge("user1", "vault1")

        assert consumed == original
        assert ("user1", "vault1") not in module.webauthn_challenges

    def test_consume_challenge_not_found(self, reset_module_state):
        """Test consuming non-existent challenge"""
        module = reset_module_state

        result = module._consume_challenge("nonexistent", "vault")

        assert result is None

    def test_cleanup_expired_challenges(self, reset_module_state):
        """Test cleanup removes only expired challenges"""
        module = reset_module_state

        # Add valid challenge
        module._generate_challenge("valid_user", "valid_vault")

        # Add expired challenge
        module.webauthn_challenges[("expired_user", "expired_vault")] = {
            'challenge': secrets.token_bytes(32),
            'created_at': time.time() - 400
        }

        module._cleanup_expired_challenges()

        assert ("valid_user", "valid_vault") in module.webauthn_challenges
        assert ("expired_user", "expired_vault") not in module.webauthn_challenges


# ========== Key Derivation Tests ==========

class TestKeyDerivation:
    """Tests for key derivation functions"""

    def test_derive_kek_from_passphrase(self):
        """Test KEK derivation produces 32-byte key"""
        from api.routes.vault_auth import _derive_kek_from_passphrase

        salt = secrets.token_bytes(32)
        kek = _derive_kek_from_passphrase("my_passphrase", salt)

        assert isinstance(kek, bytes)
        assert len(kek) == 32

    def test_derive_kek_deterministic(self):
        """Test same passphrase+salt produces same KEK"""
        from api.routes.vault_auth import _derive_kek_from_passphrase

        salt = secrets.token_bytes(32)
        passphrase = "test_passphrase"

        kek1 = _derive_kek_from_passphrase(passphrase, salt)
        kek2 = _derive_kek_from_passphrase(passphrase, salt)

        assert kek1 == kek2

    def test_derive_kek_different_salts(self):
        """Test different salts produce different KEKs"""
        from api.routes.vault_auth import _derive_kek_from_passphrase

        passphrase = "test_passphrase"
        salt1 = secrets.token_bytes(32)
        salt2 = secrets.token_bytes(32)

        kek1 = _derive_kek_from_passphrase(passphrase, salt1)
        kek2 = _derive_kek_from_passphrase(passphrase, salt2)

        assert kek1 != kek2

    def test_derive_kek_different_passphrases(self):
        """Test different passphrases produce different KEKs"""
        from api.routes.vault_auth import _derive_kek_from_passphrase

        salt = secrets.token_bytes(32)

        kek1 = _derive_kek_from_passphrase("passphrase1", salt)
        kek2 = _derive_kek_from_passphrase("passphrase2", salt)

        assert kek1 != kek2


# ========== Key Wrapping Tests ==========

class TestKeyWrapping:
    """Tests for key wrapping/unwrapping functions"""

    def test_wrap_unwrap_xor_legacy(self):
        """Test XOR legacy wrap/unwrap roundtrip"""
        from api.routes.vault_auth import _wrap_kek, _unwrap_kek

        kek = secrets.token_bytes(32)
        wrap_key = secrets.token_bytes(32)

        wrapped = _wrap_kek(kek, wrap_key, method="xor_legacy")
        unwrapped = _unwrap_kek(wrapped, wrap_key, method="xor_legacy")

        assert unwrapped == kek

    def test_wrap_kek_xor_is_self_inverse(self):
        """Test XOR wrap is self-inverse"""
        from api.routes.vault_auth import _wrap_kek

        kek = secrets.token_bytes(32)
        wrap_key = secrets.token_bytes(32)

        wrapped = _wrap_kek(kek, wrap_key, method="xor_legacy")
        # XOR again should give back original
        double_wrapped = _wrap_kek(wrapped, wrap_key, method="xor_legacy")

        assert double_wrapped == kek

    def test_wrap_kek_aes_kw(self):
        """Test AES-KW wrapping calls crypto_wrap"""
        with patch('api.routes.vault_auth.crypto_wrap_key') as mock_wrap:
            mock_wrap.return_value = b'wrapped_data'

            from api.routes.vault_auth import _wrap_kek

            kek = secrets.token_bytes(32)
            key = secrets.token_bytes(32)

            result = _wrap_kek(kek, key, method="aes_kw")

            mock_wrap.assert_called_once()

    def test_unwrap_kek_aes_kw(self):
        """Test AES-KW unwrapping calls crypto_wrap"""
        with patch('api.routes.vault_auth.crypto_unwrap_key') as mock_unwrap:
            mock_unwrap.return_value = b'unwrapped_data'

            from api.routes.vault_auth import _unwrap_kek

            wrapped = secrets.token_bytes(40)  # AES-KW adds padding
            key = secrets.token_bytes(32)

            result = _unwrap_kek(wrapped, key, method="aes_kw")

            mock_unwrap.assert_called_once()


# ========== Rate Limiting Tests ==========

class TestRateLimiting:
    """Tests for rate limiting"""

    def test_check_rate_limit_allowed(self):
        """Test rate limit check when under limit"""
        with patch('api.routes.vault_auth.rate_limiter') as mock_limiter:
            mock_limiter.check_rate_limit.return_value = True

            from api.routes.vault_auth import _check_rate_limit

            result = _check_rate_limit("user1", "vault1", "127.0.0.1")

            assert result is True
            mock_limiter.check_rate_limit.assert_called_once()

    def test_check_rate_limit_blocked(self):
        """Test rate limit check when over limit"""
        with patch('api.routes.vault_auth.rate_limiter') as mock_limiter:
            mock_limiter.check_rate_limit.return_value = False

            from api.routes.vault_auth import _check_rate_limit

            result = _check_rate_limit("user1", "vault1", "127.0.0.1")

            assert result is False


# ========== Database Tests ==========

class TestDatabase:
    """Tests for database operations"""

    def test_record_unlock_attempt(self, tmp_path):
        """Test recording unlock attempt"""
        db_path = tmp_path / "vault.db"

        with patch('api.routes.vault_auth.VAULT_DB_PATH', db_path):
            # Initialize database first
            from api.routes.vault_auth import _init_vault_auth_db, _record_unlock_attempt
            _init_vault_auth_db()

            # Record attempt
            _record_unlock_attempt("user1", "vault1", True, "passphrase")

            # Verify
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM vault_unlock_attempts WHERE user_id = ?", ("user1",))
            rows = cursor.fetchall()
            conn.close()

            assert len(rows) == 1
            assert rows[0][1] == "user1"  # user_id
            assert rows[0][2] == "vault1"  # vault_id
            assert rows[0][4] == 1  # success
            assert rows[0][5] == "passphrase"  # method

    def test_init_vault_auth_db_creates_tables(self, tmp_path):
        """Test database initialization creates required tables"""
        db_path = tmp_path / "vault.db"

        with patch('api.routes.vault_auth.VAULT_DB_PATH', db_path):
            from api.routes.vault_auth import _init_vault_auth_db
            _init_vault_auth_db()

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Check tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            conn.close()

            assert 'vault_auth_metadata' in tables
            assert 'vault_unlock_attempts' in tables


# ========== Migration Tests ==========

class TestMigration:
    """Tests for XOR to AES-KW migration"""

    def test_migrate_xor_to_aes_kw_success(self, tmp_path):
        """Test successful migration from XOR to AES-KW"""
        db_path = tmp_path / "vault.db"

        with patch('api.routes.vault_auth.VAULT_DB_PATH', db_path):
            # Initialize and create test entry
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vault_auth_metadata (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    vault_id TEXT NOT NULL,
                    salt_real TEXT,
                    wrapped_kek_real TEXT,
                    wrap_method TEXT DEFAULT 'xor_legacy',
                    created_at TEXT,
                    updated_at TEXT,
                    UNIQUE(user_id, vault_id)
                )
            """)
            cursor.execute("""
                INSERT INTO vault_auth_metadata (id, user_id, vault_id, wrapped_kek_real, wrap_method, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("id1", "user1", "vault1", "aabbccdd" * 8, "xor_legacy", datetime.now().isoformat(), datetime.now().isoformat()))
            conn.commit()
            conn.close()

            # Mock crypto_wrap to avoid actual crypto operations
            with patch('api.routes.vault_auth.crypto_wrap_key') as mock_wrap:
                mock_wrap.return_value = b'\x00' * 40  # AES-KW output

                from api.routes.vault_auth import _migrate_xor_to_aes_kw

                kek = secrets.token_bytes(32)
                wrap_key_bytes = secrets.token_bytes(32)

                result = _migrate_xor_to_aes_kw("user1", "vault1", kek, wrap_key_bytes, "real")

                assert result is True

            # Verify migration
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT wrap_method FROM vault_auth_metadata WHERE user_id = ?", ("user1",))
            row = cursor.fetchone()
            conn.close()

            assert row[0] == "aes_kw"


# ========== Endpoint Tests ==========

class TestBiometricSetup:
    """Tests for biometric setup endpoint"""

    @pytest.mark.asyncio
    async def test_setup_biometric_success(self, mock_user, tmp_path):
        """Test successful biometric setup"""
        db_path = tmp_path / "vault.db"

        # Ensure parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Mock VAULT_DB_PATH and crypto_wrap_key
        with patch('api.routes.vault_auth.VAULT_DB_PATH', db_path), \
             patch('api.routes.vault_auth.crypto_wrap_key') as mock_wrap:

            mock_wrap.return_value = b'\x00' * 40

            # Initialize database
            from api.routes.vault_auth import _init_vault_auth_db, setup_biometric, BiometricSetupRequest
            _init_vault_auth_db()

            # Clear sessions
            import api.routes.vault_auth as module
            module.vault_sessions.clear()

            request = BiometricSetupRequest(
                vault_id="vault_123",
                passphrase="my_secure_passphrase",
                webauthn_credential_id="credential_id_base64",
                webauthn_public_key="public_key_base64"
            )

            result = await setup_biometric(request, mock_user)

            assert result.success is True
            assert result.data.success is True
            assert result.data.session_id is not None

    @pytest.mark.asyncio
    async def test_setup_biometric_update_existing(self, mock_user, tmp_path):
        """Test updating existing biometric setup"""
        db_path = tmp_path / "vault.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with patch('api.routes.vault_auth.VAULT_DB_PATH', db_path), \
             patch('api.routes.vault_auth.crypto_wrap_key') as mock_wrap:

            mock_wrap.return_value = b'\x00' * 40

            from api.routes.vault_auth import _init_vault_auth_db, setup_biometric, BiometricSetupRequest
            _init_vault_auth_db()

            import api.routes.vault_auth as module
            module.vault_sessions.clear()

            # First setup
            request = BiometricSetupRequest(
                vault_id="vault_123",
                passphrase="passphrase1",
                webauthn_credential_id="cred1",
                webauthn_public_key="key1"
            )
            await setup_biometric(request, mock_user)

            # Update
            request2 = BiometricSetupRequest(
                vault_id="vault_123",
                passphrase="passphrase2",
                webauthn_credential_id="cred2",
                webauthn_public_key="key2"
            )
            result = await setup_biometric(request2, mock_user)

            assert result.success is True


class TestBiometricChallenge:
    """Tests for biometric challenge endpoint"""

    @pytest.mark.asyncio
    async def test_get_biometric_challenge(self, mock_user, reset_module_state):
        """Test getting biometric challenge"""
        from api.routes.vault_auth import get_biometric_challenge

        result = await get_biometric_challenge("vault_123", mock_user)

        assert result.success is True
        assert result.data.challenge is not None
        assert result.data.timeout == 300000  # 5 minutes in ms


class TestBiometricUnlock:
    """Tests for biometric unlock endpoint"""

    @pytest.mark.asyncio
    async def test_unlock_biometric_rate_limited(self, mock_user, mock_request):
        """Test rate limiting blocks excessive attempts"""
        with patch('api.routes.vault_auth._check_rate_limit', return_value=False), \
             patch('api.routes.vault_auth._record_unlock_attempt'):

            from api.routes.vault_auth import unlock_biometric, BiometricUnlockRequest

            request = BiometricUnlockRequest(
                vault_id="vault_123",
                webauthn_assertion="assertion_data",
                signature="signature_data"
            )

            with pytest.raises(HTTPException) as exc:
                await unlock_biometric(request, mock_request, mock_user)

            assert exc.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.asyncio
    async def test_unlock_biometric_not_configured(self, mock_user, mock_request, tmp_path):
        """Test unlock fails if biometric not configured"""
        db_path = tmp_path / "vault.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with patch('api.routes.vault_auth.VAULT_DB_PATH', db_path), \
             patch('api.routes.vault_auth._check_rate_limit', return_value=True), \
             patch('api.routes.vault_auth._record_unlock_attempt'):

            from api.routes.vault_auth import _init_vault_auth_db, unlock_biometric, BiometricUnlockRequest
            _init_vault_auth_db()

            request = BiometricUnlockRequest(
                vault_id="nonexistent_vault",
                webauthn_assertion="assertion",
                signature="sig"
            )

            with pytest.raises(HTTPException) as exc:
                await unlock_biometric(request, mock_request, mock_user)

            assert exc.value.status_code == status.HTTP_404_NOT_FOUND


class TestDualPasswordSetup:
    """Tests for dual-password mode setup"""

    @pytest.mark.asyncio
    async def test_setup_dual_password_success(self, mock_user, tmp_path):
        """Test successful dual-password setup"""
        db_path = tmp_path / "vault.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with patch('api.routes.vault_auth.VAULT_DB_PATH', db_path), \
             patch('api.routes.vault_auth.crypto_wrap_key') as mock_wrap:

            mock_wrap.return_value = b'\x00' * 40

            from api.routes.vault_auth import _init_vault_auth_db, setup_dual_password, DualPasswordSetupRequest
            _init_vault_auth_db()

            import api.routes.vault_auth as module
            module.vault_sessions.clear()

            request = DualPasswordSetupRequest(
                vault_id="vault_123",
                password_sensitive="sensitive_password",
                password_unsensitive="decoy_password"
            )

            result = await setup_dual_password(request, mock_user)

            assert result.success is True
            assert result.data.success is True

    @pytest.mark.asyncio
    async def test_setup_dual_password_same_passwords_rejected(self, mock_user):
        """Test setup fails if both passwords are the same"""
        from api.routes.vault_auth import setup_dual_password, DualPasswordSetupRequest

        request = DualPasswordSetupRequest(
            vault_id="vault_123",
            password_sensitive="same_password",
            password_unsensitive="same_password"
        )

        with pytest.raises(HTTPException) as exc:
            await setup_dual_password(request, mock_user)

        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


class TestPassphraseUnlock:
    """Tests for passphrase unlock endpoint"""

    @pytest.mark.asyncio
    async def test_unlock_passphrase_rate_limited(self, mock_user, mock_request):
        """Test rate limiting blocks excessive attempts"""
        with patch('api.routes.vault_auth._check_rate_limit', return_value=False), \
             patch('api.routes.vault_auth._record_unlock_attempt'):

            from api.routes.vault_auth import unlock_passphrase

            with pytest.raises(HTTPException) as exc:
                await unlock_passphrase("vault_123", "passphrase", mock_request, mock_user)

            assert exc.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.asyncio
    async def test_unlock_passphrase_not_configured(self, mock_user, mock_request, tmp_path):
        """Test unlock fails if vault not configured"""
        db_path = tmp_path / "vault.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with patch('api.routes.vault_auth.VAULT_DB_PATH', db_path), \
             patch('api.routes.vault_auth._check_rate_limit', return_value=True), \
             patch('api.routes.vault_auth._record_unlock_attempt'):

            from api.routes.vault_auth import _init_vault_auth_db, unlock_passphrase
            _init_vault_auth_db()

            with pytest.raises(HTTPException) as exc:
                await unlock_passphrase("nonexistent", "pass", mock_request, mock_user)

            assert exc.value.status_code == status.HTTP_404_NOT_FOUND


class TestSessionStatus:
    """Tests for session status endpoint"""

    @pytest.mark.asyncio
    async def test_session_status_unlocked(self, mock_user, reset_module_state):
        """Test session status when vault is unlocked"""
        module = reset_module_state

        # Create active session
        module.vault_sessions[(mock_user.user_id, "vault_123")] = {
            'kek': b'\x00' * 32,
            'vault_type': 'real',
            'unlocked_at': time.time(),
            'session_id': 'session_abc'
        }

        from api.routes.vault_auth import get_session_status

        result = await get_session_status("vault_123", mock_user)

        assert result.data['unlocked'] is True
        assert result.data['session_id'] == 'session_abc'

    @pytest.mark.asyncio
    async def test_session_status_locked(self, mock_user, reset_module_state):
        """Test session status when vault is locked"""
        module = reset_module_state
        module.vault_sessions.clear()

        from api.routes.vault_auth import get_session_status

        result = await get_session_status("vault_123", mock_user)

        assert result.data['unlocked'] is False
        assert result.data['session_id'] is None

    @pytest.mark.asyncio
    async def test_session_status_expired(self, mock_user, reset_module_state):
        """Test expired session is cleaned up"""
        module = reset_module_state

        # Create expired session (> 1 hour old)
        module.vault_sessions[(mock_user.user_id, "vault_123")] = {
            'kek': b'\x00' * 32,
            'vault_type': 'real',
            'unlocked_at': time.time() - 4000,  # > 1 hour
            'session_id': 'old_session'
        }

        from api.routes.vault_auth import get_session_status

        result = await get_session_status("vault_123", mock_user)

        assert result.data['unlocked'] is False
        assert (mock_user.user_id, "vault_123") not in module.vault_sessions


class TestLockVault:
    """Tests for vault locking endpoint"""

    @pytest.mark.asyncio
    async def test_lock_vault_success(self, mock_user, reset_module_state):
        """Test successful vault locking"""
        module = reset_module_state

        # Create active session
        module.vault_sessions[(mock_user.user_id, "vault_123")] = {
            'kek': b'\x00' * 32,
            'vault_type': 'real',
            'unlocked_at': time.time(),
            'session_id': 'session_xyz'
        }

        from api.routes.vault_auth import lock_vault

        result = await lock_vault("vault_123", mock_user)

        assert result.data['success'] is True
        assert (mock_user.user_id, "vault_123") not in module.vault_sessions

    @pytest.mark.asyncio
    async def test_lock_vault_not_unlocked(self, mock_user, reset_module_state):
        """Test locking already locked vault succeeds"""
        module = reset_module_state
        module.vault_sessions.clear()

        from api.routes.vault_auth import lock_vault

        result = await lock_vault("vault_123", mock_user)

        assert result.data['success'] is True


# ========== Request/Response Model Tests ==========

class TestModels:
    """Tests for Pydantic models"""

    def test_biometric_setup_request_validation(self):
        """Test BiometricSetupRequest validation"""
        from api.routes.vault_auth import BiometricSetupRequest

        # Valid request
        req = BiometricSetupRequest(
            vault_id="vault_123",
            passphrase="longpassphrase",
            webauthn_credential_id="cred_id",
            webauthn_public_key="pub_key"
        )
        assert req.vault_id == "vault_123"

    def test_biometric_setup_request_short_passphrase(self):
        """Test passphrase minimum length"""
        from api.routes.vault_auth import BiometricSetupRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BiometricSetupRequest(
                vault_id="vault_123",
                passphrase="short",  # < 8 chars
                webauthn_credential_id="cred_id",
                webauthn_public_key="pub_key"
            )

    def test_dual_password_request_validation(self):
        """Test DualPasswordSetupRequest validation"""
        from api.routes.vault_auth import DualPasswordSetupRequest

        req = DualPasswordSetupRequest(
            vault_id="vault_123",
            password_sensitive="longpassword1",
            password_unsensitive="longpassword2"
        )
        assert req.vault_id == "vault_123"

    def test_unlock_response_model(self):
        """Test UnlockResponse model"""
        from api.routes.vault_auth import UnlockResponse

        response = UnlockResponse(
            success=True,
            session_id="session_123",
            message="Unlocked"
        )

        assert response.success is True
        assert response.vault_type is None  # Maintains plausible deniability


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_challenge_ttl_constant(self):
        """Test challenge TTL is configured correctly"""
        from api.routes.vault_auth import CHALLENGE_TTL_SECONDS

        assert CHALLENGE_TTL_SECONDS == 300  # 5 minutes

    def test_pbkdf2_iterations_owasp_compliant(self):
        """Test PBKDF2 iterations meet OWASP 2023 recommendations"""
        from api.routes.vault_auth import PBKDF2_ITERATIONS

        # OWASP 2023 recommends 600,000 for SHA-256
        assert PBKDF2_ITERATIONS >= 600_000

    def test_rate_limit_constants(self):
        """Test rate limit configuration"""
        from api.routes.vault_auth import UNLOCK_RATE_LIMIT, UNLOCK_WINDOW_SECONDS

        assert UNLOCK_RATE_LIMIT == 5
        assert UNLOCK_WINDOW_SECONDS == 300  # 5 minutes

    def test_router_prefix_and_tags(self):
        """Test router configuration"""
        from api.routes.vault_auth import router

        assert router.prefix == "/api/v1/vault"
        assert "vault-auth" in router.tags


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests"""

    @pytest.mark.asyncio
    async def test_full_biometric_setup_flow(self, mock_user, tmp_path):
        """Test complete biometric setup flow"""
        db_path = tmp_path / "vault.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with patch('api.routes.vault_auth.VAULT_DB_PATH', db_path), \
             patch('api.routes.vault_auth.crypto_wrap_key') as mock_wrap:

            mock_wrap.return_value = b'\x00' * 40

            from api.routes.vault_auth import (
                _init_vault_auth_db, setup_biometric, get_biometric_challenge,
                BiometricSetupRequest
            )
            import api.routes.vault_auth as module

            _init_vault_auth_db()
            module.vault_sessions.clear()
            module.webauthn_challenges.clear()

            # Step 1: Setup biometric
            setup_req = BiometricSetupRequest(
                vault_id="vault_123",
                passphrase="my_secure_passphrase",
                webauthn_credential_id="cred_base64",
                webauthn_public_key="pubkey_base64"
            )
            setup_result = await setup_biometric(setup_req, mock_user)

            assert setup_result.success is True

            # Step 2: Get challenge for future unlock
            challenge_result = await get_biometric_challenge("vault_123", mock_user)

            assert challenge_result.success is True
            assert challenge_result.data.challenge is not None

    @pytest.mark.asyncio
    async def test_session_lifecycle(self, mock_user, reset_module_state):
        """Test complete session lifecycle"""
        module = reset_module_state
        module.vault_sessions.clear()

        from api.routes.vault_auth import get_session_status, lock_vault

        # Initially locked
        status1 = await get_session_status("vault_123", mock_user)
        assert status1.data['unlocked'] is False

        # Simulate unlock
        module.vault_sessions[(mock_user.user_id, "vault_123")] = {
            'kek': b'\x00' * 32,
            'vault_type': 'real',
            'unlocked_at': time.time(),
            'session_id': 'session_abc'
        }

        # Now unlocked
        status2 = await get_session_status("vault_123", mock_user)
        assert status2.data['unlocked'] is True

        # Lock
        await lock_vault("vault_123", mock_user)

        # Back to locked
        status3 = await get_session_status("vault_123", mock_user)
        assert status3.data['unlocked'] is False
