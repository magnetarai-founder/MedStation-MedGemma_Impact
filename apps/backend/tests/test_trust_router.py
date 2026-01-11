"""
Tests for Trust Router

Tests REST API endpoints for MagnetarTrust network operations,
including signature verification for node registration.
"""

import pytest
import base64
import sys
import hashlib
import hmac
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, UTC
from fastapi.testclient import TestClient
from fastapi import FastAPI
from types import ModuleType


# ===== Mock NaCl Module =====
# PyNaCl is an optional dependency. We inject a mock module for testing.

def _create_mock_nacl_modules():
    """Create mock nacl modules for testing trust router."""

    class MockSignedMessage:
        """Mock signed message (signature + message)."""
        def __init__(self, signature: bytes, message: bytes):
            self._signature = signature
            self._message = message

        @property
        def signature(self) -> bytes:
            return self._signature

        @property
        def message(self) -> bytes:
            return self._message

        def __bytes__(self) -> bytes:
            return self._signature + self._message

    class MockVerifyKey:
        """Mock Ed25519 verify key."""
        SIZE = 32

        def __init__(self, key_bytes: bytes = None):
            self._key = key_bytes or os.urandom(32)

        def verify(self, signed_message: bytes, signature: bytes = None) -> bytes:
            """Verify signature."""
            if isinstance(signed_message, MockSignedMessage):
                message = signed_message.message
                sig = signed_message.signature
            else:
                message = signed_message
                sig = signature

            expected = hmac.new(self._key, message, hashlib.sha512).digest()
            if sig is not None and not hmac.compare_digest(sig, expected):
                from nacl.exceptions import BadSignatureError
                raise BadSignatureError("Signature verification failed")
            return message

        def encode(self, encoder=None) -> bytes:
            return self._key

        def __bytes__(self) -> bytes:
            return self._key

    class MockSigningKey:
        """Mock Ed25519 signing key."""
        SIZE = 32
        SEED_SIZE = 32

        def __init__(self, seed: bytes = None):
            self._seed = seed or os.urandom(32)
            self._key = hashlib.sha256(self._seed + b"signing").digest()
            self._verify_key = MockVerifyKey(self._key)

        @property
        def verify_key(self) -> MockVerifyKey:
            return self._verify_key

        def sign(self, message: bytes) -> MockSignedMessage:
            """Sign message."""
            signature = hmac.new(self._key, message, hashlib.sha512).digest()
            return MockSignedMessage(signature, message)

        def encode(self, encoder=None) -> bytes:
            return self._seed

        def __bytes__(self) -> bytes:
            return self._seed

        @classmethod
        def generate(cls) -> "MockSigningKey":
            return cls(os.urandom(32))

    # Mock exceptions
    class MockBadSignatureError(Exception):
        """Mock bad signature error."""
        pass

    class MockCryptoError(Exception):
        """Mock crypto error."""
        pass

    class MockNaClValueError(Exception):
        """Mock nacl ValueError (distinct from builtin ValueError)."""
        pass

    # Create module structure
    nacl_module = ModuleType("nacl")
    nacl_module.__path__ = []  # Make it a package

    nacl_signing = ModuleType("nacl.signing")
    nacl_signing.SigningKey = MockSigningKey
    nacl_signing.VerifyKey = MockVerifyKey

    nacl_exceptions = ModuleType("nacl.exceptions")
    nacl_exceptions.BadSignatureError = MockBadSignatureError
    nacl_exceptions.CryptoError = MockCryptoError
    nacl_exceptions.ValueError = MockNaClValueError  # Use custom class to avoid catching binascii.Error

    nacl_module.signing = nacl_signing
    nacl_module.exceptions = nacl_exceptions

    return {
        "nacl": nacl_module,
        "nacl.signing": nacl_signing,
        "nacl.exceptions": nacl_exceptions,
    }


# Inject mock nacl before any imports
_mock_modules = _create_mock_nacl_modules()
for name, module in _mock_modules.items():
    sys.modules[name] = module

# Remove cached trust_router module to force reimport with mock nacl
if "api.trust_router" in sys.modules:
    del sys.modules["api.trust_router"]

import nacl.signing

from api.trust_router import router, public_router, verify_registration_signature
from api.trust_models import RegisterNodeRequest, NodeType, DisplayMode
from api.auth_middleware import get_current_user


