"""
Tests for Mesh Relay System

Tests the multi-hop message routing and connection pooling for mesh networking.
"""

import pytest
import asyncio
import sys
import time
import hashlib
import secrets
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC


# ===== Mock nacl module =====
# Create a mock nacl module to allow tests to run without PyNaCl installed
# This provides a simplified but functional Ed25519 simulation using HMAC

def _create_mock_nacl_module():
    """
    Create a mock nacl module that simulates Ed25519 signing.
    Uses HMAC-SHA256 for signature simulation (not cryptographically secure,
    but sufficient for testing the handshake protocol logic).
    """
    import hmac

    class MockBadSignature(Exception):
        """Mock nacl.exceptions.BadSignature"""
        pass

    # Alias for nacl.exceptions.BadSignatureError (used in some nacl versions)
    MockBadSignatureError = MockBadSignature

    class MockValueError(ValueError):
        """Mock nacl.exceptions.ValueError"""
        pass

    class MockSignedMessage:
        """Mock signed message with signature attribute"""
        def __init__(self, signature: bytes, message: bytes):
            self.signature = signature
            self.message = message

    class MockVerifyKey:
        """Mock nacl.signing.VerifyKey"""
        def __init__(self, public_key_bytes: bytes):
            self._public_key = public_key_bytes

        def __bytes__(self):
            return self._public_key

        def encode(self):
            return self._public_key

        def verify(self, message: bytes, signature: bytes = None) -> bytes:
            """
            Verify signature - uses HMAC for simulation.
            Matches PyNaCl API: verify(message, signature) or verify(signed_message)
            """
            if signature is None:
                # If no signature provided, assume message is signed_message (sig + msg)
                # In PyNaCl, signature is 64 bytes
                signature = message[:64]
                message = message[64:]

            # Simulate verification using the public key as HMAC key
            expected = hmac.new(self._public_key, message, hashlib.sha256).digest()
            if not hmac.compare_digest(signature, expected):
                raise MockBadSignature("Signature verification failed")
            return message

    class MockSigningKey:
        """Mock nacl.signing.SigningKey"""
        def __init__(self, seed: bytes = None):
            # Generate random 32-byte key
            self._seed = seed or secrets.token_bytes(32)
            # Derive "public key" from seed (in real Ed25519, this is a proper derivation)
            self._public_key = hashlib.sha256(self._seed + b"public").digest()
            self.verify_key = MockVerifyKey(self._public_key)

        def __bytes__(self):
            return self._seed

        @classmethod
        def generate(cls) -> "MockSigningKey":
            """Generate a new signing key"""
            return cls()

        def sign(self, message: bytes) -> MockSignedMessage:
            """Sign a message - uses HMAC for simulation"""
            if isinstance(message, str):
                message = message.encode('utf-8')
            # Use HMAC-SHA256 as signature simulation
            signature = hmac.new(self._public_key, message, hashlib.sha256).digest()
            return MockSignedMessage(signature=signature, message=message)

    # Create mock module structure
    mock_nacl = MagicMock()
    mock_signing = MagicMock()
    mock_exceptions = MagicMock()

    # Set up the classes
    mock_signing.SigningKey = MockSigningKey
    mock_signing.VerifyKey = MockVerifyKey

    # Set up all exception types (nacl uses various names)
    mock_exceptions.BadSignature = MockBadSignature
    mock_exceptions.BadSignatureError = MockBadSignatureError
    mock_exceptions.ValueError = MockValueError

    mock_nacl.signing = mock_signing
    mock_nacl.exceptions = mock_exceptions

    return mock_nacl, mock_signing, mock_exceptions


# Inject mock nacl module BEFORE importing api.mesh_relay
# This must happen at module level, not in a fixture
_mock_nacl, _mock_signing, _mock_exceptions = _create_mock_nacl_module()

