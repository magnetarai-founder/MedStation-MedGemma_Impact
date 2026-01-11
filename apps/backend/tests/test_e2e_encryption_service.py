"""
Comprehensive tests for e2e_encryption_service.py

Tests cover:
- Key generation (Curve25519 identity + Ed25519 signing)
- Key loading from Secure Enclave
- Fingerprint generation and formatting
- Safety number generation (Signal-style)
- Message encryption/decryption (NaCl SealedBox)
- Message signing and verification
- Multi-device identity export/import
- Error handling
- Singleton pattern

Coverage target: 100%
"""

import pytest
import hashlib
import hmac
import os
import sys
from unittest.mock import Mock, MagicMock, patch
from types import ModuleType


# ===== Mock NaCl Module =====
# PyNaCl is an optional dependency. We inject a mock module to test the encryption service.

def _create_mock_nacl_modules():
    """Create comprehensive mock nacl modules for testing."""

    # --- Mock encoding module ---
    class MockHexEncoder:
        """Hex encoder for key serialization."""
        @staticmethod
        def decode(data: bytes) -> bytes:
            if isinstance(data, str):
                return bytes.fromhex(data)
            return bytes.fromhex(data.decode())

        @staticmethod
        def encode(data: bytes) -> bytes:
            return data.hex().encode()

    class MockRawEncoder:
        """Raw encoder (passthrough)."""
        @staticmethod
        def decode(data: bytes) -> bytes:
            return data

        @staticmethod
        def encode(data: bytes) -> bytes:
            return data

    class MockBase64Encoder:
        """Base64 encoder."""
        import base64

        @staticmethod
        def decode(data: bytes) -> bytes:
            import base64
            if isinstance(data, str):
                data = data.encode()
            return base64.b64decode(data)

        @staticmethod
        def encode(data: bytes) -> bytes:
            import base64
            return base64.b64encode(data)

    # --- Mock public key cryptography ---
    class MockPublicKey:
        """Mock Curve25519 public key."""
        SIZE = 32

        def __init__(self, key_bytes: bytes = None):
            self._key = key_bytes or os.urandom(32)

        def encode(self, encoder=None) -> bytes:
            return self._key

        def __bytes__(self) -> bytes:
            return self._key

        def __eq__(self, other):
            if isinstance(other, MockPublicKey):
                return self._key == other._key
            return False

    class MockPrivateKey:
        """Mock Curve25519 private key."""
        SIZE = 32

        def __init__(self, key_bytes: bytes = None):
            self._key = key_bytes or os.urandom(32)
            # Derive public key deterministically from private key
            self._public_key = MockPublicKey(
                hashlib.sha256(self._key + b"public").digest()
            )

        @property
        def public_key(self) -> MockPublicKey:
            return self._public_key

        def encode(self, encoder=None) -> bytes:
            return self._key

        def __bytes__(self) -> bytes:
            return self._key

        @classmethod
        def generate(cls) -> "MockPrivateKey":
            return cls(os.urandom(32))

    # --- Mock SealedBox (anonymous encryption) ---
    class MockSealedBox:
        """Mock sealed box for anonymous encryption.

        In real NaCl, SealedBox uses asymmetric encryption with the recipient's
        public key. For our mock, we derive a symmetric key from the public key.
        """
        def __init__(self, key):
            if isinstance(key, MockPublicKey):
                # For encryption: use the public key bytes
                self._symmetric_key = key._key
                self._can_decrypt = False
            elif isinstance(key, MockPrivateKey):
                # For decryption: use the PUBLIC key bytes (derived from private)
                # This ensures encryption with PublicKey and decryption with PrivateKey
                # use the same symmetric key
                self._symmetric_key = key.public_key._key
                self._can_decrypt = True
            else:
                self._symmetric_key = bytes(key) if hasattr(key, '__bytes__') else key
                self._can_decrypt = True

        def encrypt(self, plaintext: bytes) -> bytes:
            """Encrypt using XOR with derived key (mock implementation)."""
            nonce = os.urandom(24)
            key_stream = hashlib.sha256(self._symmetric_key + nonce).digest()
            # Simple XOR encryption for testing
            ciphertext = bytes(p ^ key_stream[i % 32] for i, p in enumerate(plaintext))
            return nonce + ciphertext

        def decrypt(self, ciphertext: bytes) -> bytes:
            """Decrypt using XOR with derived key (mock implementation)."""
            if not self._can_decrypt:
                raise ValueError("Cannot decrypt with public key only")
            nonce = ciphertext[:24]
            encrypted = ciphertext[24:]
            key_stream = hashlib.sha256(self._symmetric_key + nonce).digest()
            return bytes(c ^ key_stream[i % 32] for i, c in enumerate(encrypted))

    # --- Mock Box (authenticated encryption) ---
    class MockBox:
        """Mock box for authenticated encryption."""
        def __init__(self, private_key: MockPrivateKey, public_key: MockPublicKey):
            self._shared_key = hashlib.sha256(
                private_key._key + public_key._key
            ).digest()

        def encrypt(self, plaintext: bytes, nonce: bytes = None) -> bytes:
            """Encrypt with authentication."""
            nonce = nonce or os.urandom(24)
            key_stream = hashlib.sha256(self._shared_key + nonce).digest()
            ciphertext = bytes(p ^ key_stream[i % 32] for i, p in enumerate(plaintext))
            return nonce + ciphertext

        def decrypt(self, ciphertext: bytes) -> bytes:
            """Decrypt with authentication."""
            nonce = ciphertext[:24]
            encrypted = ciphertext[24:]
            key_stream = hashlib.sha256(self._shared_key + nonce).digest()
            return bytes(c ^ key_stream[i % 32] for i, c in enumerate(encrypted))

    # --- Mock signing key (Ed25519) ---
    class MockVerifyKey:
        """Mock Ed25519 verify key."""
        SIZE = 32

        def __init__(self, key_bytes: bytes = None):
            self._key = key_bytes or os.urandom(32)

        def verify(self, message: bytes, signature: bytes = None) -> bytes:
            """Verify signature (mock - uses HMAC-SHA512 to match signing)."""
            expected = hmac.new(self._key, message, hashlib.sha512).digest()
            if signature is not None and not hmac.compare_digest(signature, expected):
                raise Exception("Signature verification failed")
            return message

        def encode(self, encoder=None) -> bytes:
            return self._key

        def __bytes__(self) -> bytes:
            return self._key

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
            """Sign message (mock using HMAC-SHA512 for 64-byte signature like Ed25519)."""
            signature = hmac.new(self._key, message, hashlib.sha512).digest()
            return MockSignedMessage(signature, message)

        def encode(self, encoder=None) -> bytes:
            return self._seed

        def __bytes__(self) -> bytes:
            return self._seed

        @classmethod
        def generate(cls) -> "MockSigningKey":
            return cls(os.urandom(32))

    # --- Mock hash module ---
    def mock_sha256(data: bytes, encoder=None) -> bytes:
        digest = hashlib.sha256(data).digest()
        if encoder:
            return encoder.encode(digest)
        return digest

    # --- Mock utils module ---
    def mock_random(size: int) -> bytes:
        return os.urandom(size)

    # Create module structure
    nacl_module = ModuleType("nacl")

    nacl_public = ModuleType("nacl.public")
    nacl_public.PublicKey = MockPublicKey
    nacl_public.PrivateKey = MockPrivateKey
    nacl_public.SealedBox = MockSealedBox
    nacl_public.Box = MockBox

    nacl_signing = ModuleType("nacl.signing")
    nacl_signing.SigningKey = MockSigningKey
    nacl_signing.VerifyKey = MockVerifyKey

    nacl_encoding = ModuleType("nacl.encoding")
    nacl_encoding.HexEncoder = MockHexEncoder
    nacl_encoding.RawEncoder = MockRawEncoder
    nacl_encoding.Base64Encoder = MockBase64Encoder

    nacl_utils = ModuleType("nacl.utils")
    nacl_utils.random = mock_random

    nacl_hash = ModuleType("nacl.hash")
    nacl_hash.sha256 = mock_sha256

    # Link modules
    nacl_module.public = nacl_public
    nacl_module.signing = nacl_signing
    nacl_module.encoding = nacl_encoding
    nacl_module.utils = nacl_utils
    nacl_module.hash = nacl_hash

    return {
        "nacl": nacl_module,
        "nacl.public": nacl_public,
        "nacl.signing": nacl_signing,
        "nacl.encoding": nacl_encoding,
        "nacl.utils": nacl_utils,
        "nacl.hash": nacl_hash,
    }