# ===== Test Fixtures =====

@pytest.fixture
def ed25519_keypair():
    """Generate a real Ed25519 keypair for testing"""
    signing_key = nacl.signing.SigningKey.generate()
    verify_key = signing_key.verify_key
    return {
        "signing_key": signing_key,
        "verify_key": verify_key,
        "public_key_bytes": bytes(verify_key),
        "public_key_b64": base64.b64encode(bytes(verify_key)).decode('utf-8'),
    }


@pytest.fixture
def valid_registration(ed25519_keypair):
    """Create a validly signed registration request"""
    import secrets
    timestamp = datetime.now(UTC).isoformat()
    public_key_b64 = ed25519_keypair["public_key_b64"]
    public_name = "Test Node"
    node_type = NodeType.INDIVIDUAL
    nonce = secrets.token_hex(16)

    # Create canonical payload (with nonce prefix)
    canonical_payload = f"{nonce}|{timestamp}|{public_key_b64}|{public_name}|{node_type.value}"

    # Sign it
    signature = ed25519_keypair["signing_key"].sign(canonical_payload.encode('utf-8'))
    signature_b64 = base64.b64encode(signature.signature).decode('utf-8')

    return RegisterNodeRequest(
        public_key=public_key_b64,
        public_name=public_name,
        type=node_type,
        timestamp=timestamp,
        nonce=nonce,
        signature=signature_b64,
    )


@pytest.fixture
def mock_user(ed25519_keypair):
    """Mock authenticated user with public key"""
    return {
        "user_id": "test_user_123",
        "email": "test@example.com",
        "public_key": ed25519_keypair["public_key_b64"],
    }


@pytest.fixture
def mock_storage():
    """Mock trust storage"""
    storage = MagicMock()
    storage.get_node_by_public_key.return_value = None
    storage.create_node.side_effect = lambda node: node
    storage.get_node.return_value = None
    storage.list_nodes.return_value = []
    return storage


@pytest.fixture
def app(mock_user):
    """Create FastAPI app with trust router"""
    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.include_router(router)
    app.include_router(public_router)
    return app


@pytest.fixture
def client(app, mock_storage):
    """Create test client with mocked storage"""
    with patch("api.trust_router.get_trust_storage", return_value=mock_storage):
        yield TestClient(app)


# ===== Signature Verification Tests =====