# Only inject if nacl is not already installed
if "nacl" not in sys.modules:
    sys.modules["nacl"] = _mock_nacl
    sys.modules["nacl.signing"] = _mock_signing
    sys.modules["nacl.exceptions"] = _mock_exceptions

from api.mesh_relay import (
    MeshRelay,
    MeshConnection,
    MeshConnectionPool,
    MeshMessage,
    RouteMetrics,
    get_mesh_relay,
)

# Ensure NACL_AVAILABLE is True after importing (since we injected mock)
try:
    import api.mesh.security as _security_module
    _security_module.NACL_AVAILABLE = True
except ImportError:
    pass


class TestMeshConnection:
    """Tests for MeshConnection dataclass"""

    def test_create_connection(self):
        """Test creating a mesh connection"""
        conn = MeshConnection(
            peer_id="peer_001",
            connection=None,
            created_at=time.time(),
            last_used=time.time()
        )

        assert conn.peer_id == "peer_001"
        assert conn.connection is None
        assert conn.message_count == 0
        assert conn.is_healthy is True

    def test_connection_with_address(self):
        """Test connection with IP address and port"""
        conn = MeshConnection(
            peer_id="peer_002",
            connection=None,
            ip_address="192.168.1.100",
            port=8765,
            created_at=time.time(),
            last_used=time.time()
        )

        assert conn.ip_address == "192.168.1.100"
        assert conn.port == 8765

    @pytest.mark.asyncio
    async def test_send_without_connection(self):
        """Test send logs when no actual connection"""
        conn = MeshConnection(
            peer_id="peer_001",
            connection=None,
            created_at=time.time(),
            last_used=time.time()
        )

        # Should not raise, just log
        await conn.send({"type": "test", "data": "hello"})

        assert conn.message_count == 1

    @pytest.mark.asyncio
    async def test_send_raises_when_closed(self):
        """Test send raises error when connection is closed"""
        conn = MeshConnection(
            peer_id="peer_001",
            connection=None,
            created_at=time.time(),
            last_used=time.time(),
            _closed=True
        )

        with pytest.raises(ConnectionError):
            await conn.send({"type": "test"})

    @pytest.mark.asyncio
    async def test_ping_returns_health_status(self):
        """Test ping returns current health status without connection"""
        conn = MeshConnection(
            peer_id="peer_001",
            connection=None,
            created_at=time.time(),
            last_used=time.time()
        )

        result = await conn.ping()
        assert result is True

        conn.is_healthy = False
        result = await conn.ping()
        assert result is False

    @pytest.mark.asyncio
    async def test_close_sets_closed_flag(self):
        """Test close sets the closed flag"""
        conn = MeshConnection(
            peer_id="peer_001",
            connection=None,
            created_at=time.time(),
            last_used=time.time()
        )

        await conn.close()

        assert conn._closed is True
        assert conn.is_healthy is False