# Store original modules
_original_nacl_modules = {}

def _inject_mock_nacl():
    """Inject mock nacl modules into sys.modules."""
    global _original_nacl_modules
    mock_modules = _create_mock_nacl_modules()

    for name, module in mock_modules.items():
        if name in sys.modules:
            _original_nacl_modules[name] = sys.modules[name]
        sys.modules[name] = module


# Inject mock nacl before any imports that might use it
_inject_mock_nacl()

# Remove cached e2e encryption module to force reimport with mock nacl
if "api.e2e_encryption_service" in sys.modules:
    del sys.modules["api.e2e_encryption_service"]

# Now import nacl (will get the mock)
import nacl.public
import nacl.signing

from api.e2e_encryption_service import (
    E2EEncryptionService,
    get_e2e_service,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_secure_enclave():
    """Create mock Secure Enclave service"""
    mock = Mock()
    mock.stored_keys = {}

    def store_key(key_id, key_bytes, passphrase):
        mock.stored_keys[key_id] = key_bytes

    def retrieve_key(key_id, passphrase):
        return mock.stored_keys.get(key_id)

    mock.store_key_in_keychain = Mock(side_effect=store_key)
    mock.retrieve_key_from_keychain = Mock(side_effect=retrieve_key)

    return mock


@pytest.fixture
def e2e_service(mock_secure_enclave):
    """Create E2E encryption service with mock Secure Enclave"""
    return E2EEncryptionService(mock_secure_enclave)


@pytest.fixture
def e2e_service_with_keys(e2e_service):
    """Create E2E service with pre-generated keypairs"""
    e2e_service.generate_identity_keypair("test_device", "test_passphrase")
    return e2e_service


@pytest.fixture
def cleanup_global():
    """Reset global singleton after test"""
    import api.e2e_encryption_service as module
    original = module._e2e_service
    yield
    module._e2e_service = original


# =============================================================================
# Initialization Tests
# =============================================================================

class TestInitialization:
    """Tests for service initialization"""

    def test_init_sets_secure_enclave(self, mock_secure_enclave):
        """Test initialization with Secure Enclave service"""
        service = E2EEncryptionService(mock_secure_enclave)

        assert service.secure_enclave is mock_secure_enclave
        assert service._identity_keypair is None
        assert service._signing_keypair is None
        assert service._device_id is None


# =============================================================================
# Key Generation Tests
# =============================================================================

class TestKeyGeneration:
    """Tests for identity keypair generation"""

    def test_generate_identity_keypair_returns_tuple(self, e2e_service):
        """Test that generate returns (public_key, fingerprint)"""
        public_key, fingerprint = e2e_service.generate_identity_keypair(
            "device_1", "passphrase"
        )

        assert isinstance(public_key, bytes)
        assert isinstance(fingerprint, bytes)

    def test_generate_identity_keypair_key_sizes(self, e2e_service):
        """Test that keys are correct sizes"""
        public_key, fingerprint = e2e_service.generate_identity_keypair(
            "device_1", "passphrase"
        )

        assert len(public_key) == 32  # Curve25519 public key
        assert len(fingerprint) == 32  # SHA-256 hash

    def test_generate_identity_keypair_stores_in_enclave(self, e2e_service, mock_secure_enclave):
        """Test that keys are stored in Secure Enclave"""
        e2e_service.generate_identity_keypair("device_1", "my_passphrase")

        # Should have called store twice (identity + signing)
        assert mock_secure_enclave.store_key_in_keychain.call_count == 2

        # Verify key IDs
        calls = mock_secure_enclave.store_key_in_keychain.call_args_list
        key_ids = [call[0][0] for call in calls]
        assert "e2e_identity_device_1" in key_ids
        assert "e2e_signing_device_1" in key_ids

    def test_generate_identity_keypair_caches_keypairs(self, e2e_service):
        """Test that keypairs are cached in memory"""
        e2e_service.generate_identity_keypair("device_1", "passphrase")

        assert e2e_service._identity_keypair is not None
        assert e2e_service._signing_keypair is not None
        assert e2e_service._device_id == "device_1"

    def test_generate_identity_keypair_unique_keys(self, e2e_service):
        """Test that each generation produces unique keys"""
        pk1, fp1 = e2e_service.generate_identity_keypair("device_1", "pass1")

        # Create new service for second generation
        service2 = E2EEncryptionService(Mock())
        pk2, fp2 = service2.generate_identity_keypair("device_2", "pass2")

        assert pk1 != pk2
        assert fp1 != fp2

    def test_generate_identity_keypair_fingerprint_is_sha256(self, e2e_service):
        """Test fingerprint is SHA-256 of public key"""
        public_key, fingerprint = e2e_service.generate_identity_keypair(
            "device_1", "passphrase"
        )

        expected = hashlib.sha256(public_key).digest()
        assert fingerprint == expected


# =============================================================================
# Key Loading Tests
# =============================================================================

class TestKeyLoading:
    """Tests for loading keypairs from Secure Enclave"""

    def test_load_identity_keypair_returns_tuple(self, e2e_service_with_keys, mock_secure_enclave):
        """Test loading existing keypair"""
        # Create new service to load existing keys
        service2 = E2EEncryptionService(mock_secure_enclave)
        public_key, fingerprint = service2.load_identity_keypair(
            "test_device", "test_passphrase"
        )

        assert isinstance(public_key, bytes)
        assert isinstance(fingerprint, bytes)
        assert len(public_key) == 32
        assert len(fingerprint) == 32

    def test_load_identity_keypair_retrieves_from_enclave(self, e2e_service_with_keys, mock_secure_enclave):
        """Test that keys are retrieved from Secure Enclave"""
        service2 = E2EEncryptionService(mock_secure_enclave)
        service2.load_identity_keypair("test_device", "test_passphrase")

        # Should have called retrieve twice
        assert mock_secure_enclave.retrieve_key_from_keychain.call_count == 2

    def test_load_identity_keypair_caches_keypairs(self, e2e_service_with_keys, mock_secure_enclave):
        """Test that loaded keypairs are cached"""
        service2 = E2EEncryptionService(mock_secure_enclave)
        service2.load_identity_keypair("test_device", "test_passphrase")

        assert service2._identity_keypair is not None
        assert service2._signing_keypair is not None
        assert service2._device_id == "test_device"

    def test_load_identity_keypair_not_found_raises(self, e2e_service):
        """Test error when keypair not found"""
        with pytest.raises(ValueError) as exc_info:
            e2e_service.load_identity_keypair("nonexistent_device", "passphrase")

        assert "not found" in str(exc_info.value)

    def test_load_identity_keypair_same_public_key(self, e2e_service_with_keys, mock_secure_enclave):
        """Test that loaded keypair has same public key"""
        # Get original public key
        original_pk = bytes(e2e_service_with_keys._identity_keypair.public_key)

        # Load in new service
        service2 = E2EEncryptionService(mock_secure_enclave)
        loaded_pk, _ = service2.load_identity_keypair("test_device", "test_passphrase")

        assert loaded_pk == original_pk


# =============================================================================
# Fingerprint Tests
# =============================================================================

class TestFingerprint:
    """Tests for fingerprint generation and formatting"""

    def test_generate_fingerprint_sha256(self, e2e_service):
        """Test fingerprint is SHA-256 hash"""
        public_key = b"test_public_key_32_bytes_here!!"
        fingerprint = e2e_service.generate_fingerprint(public_key)

        expected = hashlib.sha256(public_key).digest()
        assert fingerprint == expected

    def test_generate_fingerprint_length(self, e2e_service):
        """Test fingerprint is 32 bytes"""
        public_key = b"test_public_key_32_bytes_here!!"
        fingerprint = e2e_service.generate_fingerprint(public_key)

        assert len(fingerprint) == 32

    def test_generate_fingerprint_deterministic(self, e2e_service):
        """Test fingerprint is deterministic"""
        public_key = b"same_key_data_32_bytes_long_xxx"

        fp1 = e2e_service.generate_fingerprint(public_key)
        fp2 = e2e_service.generate_fingerprint(public_key)

        assert fp1 == fp2

    def test_format_fingerprint_colon_separated(self, e2e_service):
        """Test formatting as colon-separated hex"""
        fingerprint = bytes([0xAB, 0xCD, 0xEF, 0x12])
        formatted = e2e_service.format_fingerprint(fingerprint)

        assert formatted == "AB:CD:EF:12"

    def test_format_fingerprint_uppercase(self, e2e_service):
        """Test formatting uses uppercase hex"""
        fingerprint = bytes([0xab, 0xcd])
        formatted = e2e_service.format_fingerprint(fingerprint)

        assert formatted == "AB:CD"

    def test_format_fingerprint_full_length(self, e2e_service):
        """Test formatting 32-byte fingerprint"""
        fingerprint = bytes(range(32))
        formatted = e2e_service.format_fingerprint(fingerprint)

        # Should have 32 pairs with 31 colons
        parts = formatted.split(":")
        assert len(parts) == 32


# =============================================================================
# Safety Number Tests
# =============================================================================

class TestSafetyNumber:
    """Tests for Signal-style safety number generation"""

    def test_generate_safety_number_length(self, e2e_service):
        """Test safety number is 60 digits"""
        pk1 = b"a" * 32
        pk2 = b"b" * 32

        safety_number = e2e_service.generate_safety_number(pk1, pk2)

        assert len(safety_number) == 60
        assert safety_number.isdigit()

    def test_generate_safety_number_symmetric(self, e2e_service):
        """Test safety number is same regardless of key order"""
        pk1 = b"a" * 32
        pk2 = b"b" * 32

        sn1 = e2e_service.generate_safety_number(pk1, pk2)
        sn2 = e2e_service.generate_safety_number(pk2, pk1)

        assert sn1 == sn2

    def test_generate_safety_number_different_for_different_keys(self, e2e_service):
        """Test different keys produce different safety numbers"""
        pk1 = b"a" * 32
        pk2 = b"b" * 32
        pk3 = b"c" * 32

        sn1 = e2e_service.generate_safety_number(pk1, pk2)
        sn2 = e2e_service.generate_safety_number(pk1, pk3)

        assert sn1 != sn2

    def test_generate_safety_number_deterministic(self, e2e_service):
        """Test safety number is deterministic"""
        pk1 = b"x" * 32
        pk2 = b"y" * 32

        sn1 = e2e_service.generate_safety_number(pk1, pk2)
        sn2 = e2e_service.generate_safety_number(pk1, pk2)

        assert sn1 == sn2


# =============================================================================
# Encryption Tests
# =============================================================================

class TestEncryption:
    """Tests for message encryption"""

    def test_encrypt_message_returns_bytes(self, e2e_service_with_keys):
        """Test encryption returns bytes"""
        # Get own public key as recipient
        recipient_pk = bytes(e2e_service_with_keys._identity_keypair.public_key)

        ciphertext = e2e_service_with_keys.encrypt_message(
            recipient_pk, "Hello, World!"
        )

        assert isinstance(ciphertext, bytes)

    def test_encrypt_message_different_from_plaintext(self, e2e_service_with_keys):
        """Test ciphertext is different from plaintext"""
        recipient_pk = bytes(e2e_service_with_keys._identity_keypair.public_key)
        plaintext = "Secret message"

        ciphertext = e2e_service_with_keys.encrypt_message(recipient_pk, plaintext)

        assert ciphertext != plaintext.encode()

    def test_encrypt_message_not_deterministic(self, e2e_service_with_keys):
        """Test encryption is not deterministic (uses random nonce)"""
        recipient_pk = bytes(e2e_service_with_keys._identity_keypair.public_key)
        plaintext = "Same message"

        ct1 = e2e_service_with_keys.encrypt_message(recipient_pk, plaintext)
        ct2 = e2e_service_with_keys.encrypt_message(recipient_pk, plaintext)

        assert ct1 != ct2

    def test_encrypt_message_without_keypair_raises(self, e2e_service):
        """Test encryption fails without loaded keypair"""
        fake_pk = b"x" * 32

        with pytest.raises(RuntimeError) as exc_info:
            e2e_service.encrypt_message(fake_pk, "test")

        assert "not loaded" in str(exc_info.value)

    def test_encrypt_message_unicode(self, e2e_service_with_keys):
        """Test encryption handles unicode"""
        recipient_pk = bytes(e2e_service_with_keys._identity_keypair.public_key)
        plaintext = "Привет мир! 🔐"

        ciphertext = e2e_service_with_keys.encrypt_message(recipient_pk, plaintext)

        assert isinstance(ciphertext, bytes)


# =============================================================================
# Decryption Tests
# =============================================================================

class TestDecryption:
    """Tests for message decryption"""

    def test_decrypt_message_roundtrip(self, e2e_service_with_keys):
        """Test encrypt then decrypt returns original"""
        recipient_pk = bytes(e2e_service_with_keys._identity_keypair.public_key)
        original = "Hello, World!"

        ciphertext = e2e_service_with_keys.encrypt_message(recipient_pk, original)
        decrypted = e2e_service_with_keys.decrypt_message(ciphertext)

        assert decrypted == original

    def test_decrypt_message_unicode_roundtrip(self, e2e_service_with_keys):
        """Test unicode roundtrip"""
        recipient_pk = bytes(e2e_service_with_keys._identity_keypair.public_key)
        original = "Привет мир! 🔐 日本語"

        ciphertext = e2e_service_with_keys.encrypt_message(recipient_pk, original)
        decrypted = e2e_service_with_keys.decrypt_message(ciphertext)

        assert decrypted == original

    def test_decrypt_message_without_keypair_raises(self, e2e_service):
        """Test decryption fails without loaded keypair"""
        with pytest.raises(RuntimeError) as exc_info:
            e2e_service.decrypt_message(b"fake_ciphertext")

        assert "not loaded" in str(exc_info.value)

    def test_decrypt_message_wrong_key_raises(self, e2e_service_with_keys, mock_secure_enclave):
        """Test decryption fails with wrong key"""
        recipient_pk = bytes(e2e_service_with_keys._identity_keypair.public_key)
        ciphertext = e2e_service_with_keys.encrypt_message(recipient_pk, "secret")

        # Create another service with different keys
        service2 = E2EEncryptionService(Mock())
        service2.generate_identity_keypair("device_2", "pass")

        with pytest.raises(ValueError) as exc_info:
            service2.decrypt_message(ciphertext)

        assert "Decryption failed" in str(exc_info.value)

    def test_decrypt_message_tampered_raises(self, e2e_service_with_keys):
        """Test decryption fails with tampered ciphertext"""
        recipient_pk = bytes(e2e_service_with_keys._identity_keypair.public_key)
        ciphertext = e2e_service_with_keys.encrypt_message(recipient_pk, "secret")

        # Tamper with ciphertext
        tampered = bytearray(ciphertext)
        tampered[10] ^= 0xFF  # Flip bits
        tampered = bytes(tampered)

        with pytest.raises(ValueError) as exc_info:
            e2e_service_with_keys.decrypt_message(tampered)

        assert "Decryption failed" in str(exc_info.value)


# =============================================================================
# Signing Tests
# =============================================================================

class TestSigning:
    """Tests for message signing"""

    def test_sign_message_returns_bytes(self, e2e_service_with_keys):
        """Test signing returns bytes"""
        signature = e2e_service_with_keys.sign_message("test message")

        assert isinstance(signature, bytes)

    def test_sign_message_length(self, e2e_service_with_keys):
        """Test signature is 64 bytes"""
        signature = e2e_service_with_keys.sign_message("test message")

        assert len(signature) == 64

    def test_sign_message_deterministic(self, e2e_service_with_keys):
        """Test signing is deterministic (same message = same signature)"""
        message = "same message"

        sig1 = e2e_service_with_keys.sign_message(message)
        sig2 = e2e_service_with_keys.sign_message(message)

        assert sig1 == sig2

    def test_sign_message_different_for_different_messages(self, e2e_service_with_keys):
        """Test different messages produce different signatures"""
        sig1 = e2e_service_with_keys.sign_message("message 1")
        sig2 = e2e_service_with_keys.sign_message("message 2")

        assert sig1 != sig2

    def test_sign_message_without_keypair_raises(self, e2e_service):
        """Test signing fails without loaded keypair"""
        with pytest.raises(RuntimeError) as exc_info:
            e2e_service.sign_message("test")

        assert "not loaded" in str(exc_info.value)


# =============================================================================
# Signature Verification Tests
# =============================================================================

class TestSignatureVerification:
    """Tests for signature verification"""

    def test_verify_signature_valid(self, e2e_service_with_keys):
        """Test valid signature verifies"""
        message = "test message"
        signature = e2e_service_with_keys.sign_message(message)

        # Get verify key
        verify_key = bytes(e2e_service_with_keys._signing_keypair.verify_key)

        result = e2e_service_with_keys.verify_signature(message, signature, verify_key)

        assert result is True

    def test_verify_signature_invalid_signature(self, e2e_service_with_keys):
        """Test invalid signature fails verification"""
        message = "test message"
        verify_key = bytes(e2e_service_with_keys._signing_keypair.verify_key)

        # Fake signature
        fake_signature = b"x" * 64

        result = e2e_service_with_keys.verify_signature(message, fake_signature, verify_key)

        assert result is False

    def test_verify_signature_wrong_message(self, e2e_service_with_keys):
        """Test signature fails for different message"""
        signature = e2e_service_with_keys.sign_message("original message")
        verify_key = bytes(e2e_service_with_keys._signing_keypair.verify_key)

        result = e2e_service_with_keys.verify_signature(
            "different message", signature, verify_key
        )

        assert result is False

    def test_verify_signature_wrong_key(self, e2e_service_with_keys):
        """Test signature fails with wrong verify key"""
        message = "test message"
        signature = e2e_service_with_keys.sign_message(message)

        # Generate different key
        other_signing_key = nacl.signing.SigningKey.generate()
        wrong_verify_key = bytes(other_signing_key.verify_key)

        result = e2e_service_with_keys.verify_signature(
            message, signature, wrong_verify_key
        )

        assert result is False


# =============================================================================
# Multi-Device Export/Import Tests
# =============================================================================

class TestMultiDevice:
    """Tests for multi-device identity export/import"""

    def test_export_identity_returns_dict(self, e2e_service_with_keys):
        """Test export returns dict with required fields"""
        exported = e2e_service_with_keys.export_identity_for_linking("passphrase")

        assert "encrypted_bundle" in exported
        assert "salt" in exported
        assert "nonce" in exported

    def test_export_identity_encrypted_bundle_is_hex(self, e2e_service_with_keys):
        """Test encrypted bundle is hex string"""
        exported = e2e_service_with_keys.export_identity_for_linking("passphrase")

        # Should be valid hex
        try:
            bytes.fromhex(exported["encrypted_bundle"])
            bytes.fromhex(exported["salt"])
            bytes.fromhex(exported["nonce"])
        except ValueError:
            pytest.fail("Export data should be hex strings")

    def test_export_identity_without_keypair_raises(self, e2e_service):
        """Test export fails without loaded keypair"""
        with pytest.raises(RuntimeError) as exc_info:
            e2e_service.export_identity_for_linking("passphrase")

        assert "not loaded" in str(exc_info.value)

    def test_import_identity_roundtrip(self, e2e_service_with_keys, mock_secure_enclave):
        """Test export then import preserves keys"""
        # Get original public key
        original_pk = bytes(e2e_service_with_keys._identity_keypair.public_key)

        # Export
        exported = e2e_service_with_keys.export_identity_for_linking("passphrase")

        # Import in new service
        new_service = E2EEncryptionService(mock_secure_enclave)
        imported_pk, _ = new_service.import_identity_from_link(
            exported, "passphrase", "new_device"
        )

        assert imported_pk == original_pk

    def test_import_identity_stores_in_enclave(self, e2e_service_with_keys, mock_secure_enclave):
        """Test import stores keys in Secure Enclave"""
        exported = e2e_service_with_keys.export_identity_for_linking("passphrase")

        # Reset call counts
        mock_secure_enclave.store_key_in_keychain.reset_mock()

        new_service = E2EEncryptionService(mock_secure_enclave)
        new_service.import_identity_from_link(exported, "passphrase", "new_device_2")

        # Should have stored identity + signing keys
        assert mock_secure_enclave.store_key_in_keychain.call_count == 2

    def test_import_identity_wrong_passphrase_raises(self, e2e_service_with_keys, mock_secure_enclave):
        """Test import fails with wrong passphrase"""
        exported = e2e_service_with_keys.export_identity_for_linking("correct_pass")

        new_service = E2EEncryptionService(mock_secure_enclave)

        with pytest.raises(Exception):  # AESGCM raises InvalidTag
            new_service.import_identity_from_link(exported, "wrong_pass", "new_device")

    def test_import_identity_can_encrypt_decrypt(self, e2e_service_with_keys, mock_secure_enclave):
        """Test imported identity can encrypt/decrypt messages"""
        # Export
        exported = e2e_service_with_keys.export_identity_for_linking("passphrase")

        # Import in new service
        new_service = E2EEncryptionService(mock_secure_enclave)
        public_key, _ = new_service.import_identity_from_link(
            exported, "passphrase", "new_device"
        )

        # New service should be able to encrypt
        ciphertext = new_service.encrypt_message(public_key, "test message")

        # And decrypt
        decrypted = new_service.decrypt_message(ciphertext)

        assert decrypted == "test message"

    def test_import_identity_can_sign_verify(self, e2e_service_with_keys, mock_secure_enclave):
        """Test imported identity can sign and verify"""
        # Export
        exported = e2e_service_with_keys.export_identity_for_linking("passphrase")

        # Import in new service
        new_service = E2EEncryptionService(mock_secure_enclave)
        new_service.import_identity_from_link(exported, "passphrase", "new_device")

        # Sign with new service
        message = "test message"
        signature = new_service.sign_message(message)

        # Verify with original service's verify key
        verify_key = bytes(e2e_service_with_keys._signing_keypair.verify_key)
        result = new_service.verify_signature(message, signature, verify_key)

        assert result is True


# =============================================================================
# Global Function Tests
# =============================================================================

class TestGlobalFunctions:
    """Tests for module-level functions"""

    def test_get_e2e_service_creates_instance(self, cleanup_global):
        """Test get_e2e_service creates instance"""
        import api.e2e_encryption_service as module
        module._e2e_service = None

        # The import is "from secure_enclave_service import" (relative/sibling)
        with patch.dict('sys.modules', {'secure_enclave_service': MagicMock()}):
            import sys
            sys.modules['secure_enclave_service'].get_secure_enclave_service = Mock(return_value=Mock())

            service = get_e2e_service()

        assert service is not None
        assert isinstance(service, E2EEncryptionService)

    def test_get_e2e_service_returns_singleton(self, cleanup_global):
        """Test get_e2e_service returns same instance"""
        import api.e2e_encryption_service as module
        module._e2e_service = None

        with patch.dict('sys.modules', {'secure_enclave_service': MagicMock()}):
            import sys
            sys.modules['secure_enclave_service'].get_secure_enclave_service = Mock(return_value=Mock())

            service1 = get_e2e_service()
            service2 = get_e2e_service()

        assert service1 is service2


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case tests"""

    def test_encrypt_empty_message(self, e2e_service_with_keys):
        """Test encrypting empty message"""
        recipient_pk = bytes(e2e_service_with_keys._identity_keypair.public_key)

        ciphertext = e2e_service_with_keys.encrypt_message(recipient_pk, "")
        decrypted = e2e_service_with_keys.decrypt_message(ciphertext)

        assert decrypted == ""

    def test_encrypt_long_message(self, e2e_service_with_keys):
        """Test encrypting long message"""
        recipient_pk = bytes(e2e_service_with_keys._identity_keypair.public_key)
        long_message = "A" * 100000  # 100KB

        ciphertext = e2e_service_with_keys.encrypt_message(recipient_pk, long_message)
        decrypted = e2e_service_with_keys.decrypt_message(ciphertext)

        assert decrypted == long_message

    def test_sign_empty_message(self, e2e_service_with_keys):
        """Test signing empty message"""
        signature = e2e_service_with_keys.sign_message("")

        assert len(signature) == 64

    def test_sign_long_message(self, e2e_service_with_keys):
        """Test signing long message"""
        long_message = "B" * 100000

        signature = e2e_service_with_keys.sign_message(long_message)
        verify_key = bytes(e2e_service_with_keys._signing_keypair.verify_key)

        result = e2e_service_with_keys.verify_signature(
            long_message, signature, verify_key
        )

        assert result is True

    def test_fingerprint_empty_key(self, e2e_service):
        """Test fingerprint of empty bytes"""
        fingerprint = e2e_service.generate_fingerprint(b"")

        expected = hashlib.sha256(b"").digest()
        assert fingerprint == expected

    def test_format_fingerprint_empty(self, e2e_service):
        """Test formatting empty fingerprint"""
        formatted = e2e_service.format_fingerprint(b"")

        assert formatted == ""

    def test_safety_number_same_keys(self, e2e_service):
        """Test safety number with identical keys"""
        pk = b"x" * 32

        # Should work even with same key (edge case)
        safety_number = e2e_service.generate_safety_number(pk, pk)

        assert len(safety_number) == 60


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests"""

    def test_full_conversation_flow(self, mock_secure_enclave):
        """Test complete conversation flow between two parties"""
        # Alice generates identity
        alice_service = E2EEncryptionService(mock_secure_enclave)
        alice_pk, alice_fp = alice_service.generate_identity_keypair("alice", "alice_pass")

        # Bob generates identity
        bob_service = E2EEncryptionService(Mock())
        bob_pk, bob_fp = bob_service.generate_identity_keypair("bob", "bob_pass")

        # Both compute safety number (should match)
        alice_sn = alice_service.generate_safety_number(alice_pk, bob_pk)
        bob_sn = bob_service.generate_safety_number(bob_pk, alice_pk)
        assert alice_sn == bob_sn

        # Alice sends encrypted message to Bob
        message = "Hello Bob!"
        ciphertext = alice_service.encrypt_message(bob_pk, message)
        signature = alice_service.sign_message(message)

        # Bob decrypts and verifies
        decrypted = bob_service.decrypt_message(ciphertext)
        alice_verify_key = bytes(alice_service._signing_keypair.verify_key)
        is_valid = bob_service.verify_signature(decrypted, signature, alice_verify_key)

        assert decrypted == message
        assert is_valid is True

    def test_device_linking_preserves_functionality(self, mock_secure_enclave):
        """Test that linked device can communicate with existing contacts"""
        # Original device
        original = E2EEncryptionService(mock_secure_enclave)
        original_pk, _ = original.generate_identity_keypair("phone", "pass")

        # Contact (Bob)
        bob = E2EEncryptionService(Mock())
        bob_pk, _ = bob.generate_identity_keypair("bob", "pass")

        # Bob sends message to original device
        message = "Hey!"
        ciphertext = bob.encrypt_message(original_pk, message)

        # Link to new device (tablet)
        exported = original.export_identity_for_linking("pass")
        tablet = E2EEncryptionService(mock_secure_enclave)
        tablet.import_identity_from_link(exported, "pass", "tablet")

        # Tablet should be able to decrypt message intended for original
        decrypted = tablet.decrypt_message(ciphertext)
        assert decrypted == message