class TestVerifyRegistrationSignature:
    """Tests for verify_registration_signature function"""

    def test_valid_signature_accepted(self, valid_registration):
        """Test that a valid signature is accepted"""
        result = verify_registration_signature(valid_registration)
        assert result is True

    def test_invalid_signature_rejected(self, ed25519_keypair):
        """Test that an invalid signature is rejected"""
        timestamp = datetime.now(UTC).isoformat()

        # Create request with wrong signature
        request = RegisterNodeRequest(
            public_key=ed25519_keypair["public_key_b64"],
            public_name="Test Node",
            type=NodeType.INDIVIDUAL,
            timestamp=timestamp,
            signature=base64.b64encode(b"invalid_signature_data_32bytes!!").decode('utf-8'),
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            verify_registration_signature(request)

        assert exc_info.value.status_code == 401
        assert "Invalid signature" in exc_info.value.detail

    def test_expired_timestamp_rejected(self, ed25519_keypair):
        """Test that expired timestamps are rejected (replay protection)"""
        # Create timestamp 10 minutes ago (beyond 5 minute tolerance)
        old_timestamp = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
        public_key_b64 = ed25519_keypair["public_key_b64"]

        canonical_payload = f"{old_timestamp}|{public_key_b64}|Test Node|individual"
        signature = ed25519_keypair["signing_key"].sign(canonical_payload.encode('utf-8'))

        request = RegisterNodeRequest(
            public_key=public_key_b64,
            public_name="Test Node",
            type=NodeType.INDIVIDUAL,
            timestamp=old_timestamp,
            signature=base64.b64encode(signature.signature).decode('utf-8'),
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            verify_registration_signature(request)

        assert exc_info.value.status_code == 400
        assert "timestamp expired" in exc_info.value.detail

    def test_future_timestamp_within_tolerance_accepted(self, ed25519_keypair):
        """Test that near-future timestamps are accepted (clock skew tolerance)"""
        import secrets
        # Create timestamp 2 minutes in the future (within 5 minute tolerance)
        future_timestamp = (datetime.now(UTC) + timedelta(minutes=2)).isoformat()
        public_key_b64 = ed25519_keypair["public_key_b64"]
        nonce = secrets.token_hex(16)

        canonical_payload = f"{nonce}|{future_timestamp}|{public_key_b64}|Test Node|individual"
        signature = ed25519_keypair["signing_key"].sign(canonical_payload.encode('utf-8'))

        request = RegisterNodeRequest(
            public_key=public_key_b64,
            public_name="Test Node",
            type=NodeType.INDIVIDUAL,
            timestamp=future_timestamp,
            nonce=nonce,
            signature=base64.b64encode(signature.signature).decode('utf-8'),
        )

        result = verify_registration_signature(request)
        assert result is True

    def test_future_timestamp_beyond_tolerance_rejected(self, ed25519_keypair):
        """Test that far-future timestamps are rejected"""
        # Create timestamp 10 minutes in the future
        future_timestamp = (datetime.now(UTC) + timedelta(minutes=10)).isoformat()
        public_key_b64 = ed25519_keypair["public_key_b64"]

        canonical_payload = f"{future_timestamp}|{public_key_b64}|Test Node|individual"
        signature = ed25519_keypair["signing_key"].sign(canonical_payload.encode('utf-8'))

        request = RegisterNodeRequest(
            public_key=public_key_b64,
            public_name="Test Node",
            type=NodeType.INDIVIDUAL,
            timestamp=future_timestamp,
            signature=base64.b64encode(signature.signature).decode('utf-8'),
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            verify_registration_signature(request)

        assert exc_info.value.status_code == 400
        assert "timestamp expired" in exc_info.value.detail

    def test_invalid_public_key_length_rejected(self):
        """Test that invalid public key length is rejected"""
        request = RegisterNodeRequest(
            public_key=base64.b64encode(b"too_short").decode('utf-8'),
            public_name="Test Node",
            type=NodeType.INDIVIDUAL,
            timestamp=datetime.now(UTC).isoformat(),
            signature=base64.b64encode(b"x" * 64).decode('utf-8'),
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            verify_registration_signature(request)

        assert exc_info.value.status_code == 400
        assert "32 bytes" in exc_info.value.detail

    def test_invalid_base64_rejected(self):
        """Test that invalid base64 encoding is rejected"""
        request = RegisterNodeRequest(
            public_key="not-valid-base64!!!",
            public_name="Test Node",
            type=NodeType.INDIVIDUAL,
            timestamp=datetime.now(UTC).isoformat(),
            signature="also-not-valid!!!",
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            verify_registration_signature(request)

        assert exc_info.value.status_code == 400
        assert "base64" in exc_info.value.detail.lower()

    def test_invalid_timestamp_format_rejected(self, ed25519_keypair):
        """Test that invalid timestamp format is rejected"""
        request = RegisterNodeRequest(
            public_key=ed25519_keypair["public_key_b64"],
            public_name="Test Node",
            type=NodeType.INDIVIDUAL,
            timestamp="not-a-valid-timestamp",
            signature=base64.b64encode(b"x" * 64).decode('utf-8'),
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            verify_registration_signature(request)

        assert exc_info.value.status_code == 400
        assert "timestamp format" in exc_info.value.detail.lower()

    def test_tampered_payload_rejected(self, ed25519_keypair):
        """Test that tampered payloads are rejected"""
        timestamp = datetime.now(UTC).isoformat()
        public_key_b64 = ed25519_keypair["public_key_b64"]

        # Sign with one name
        canonical_payload = f"{timestamp}|{public_key_b64}|Original Name|individual"
        signature = ed25519_keypair["signing_key"].sign(canonical_payload.encode('utf-8'))

        # Submit with different name (tampered)
        request = RegisterNodeRequest(
            public_key=public_key_b64,
            public_name="Tampered Name",  # Different from signed payload
            type=NodeType.INDIVIDUAL,
            timestamp=timestamp,
            signature=base64.b64encode(signature.signature).decode('utf-8'),
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            verify_registration_signature(request)

        assert exc_info.value.status_code == 401

    def test_wrong_key_rejected(self):
        """Test that signature from different key is rejected"""
        # Generate two different keypairs
        attacker_key = nacl.signing.SigningKey.generate()
        victim_key = nacl.signing.SigningKey.generate()

        timestamp = datetime.now(UTC).isoformat()
        victim_public_b64 = base64.b64encode(bytes(victim_key.verify_key)).decode('utf-8')

        # Attacker signs with their key but claims victim's public key
        canonical_payload = f"{timestamp}|{victim_public_b64}|Test|individual"
        attacker_signature = attacker_key.sign(canonical_payload.encode('utf-8'))

        request = RegisterNodeRequest(
            public_key=victim_public_b64,  # Victim's public key
            public_name="Test",
            type=NodeType.INDIVIDUAL,
            timestamp=timestamp,
            signature=base64.b64encode(attacker_signature.signature).decode('utf-8'),  # Attacker's signature
        )

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            verify_registration_signature(request)

        assert exc_info.value.status_code == 401
        assert "Invalid signature" in exc_info.value.detail


# ===== Canonical Payload Tests =====

class TestCanonicalPayload:
    """Tests for canonical payload generation"""

    def test_canonical_payload_format(self):
        """Test canonical payload follows expected format with nonce prefix"""
        request = RegisterNodeRequest(
            public_key="test_key_123",
            public_name="Test Node",
            type=NodeType.CHURCH,
            timestamp="2025-12-23T12:00:00Z",
            nonce="abc123nonce",
            signature="dummy_sig",
        )

        payload = request.get_canonical_payload()

        assert payload == "abc123nonce|2025-12-23T12:00:00Z|test_key_123|Test Node|church"

    def test_canonical_payload_deterministic(self):
        """Test canonical payload is deterministic"""
        request1 = RegisterNodeRequest(
            public_key="key",
            public_name="Name",
            type=NodeType.INDIVIDUAL,
            timestamp="2025-12-23T12:00:00Z",
            nonce="same_nonce",
            signature="sig",
        )
        request2 = RegisterNodeRequest(
            public_key="key",
            public_name="Name",
            type=NodeType.INDIVIDUAL,
            timestamp="2025-12-23T12:00:00Z",
            nonce="same_nonce",
            signature="sig",
        )

        assert request1.get_canonical_payload() == request2.get_canonical_payload()


# ===== Registration Endpoint Tests =====

class TestRegisterNodeEndpoint:
    """Tests for POST /nodes endpoint"""

    def test_register_with_valid_signature(self, client, valid_registration, mock_storage):
        """Test successful registration with valid signature"""
        response = client.post(
            "/api/v1/trust/nodes",
            json={
                "public_key": valid_registration.public_key,
                "public_name": valid_registration.public_name,
                "type": valid_registration.type.value,
                "timestamp": valid_registration.timestamp,
                "nonce": valid_registration.nonce,
                "signature": valid_registration.signature,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["public_name"] == valid_registration.public_name
        assert "id" in data

    def test_register_duplicate_key_rejected(self, client, valid_registration, mock_storage):
        """Test registration with duplicate public key is rejected"""
        # Simulate existing node
        mock_storage.get_node_by_public_key.return_value = {"id": "existing_node"}

        response = client.post(
            "/api/v1/trust/nodes",
            json={
                "public_key": valid_registration.public_key,
                "public_name": valid_registration.public_name,
                "type": valid_registration.type.value,
                "timestamp": valid_registration.timestamp,
                "nonce": valid_registration.nonce,
                "signature": valid_registration.signature,
            }
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_register_without_signature_rejected(self, client, ed25519_keypair):
        """Test registration without signature fields is rejected"""
        response = client.post(
            "/api/v1/trust/nodes",
            json={
                "public_key": ed25519_keypair["public_key_b64"],
                "public_name": "Test Node",
                "type": "individual",
                # Missing timestamp and signature
            }
        )

        assert response.status_code == 422  # Validation error


# ===== Public Endpoint Tests =====

class TestHealthEndpoint:
    """Tests for public health endpoint"""

    def test_health_returns_ok(self, mock_storage):
        """Test health endpoint returns OK status"""
        app = FastAPI()
        app.include_router(public_router)

        with patch("api.trust_router.get_trust_storage", return_value=mock_storage):
            client = TestClient(app)
            response = client.get("/api/v1/trust/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "MagnetarTrust"
        assert "total_nodes" in data
        assert "timestamp" in data


# ===== Nonce Replay Protection Tests (Task 5.1.3) =====

class TestNonceReplayProtection:
    """Tests for nonce-based replay protection"""

    @pytest.fixture
    def ed25519_keypair(self):
        """Generate a real Ed25519 keypair for testing"""
        signing_key = nacl.signing.SigningKey.generate()
        verify_key = signing_key.verify_key
        return {
            "signing_key": signing_key,
            "verify_key": verify_key,
            "public_key_bytes": bytes(verify_key),
            "public_key_b64": base64.b64encode(bytes(verify_key)).decode('utf-8'),
        }

    def create_signed_request(self, ed25519_keypair, nonce=""):
        """Helper to create a signed registration request with nonce"""
        import secrets
        timestamp = datetime.now(UTC).isoformat()
        public_key_b64 = ed25519_keypair["public_key_b64"]
        public_name = "Test Node"
        node_type = NodeType.INDIVIDUAL

        if not nonce:
            nonce = secrets.token_hex(16)

        # Create canonical payload with nonce
        canonical_payload = f"{nonce}|{timestamp}|{public_key_b64}|{public_name}|{node_type.value}"

        # Sign it
        signature = ed25519_keypair["signing_key"].sign(canonical_payload.encode('utf-8'))
        signature_b64 = base64.b64encode(signature.signature).decode('utf-8')

        return RegisterNodeRequest(
            public_key=public_key_b64,
            public_name=public_name,
            type=node_type,
            timestamp=timestamp,
            nonce=nonce,
            signature=signature_b64,
        )

    def test_request_with_nonce_accepted(self, ed25519_keypair):
        """Test that request with unique nonce is accepted"""
        # Clear nonce cache for clean test
        import api.trust_router as trust_module
        trust_module._used_nonces = set()

        request = self.create_signed_request(ed25519_keypair)
        result = verify_registration_signature(request)

        assert result is True

    def test_replay_with_same_nonce_rejected(self, ed25519_keypair):
        """Test that replaying same nonce is rejected"""
        import api.trust_router as trust_module
        trust_module._used_nonces = set()

        # First request succeeds
        fixed_nonce = "fixed_nonce_for_replay_test_12345"
        request1 = self.create_signed_request(ed25519_keypair, nonce=fixed_nonce)
        result1 = verify_registration_signature(request1)
        assert result1 is True

        # Second request with same nonce should fail
        request2 = self.create_signed_request(ed25519_keypair, nonce=fixed_nonce)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            verify_registration_signature(request2)

        assert exc_info.value.status_code == 400
        assert "Replay attack" in exc_info.value.detail

    def test_different_nonces_both_accepted(self, ed25519_keypair):
        """Test that different nonces are both accepted"""
        import api.trust_router as trust_module
        trust_module._used_nonces = set()

        request1 = self.create_signed_request(ed25519_keypair, nonce="nonce_one_abc123")
        request2 = self.create_signed_request(ed25519_keypair, nonce="nonce_two_xyz789")

        result1 = verify_registration_signature(request1)
        result2 = verify_registration_signature(request2)

        assert result1 is True
        assert result2 is True

    def test_empty_nonce_allowed_for_backwards_compat(self, ed25519_keypair):
        """Test that empty nonce is allowed for backwards compatibility"""
        import api.trust_router as trust_module
        trust_module._used_nonces = set()

        # Create request without nonce (empty string)
        timestamp = datetime.now(UTC).isoformat()
        public_key_b64 = ed25519_keypair["public_key_b64"]
        canonical_payload = f"|{timestamp}|{public_key_b64}|Test Node|individual"
        signature = ed25519_keypair["signing_key"].sign(canonical_payload.encode('utf-8'))

        request = RegisterNodeRequest(
            public_key=public_key_b64,
            public_name="Test Node",
            type=NodeType.INDIVIDUAL,
            timestamp=timestamp,
            nonce="",  # Empty nonce
            signature=base64.b64encode(signature.signature).decode('utf-8'),
        )

        result = verify_registration_signature(request)
        assert result is True