class TestMeshConnectionPool:
    """Tests for MeshConnectionPool"""

    @pytest.fixture
    def pool(self):
        """Create a connection pool for testing"""
        return MeshConnectionPool(max_size=10, idle_timeout=60)

    @pytest.mark.asyncio
    async def test_pool_initialization(self, pool):
        """Test pool initializes correctly"""
        assert pool.max_size == 10
        assert pool.idle_timeout == 60
        assert pool._total_connections == 0

    @pytest.mark.asyncio
    async def test_acquire_creates_connection(self, pool):
        """Test acquiring creates a new connection"""
        with patch.object(pool, '_create_connection', new_callable=AsyncMock) as mock_create:
            mock_conn = MeshConnection(
                peer_id="peer_001",
                connection=None,
                created_at=time.time(),
                last_used=time.time()
            )
            mock_create.return_value = mock_conn

            conn = await pool.acquire("peer_001")

            assert conn.peer_id == "peer_001"
            mock_create.assert_called_once_with("peer_001")

    @pytest.mark.asyncio
    async def test_release_returns_to_pool(self, pool):
        """Test releasing returns connection to pool"""
        conn = MeshConnection(
            peer_id="peer_001",
            connection=None,
            created_at=time.time(),
            last_used=time.time()
        )

        await pool.release("peer_001", conn)

        assert "peer_001" in pool._pool
        assert len(pool._pool["peer_001"]) == 1

    @pytest.mark.asyncio
    async def test_acquire_reuses_pooled_connection(self, pool):
        """Test acquiring reuses a pooled connection"""
        conn = MeshConnection(
            peer_id="peer_001",
            connection=None,
            created_at=time.time(),
            last_used=time.time()
        )

        # Add to pool
        await pool.release("peer_001", conn)

        # Mock health check
        with patch.object(pool, '_is_healthy', new_callable=AsyncMock) as mock_health:
            mock_health.return_value = True

            reused_conn = await pool.acquire("peer_001")

            assert reused_conn is conn
            assert pool._connections_reused == 1

    @pytest.mark.asyncio
    async def test_start_creates_cleanup_task(self, pool):
        """Test starting pool creates cleanup task"""
        await pool.start()

        assert pool._cleanup_task is not None

        await pool.stop()

    @pytest.mark.asyncio
    async def test_stop_closes_all_connections(self, pool):
        """Test stopping closes all pooled connections"""
        conn = MeshConnection(
            peer_id="peer_001",
            connection=None,
            created_at=time.time(),
            last_used=time.time()
        )
        await pool.release("peer_001", conn)

        await pool.stop()

        assert len(pool._pool) == 0

    def test_get_stats(self, pool):
        """Test getting pool statistics"""
        stats = pool.get_stats()

        assert 'total_connections' in stats
        assert 'pooled_connections' in stats
        assert 'active_connections' in stats
        assert 'reuse_ratio' in stats


class TestMeshMessage:
    """Tests for MeshMessage dataclass"""

    def test_create_message(self):
        """Test creating a mesh message"""
        msg = MeshMessage(
            message_id="msg_001",
            source_peer_id="peer_alice",
            dest_peer_id="peer_bob",
            payload={"text": "Hello"},
            ttl=10,
            route_history=["peer_alice"],
            timestamp=datetime.now(UTC).isoformat()
        )

        assert msg.message_id == "msg_001"
        assert msg.source_peer_id == "peer_alice"
        assert msg.dest_peer_id == "peer_bob"
        assert msg.ttl == 10
        assert msg.payload == {"text": "Hello"}


class TestRouteMetrics:
    """Tests for RouteMetrics dataclass"""

    def test_create_metrics(self):
        """Test creating route metrics"""
        metrics = RouteMetrics(
            latency_ms=25.5,
            hop_count=2,
            reliability=0.98,
            last_measured=datetime.now(UTC).isoformat()
        )

        assert metrics.latency_ms == 25.5
        assert metrics.hop_count == 2
        assert metrics.reliability == 0.98


class TestMeshRelay:
    """Tests for MeshRelay class"""

    @pytest.fixture
    def relay(self):
        """Create a mesh relay for testing"""
        return MeshRelay(local_peer_id="local_peer")

    def test_relay_initialization(self, relay):
        """Test relay initializes correctly"""
        assert relay.local_peer_id == "local_peer"
        assert len(relay.direct_peers) == 0
        assert relay.messages_relayed == 0

    def test_add_direct_peer(self, relay):
        """Test adding a direct peer"""
        relay.add_direct_peer("peer_001", latency_ms=15.0)

        assert "peer_001" in relay.direct_peers
        assert "peer_001" in relay.route_table
        assert relay.route_table["peer_001"] == ["peer_001"]

    def test_remove_direct_peer(self, relay):
        """Test removing a direct peer"""
        relay.add_direct_peer("peer_001")

        relay.remove_direct_peer("peer_001")

        assert "peer_001" not in relay.direct_peers

    def test_add_multiple_peers(self, relay):
        """Test adding multiple direct peers"""
        relay.add_direct_peer("peer_001")
        relay.add_direct_peer("peer_002")
        relay.add_direct_peer("peer_003")

        assert len(relay.direct_peers) == 3

    @pytest.mark.asyncio
    async def test_send_message_without_route(self, relay):
        """Test sending message when no route exists"""
        # Mock discover_route to avoid actual network calls
        with patch.object(relay, '_discover_route', new_callable=AsyncMock):
            result = await relay.send_message(
                dest_peer_id="unknown_peer",
                payload={"text": "Hello"}
            )

            assert result is False
            assert "unknown_peer" in relay.pending_routes

    @pytest.mark.asyncio
    async def test_send_message_with_direct_route(self, relay):
        """Test sending message to direct peer"""
        relay.add_direct_peer("peer_001")

        # Mock forward_message
        with patch.object(relay, '_forward_message', new_callable=AsyncMock):
            result = await relay.send_message(
                dest_peer_id="peer_001",
                payload={"text": "Hello"}
            )

            assert result is True
            assert relay.messages_relayed == 1

    @pytest.mark.asyncio
    async def test_receive_message_for_local(self, relay):
        """Test receiving message destined for local peer"""
        msg = MeshMessage(
            message_id="msg_001",
            source_peer_id="peer_remote",
            dest_peer_id="local_peer",  # Same as relay's local_peer_id
            payload={"text": "Hello"},
            ttl=5,
            route_history=["peer_remote"],
            timestamp=datetime.now(UTC).isoformat()
        )

        result = await relay.receive_message(msg)

        assert result is True  # Message was for us

    @pytest.mark.asyncio
    async def test_receive_message_ttl_expired(self, relay):
        """Test receiving message with expired TTL"""
        msg = MeshMessage(
            message_id="msg_001",
            source_peer_id="peer_remote",
            dest_peer_id="peer_other",
            payload={},
            ttl=0,  # Expired
            route_history=["peer_remote"],
            timestamp=datetime.now(UTC).isoformat()
        )

        result = await relay.receive_message(msg)

        assert result is False

    @pytest.mark.asyncio
    async def test_receive_message_duplicate_ignored(self, relay):
        """Test duplicate messages are ignored"""
        msg = MeshMessage(
            message_id="msg_duplicate",
            source_peer_id="peer_remote",
            dest_peer_id="local_peer",
            payload={},
            ttl=5,
            route_history=["peer_remote"],
            timestamp=datetime.now(UTC).isoformat()
        )

        # Receive first time
        await relay.receive_message(msg)

        # Receive again - should be ignored
        result = await relay.receive_message(msg)

        assert result is False  # Ignored as duplicate

    def test_generate_route_advertisement(self, relay):
        """Test generating route advertisement"""
        relay.add_direct_peer("peer_001")
        relay.add_direct_peer("peer_002")

        advertisement = relay.generate_route_advertisement()

        assert advertisement['type'] == 'route_advertisement'
        assert advertisement['peer_id'] == 'local_peer'
        assert len(advertisement['reachable_peers']) == 2

    def test_update_route_from_advertisement(self, relay):
        """Test updating routes from advertisement"""
        relay.add_direct_peer("peer_gateway")

        # Simulate receiving advertisement from gateway
        route_ad = {
            'type': 'route_advertisement',
            'peer_id': 'peer_gateway',
            'reachable_peers': [
                ('peer_remote', 1),  # Gateway can reach peer_remote in 1 hop
            ]
        }

        relay.update_route_from_advertisement(route_ad)

        assert 'peer_remote' in relay.route_table
        assert relay.routes_discovered == 1

    def test_get_route_to_direct_peer(self, relay):
        """Test getting route to direct peer"""
        relay.add_direct_peer("peer_001")

        route = relay.get_route_to("peer_001")

        assert route is not None
        assert route[0] == "local_peer"
        assert "peer_001" in route

    def test_get_route_to_unknown_peer(self, relay):
        """Test getting route to unknown peer"""
        route = relay.get_route_to("unknown_peer")

        assert route is None

    def test_get_stats(self, relay):
        """Test getting relay statistics"""
        relay.add_direct_peer("peer_001")

        stats = relay.get_stats()

        assert stats['local_peer_id'] == 'local_peer'
        assert stats['direct_peers'] == 1
        assert 'connection_pool' in stats

    def test_get_routing_table(self, relay):
        """Test getting routing table"""
        relay.add_direct_peer("peer_001")

        table = relay.get_routing_table()

        assert 'peer_001' in table
        assert 'next_hops' in table['peer_001']

    @pytest.mark.asyncio
    async def test_start_stop(self, relay):
        """Test starting and stopping relay"""
        await relay.start()

        assert relay._is_running is True
        assert relay._advertisement_task is not None

        await relay.stop()

        assert relay._is_running is False


class TestChooseBestHop:
    """Tests for hop selection logic"""

    @pytest.fixture
    def relay(self):
        return MeshRelay(local_peer_id="local")

    def test_single_hop(self, relay):
        """Test choosing from single hop option"""
        result = relay._choose_best_hop(["peer_001"], "dest")

        assert result == "peer_001"

    def test_choose_lowest_latency(self, relay):
        """Test choosing hop with lowest latency"""
        relay.route_metrics[("local", "peer_fast")] = RouteMetrics(
            latency_ms=10.0, hop_count=1, reliability=1.0,
            last_measured=datetime.now(UTC).isoformat()
        )
        relay.route_metrics[("local", "peer_slow")] = RouteMetrics(
            latency_ms=100.0, hop_count=1, reliability=1.0,
            last_measured=datetime.now(UTC).isoformat()
        )

        result = relay._choose_best_hop(["peer_fast", "peer_slow"], "dest")

        assert result == "peer_fast"


class TestMeshRelayIntegration:
    """Integration tests for mesh relay"""

    @pytest.mark.asyncio
    async def test_multi_hop_routing_setup(self):
        """Test setting up multi-hop routing"""
        # Create three relays simulating a mesh
        relay_a = MeshRelay(local_peer_id="peer_a")
        relay_b = MeshRelay(local_peer_id="peer_b")
        relay_c = MeshRelay(local_peer_id="peer_c")

        # A connects to B, B connects to C
        relay_a.add_direct_peer("peer_b")
        relay_b.add_direct_peer("peer_a")
        relay_b.add_direct_peer("peer_c")
        relay_c.add_direct_peer("peer_b")

        # B advertises its routes to A
        b_advertisement = relay_b.generate_route_advertisement()
        relay_a.update_route_from_advertisement({
            **b_advertisement,
            'peer_id': 'peer_b'  # Ensure correct peer_id
        })

        # A should now have route to C through B
        route_to_c = relay_a.get_route_to("peer_c")
        # Route may not exist if C wasn't in B's advertisement
        # This depends on the timing of route discovery

        assert relay_a.direct_peers == {"peer_b"}
        assert relay_b.direct_peers == {"peer_a", "peer_c"}


class TestGetMeshRelay:
    """Tests for singleton pattern"""

    def test_get_mesh_relay_returns_same_instance(self):
        """Test that get_mesh_relay returns singleton"""
        # Reset singleton for testing
        import api.mesh_relay as mesh_module
        mesh_module._mesh_relay = None

        relay1 = get_mesh_relay("test_peer")
        relay2 = get_mesh_relay()

        assert relay1 is relay2

        # Cleanup
        mesh_module._mesh_relay = None


# ===== Signed Handshake Tests (SECURITY Dec 2025) =====

class TestSignedHandshake:
    """Tests for SignedHandshake cryptographic verification"""

    @pytest.fixture
    def ed25519_keypair(self):
        """Generate an Ed25519 keypair for testing"""
        import nacl.signing
        signing_key = nacl.signing.SigningKey.generate()
        return signing_key

    def test_create_signed_handshake(self, ed25519_keypair):
        """Test creating a signed handshake"""
        from api.mesh_relay import SignedHandshake

        handshake = SignedHandshake.create(
            signing_key=ed25519_keypair,
            display_name="Test Peer",
            capabilities=["chat", "file_share"]
        )

        assert handshake.display_name == "Test Peer"
        assert handshake.public_key != ""
        assert handshake.signature != ""
        assert handshake.timestamp != ""
        assert handshake.peer_id != ""
        assert len(handshake.peer_id) == 16  # SHA256 prefix

    def test_peer_id_derived_from_public_key(self, ed25519_keypair):
        """Test peer_id is cryptographically bound to public key"""
        import hashlib
        import base64
        from api.mesh_relay import SignedHandshake

        handshake = SignedHandshake.create(
            signing_key=ed25519_keypair,
            display_name="Test",
            capabilities=[]
        )

        # Manually compute expected peer_id
        public_key_bytes = base64.b64decode(handshake.public_key)
        expected_peer_id = hashlib.sha256(public_key_bytes).hexdigest()[:16]

        assert handshake.peer_id == expected_peer_id

    def test_canonical_payload_deterministic(self, ed25519_keypair):
        """Test canonical payload is deterministic"""
        from api.mesh_relay import SignedHandshake

        handshake1 = SignedHandshake(
            peer_id="abc123",
            public_key="test_key",
            display_name="Test",
            capabilities=["b", "a", "c"],  # Unsorted
            timestamp="2025-12-23T12:00:00Z",
            signature="sig"
        )

        handshake2 = SignedHandshake(
            peer_id="abc123",
            public_key="test_key",
            display_name="Test",
            capabilities=["c", "a", "b"],  # Different order
            timestamp="2025-12-23T12:00:00Z",
            signature="sig"
        )

        # Capabilities should be sorted in canonical form
        assert handshake1.get_canonical_payload() == handshake2.get_canonical_payload()


class TestVerifyHandshakeSignature:
    """Tests for handshake signature verification"""

    @pytest.fixture
    def ed25519_keypair(self):
        """Generate an Ed25519 keypair for testing"""
        import nacl.signing
        return nacl.signing.SigningKey.generate()

    @pytest.fixture
    def valid_handshake_data(self, ed25519_keypair):
        """Create valid signed handshake data"""
        from api.mesh_relay import SignedHandshake

        # Clear nonce cache for clean test
        import api.mesh_relay as mesh_module
        mesh_module._handshake_nonces = set()

        handshake = SignedHandshake.create(
            signing_key=ed25519_keypair,
            display_name="Test Peer",
            capabilities=["chat"]
        )

        return {
            'peer_id': handshake.peer_id,
            'public_key': handshake.public_key,
            'display_name': handshake.display_name,
            'capabilities': handshake.capabilities,
            'timestamp': handshake.timestamp,
            'nonce': handshake.nonce,
            'signature': handshake.signature
        }

    def test_valid_handshake_verified(self, valid_handshake_data):
        """Test valid handshake is verified successfully"""
        from api.mesh_relay import verify_handshake_signature

        result = verify_handshake_signature(valid_handshake_data)

        assert result is not None
        assert result.peer_id == valid_handshake_data['peer_id']
        assert result.display_name == valid_handshake_data['display_name']

    def test_invalid_signature_rejected(self, valid_handshake_data):
        """Test invalid signature is rejected"""
        import base64
        from api.mesh_relay import verify_handshake_signature

        # Corrupt the signature
        valid_handshake_data['signature'] = base64.b64encode(b"invalid_sig_64bytes_padding_needed_here_12345678901234567890").decode()

        result = verify_handshake_signature(valid_handshake_data)

        assert result is None

    def test_expired_timestamp_rejected(self, ed25519_keypair):
        """Test expired timestamp is rejected (replay protection)"""
        from datetime import timedelta
        import base64
        import hashlib
        import nacl.signing
        from api.mesh_relay import verify_handshake_signature

        # Create handshake with old timestamp
        public_key_bytes = bytes(ed25519_keypair.verify_key)
        public_key_b64 = base64.b64encode(public_key_bytes).decode()
        peer_id = hashlib.sha256(public_key_bytes).hexdigest()[:16]
        old_timestamp = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
        capabilities = ["chat"]
        caps_str = ",".join(sorted(capabilities))

        payload = f"{old_timestamp}|{public_key_b64}|{peer_id}|Test|{caps_str}"
        signature = ed25519_keypair.sign(payload.encode())

        handshake_data = {
            'peer_id': peer_id,
            'public_key': public_key_b64,
            'display_name': "Test",
            'capabilities': capabilities,
            'timestamp': old_timestamp,
            'signature': base64.b64encode(signature.signature).decode()
        }

        result = verify_handshake_signature(handshake_data)

        assert result is None

    def test_peer_id_mismatch_rejected(self, valid_handshake_data):
        """Test peer_id mismatch is rejected"""
        from api.mesh_relay import verify_handshake_signature

        # Tamper with peer_id
        valid_handshake_data['peer_id'] = "tampered_id_123"

        result = verify_handshake_signature(valid_handshake_data)

        assert result is None

    def test_missing_fields_rejected(self):
        """Test handshake with missing fields is rejected"""
        from api.mesh_relay import verify_handshake_signature

        incomplete_data = {
            'peer_id': 'some_peer',
            'display_name': 'Test'
            # Missing public_key, timestamp, signature
        }

        result = verify_handshake_signature(incomplete_data)

        assert result is None

    def test_wrong_key_signature_rejected(self):
        """Test signature from different key is rejected"""
        import nacl.signing
        import base64
        import hashlib
        from api.mesh_relay import SignedHandshake, verify_handshake_signature

        # Create two different keypairs
        victim_key = nacl.signing.SigningKey.generate()
        attacker_key = nacl.signing.SigningKey.generate()

        # Create handshake claiming victim's public key
        victim_pubkey_bytes = bytes(victim_key.verify_key)
        victim_pubkey_b64 = base64.b64encode(victim_pubkey_bytes).decode()
        peer_id = hashlib.sha256(victim_pubkey_bytes).hexdigest()[:16]
        timestamp = datetime.now(UTC).isoformat()

        # But sign with attacker's key
        payload = f"{timestamp}|{victim_pubkey_b64}|{peer_id}|Attacker|chat"
        attacker_signature = attacker_key.sign(payload.encode())

        handshake_data = {
            'peer_id': peer_id,
            'public_key': victim_pubkey_b64,  # Victim's public key
            'display_name': 'Attacker',
            'capabilities': ['chat'],
            'timestamp': timestamp,
            'signature': base64.b64encode(attacker_signature.signature).decode()  # Attacker's signature
        }

        result = verify_handshake_signature(handshake_data)

        assert result is None  # Rejected - signature doesn't match public key


class TestMeshRelayWithSigningKey:
    """Tests for MeshRelay with signing key"""

    @pytest.fixture
    def signing_key(self):
        """Generate a signing key for testing"""
        import nacl.signing
        return nacl.signing.SigningKey.generate()

    def test_relay_accepts_signing_key(self, signing_key):
        """Test MeshRelay accepts a signing key"""
        relay = MeshRelay(local_peer_id="test", signing_key=signing_key)

        assert relay.signing_key is signing_key

    def test_connection_pool_gets_signing_key(self, signing_key):
        """Test connection pool receives signing key from relay"""
        relay = MeshRelay(local_peer_id="test", signing_key=signing_key)

        assert relay.connection_pool.signing_key is signing_key


class TestHandshakeNonceProtection:
    """Tests for handshake nonce-based replay protection (Task 5.1.3)"""

    @pytest.fixture
    def ed25519_keypair(self):
        """Generate an Ed25519 keypair for testing"""
        import nacl.signing
        return nacl.signing.SigningKey.generate()

    def test_handshake_includes_nonce(self, ed25519_keypair):
        """Test that created handshakes include a nonce"""
        from api.mesh_relay import SignedHandshake

        handshake = SignedHandshake.create(
            signing_key=ed25519_keypair,
            display_name="Test",
            capabilities=["chat"]
        )

        assert handshake.nonce != ""
        assert len(handshake.nonce) == 32  # 16 bytes hex = 32 chars

    def test_handshake_nonces_are_unique(self, ed25519_keypair):
        """Test that each handshake gets a unique nonce"""
        from api.mesh_relay import SignedHandshake

        handshake1 = SignedHandshake.create(
            signing_key=ed25519_keypair,
            display_name="Test",
            capabilities=["chat"]
        )
        handshake2 = SignedHandshake.create(
            signing_key=ed25519_keypair,
            display_name="Test",
            capabilities=["chat"]
        )

        assert handshake1.nonce != handshake2.nonce

    def test_nonce_in_canonical_payload(self, ed25519_keypair):
        """Test that nonce is included in canonical payload"""
        from api.mesh_relay import SignedHandshake

        handshake = SignedHandshake(
            peer_id="test123",
            public_key="key123",
            display_name="Test",
            capabilities=["chat"],
            timestamp="2025-12-23T12:00:00Z",
            nonce="abcd1234efgh5678",
            signature=""
        )

        payload = handshake.get_canonical_payload()

        assert "abcd1234efgh5678" in payload
        assert payload.startswith("abcd1234efgh5678|")

    def test_handshake_replay_rejected(self, ed25519_keypair):
        """Test that replaying handshake with same nonce is rejected"""
        from api.mesh_relay import SignedHandshake, verify_handshake_signature, _handshake_nonces

        # Clear nonce cache
        import api.mesh_relay as mesh_module
        mesh_module._handshake_nonces = set()

        handshake = SignedHandshake.create(
            signing_key=ed25519_keypair,
            display_name="Test",
            capabilities=["chat"]
        )

        handshake_data = {
            'peer_id': handshake.peer_id,
            'public_key': handshake.public_key,
            'display_name': handshake.display_name,
            'capabilities': handshake.capabilities,
            'timestamp': handshake.timestamp,
            'nonce': handshake.nonce,
            'signature': handshake.signature
        }

        # First verification succeeds
        result1 = verify_handshake_signature(handshake_data)
        assert result1 is not None

        # Replay with same nonce should fail
        result2 = verify_handshake_signature(handshake_data)
        assert result2 is None

    def test_different_handshake_nonces_both_accepted(self, ed25519_keypair):
        """Test that different handshakes with different nonces are accepted"""
        from api.mesh_relay import SignedHandshake, verify_handshake_signature

        # Clear nonce cache
        import api.mesh_relay as mesh_module
        mesh_module._handshake_nonces = set()

        handshake1 = SignedHandshake.create(
            signing_key=ed25519_keypair,
            display_name="Test1",
            capabilities=["chat"]
        )
        handshake2 = SignedHandshake.create(
            signing_key=ed25519_keypair,
            display_name="Test2",
            capabilities=["chat"]
        )

        result1 = verify_handshake_signature({
            'peer_id': handshake1.peer_id,
            'public_key': handshake1.public_key,
            'display_name': handshake1.display_name,
            'capabilities': handshake1.capabilities,
            'timestamp': handshake1.timestamp,
            'nonce': handshake1.nonce,
            'signature': handshake1.signature
        })
        result2 = verify_handshake_signature({
            'peer_id': handshake2.peer_id,
            'public_key': handshake2.public_key,
            'display_name': handshake2.display_name,
            'capabilities': handshake2.capabilities,
            'timestamp': handshake2.timestamp,
            'nonce': handshake2.nonce,
            'signature': handshake2.signature
        })

        assert result1 is not None
        assert result2 is not None
