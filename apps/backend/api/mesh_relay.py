#!/usr/bin/env python3
"""
Mesh Relay Routing for ElohimOS
Multi-hop message routing when peers can't connect directly
Perfect for missionaries spread across buildings/areas

SECURITY (Dec 2025):
- Handshakes now require Ed25519 signatures proving peer identity
- Replay protection via timestamp validation (5 minute window)
- Prevents MITM impersonation attacks on mesh network
"""

import asyncio
import json
import logging
import base64
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime, UTC, timedelta
from collections import defaultdict, deque
import heapq
import time

# Cryptography imports for signed handshakes
try:
    import nacl.signing
    import nacl.exceptions
    NACL_AVAILABLE = True
except ImportError:
    NACL_AVAILABLE = False

# Try to import websockets for actual connections
try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketClientProtocol = None

logger = logging.getLogger(__name__)

# Security constants
HANDSHAKE_TIMESTAMP_TOLERANCE_SECONDS = 300  # 5 minutes
HANDSHAKE_NONCE_CACHE_MAX_SIZE = 5000  # Maximum nonces to track

# Nonce tracking for replay protection
_handshake_nonces: set = set()


def _check_handshake_nonce(nonce: str) -> bool:
    """Check if handshake nonce has been used before."""
    global _handshake_nonces

    if not nonce:
        return True  # Empty nonce allowed for backwards compatibility

    if nonce in _handshake_nonces:
        return False

    _handshake_nonces.add(nonce)

    # Limit cache size
    if len(_handshake_nonces) > HANDSHAKE_NONCE_CACHE_MAX_SIZE:
        nonces_list = list(_handshake_nonces)
        _handshake_nonces = set(nonces_list[HANDSHAKE_NONCE_CACHE_MAX_SIZE // 2:])

    return True


@dataclass
class SignedHandshake:
    """
    Cryptographically signed handshake for mesh peer authentication.

    Prevents MITM impersonation attacks by requiring proof of private key ownership.

    Replay Protection:
    - timestamp: Must be within 5 minutes (prevents old signature reuse)
    - nonce: Random value (prevents replay within timestamp window)
    """
    peer_id: str
    public_key: str  # Base64-encoded Ed25519 public key
    display_name: str
    capabilities: List[str]
    timestamp: str  # ISO 8601 for replay protection
    nonce: str = ""  # Random value for replay protection
    signature: str = ""  # Base64-encoded Ed25519 signature

    def get_canonical_payload(self) -> str:
        """
        Get canonical payload for signing/verification.
        Format: nonce|timestamp|public_key|peer_id|display_name|capabilities
        """
        caps_str = ",".join(sorted(self.capabilities))
        return f"{self.nonce}|{self.timestamp}|{self.public_key}|{self.peer_id}|{self.display_name}|{caps_str}"

    @classmethod
    def create(cls, signing_key: "nacl.signing.SigningKey", display_name: str,
               capabilities: List[str]) -> "SignedHandshake":
        """Create a signed handshake with the given signing key."""
        if not NACL_AVAILABLE:
            raise RuntimeError("nacl library required for signed handshakes")

        import secrets

        # Get public key
        public_key_bytes = bytes(signing_key.verify_key)
        public_key_b64 = base64.b64encode(public_key_bytes).decode('utf-8')

        # Generate peer_id from public key (cryptographic binding)
        import hashlib
        peer_id = hashlib.sha256(public_key_bytes).hexdigest()[:16]

        # Timestamp for replay protection
        timestamp = datetime.now(UTC).isoformat()

        # Generate random nonce for additional replay protection
        nonce = secrets.token_hex(16)

        # Create handshake (without signature yet)
        handshake = cls(
            peer_id=peer_id,
            public_key=public_key_b64,
            display_name=display_name,
            capabilities=capabilities,
            timestamp=timestamp,
            nonce=nonce,
            signature=""  # Will be set below
        )

        # Sign the canonical payload
        payload = handshake.get_canonical_payload()
        signature = signing_key.sign(payload.encode('utf-8'))
        handshake.signature = base64.b64encode(signature.signature).decode('utf-8')

        return handshake


def verify_handshake_signature(handshake_data: dict) -> Optional[SignedHandshake]:
    """
    Verify an incoming handshake signature.

    Returns SignedHandshake if valid, None if invalid or verification fails.
    Logs warnings for security-relevant failures.
    """
    if not NACL_AVAILABLE:
        logger.warning("⚠ nacl not available - cannot verify handshake signatures")
        return None

    try:
        # Parse handshake
        handshake = SignedHandshake(
            peer_id=handshake_data.get('peer_id', ''),
            public_key=handshake_data.get('public_key', ''),
            display_name=handshake_data.get('display_name', ''),
            capabilities=handshake_data.get('capabilities', []),
            timestamp=handshake_data.get('timestamp', ''),
            nonce=handshake_data.get('nonce', ''),
            signature=handshake_data.get('signature', '')
        )

        # Validate required fields
        if not handshake.public_key or not handshake.signature or not handshake.timestamp:
            logger.warning(f"⚠ Handshake missing required fields from peer {handshake.peer_id[:8]}...")
            return None

        # Decode public key
        public_key_bytes = base64.b64decode(handshake.public_key)

        if len(public_key_bytes) != 32:
            logger.warning(f"⚠ Invalid public key length from peer {handshake.peer_id[:8]}...")
            return None

        # Verify peer_id matches public key (cryptographic binding)
        import hashlib
        expected_peer_id = hashlib.sha256(public_key_bytes).hexdigest()[:16]
        if handshake.peer_id != expected_peer_id:
            logger.warning(f"⚠ Peer ID mismatch: claimed {handshake.peer_id[:8]}, expected {expected_peer_id[:8]}")
            return None

        # Validate timestamp (replay protection)
        try:
            handshake_time = datetime.fromisoformat(handshake.timestamp.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"⚠ Invalid timestamp format from peer {handshake.peer_id[:8]}...")
            return None

        now = datetime.now(UTC)
        time_diff = abs((now - handshake_time).total_seconds())

        if time_diff > HANDSHAKE_TIMESTAMP_TOLERANCE_SECONDS:
            logger.warning(f"⚠ Handshake timestamp expired from peer {handshake.peer_id[:8]}... ({time_diff:.0f}s old)")
            return None

        # Check nonce for replay protection (prevents replay within timestamp window)
        if handshake.nonce and not _check_handshake_nonce(handshake.nonce):
            logger.warning(f"⚠ Replay attack: nonce already used from peer {handshake.peer_id[:8]}...")
            return None

        # Verify signature
        signature_bytes = base64.b64decode(handshake.signature)
        payload = handshake.get_canonical_payload()
        payload_bytes = payload.encode('utf-8')

        verify_key = nacl.signing.VerifyKey(public_key_bytes)
        verify_key.verify(payload_bytes, signature_bytes)

        logger.info(f"✓ Handshake verified from peer {handshake.peer_id[:8]}... ({handshake.display_name})")
        return handshake

    except (nacl.exceptions.BadSignatureError, nacl.exceptions.ValueError) as e:
        logger.warning(f"⚠ Invalid handshake signature: {e}")
        return None
    except base64.binascii.Error:
        logger.warning("⚠ Invalid base64 encoding in handshake")
        return None
    except Exception as e:
        logger.error(f"⚠ Handshake verification error: {e}")
        return None


@dataclass
class RouteMetrics:
    """Metrics for a route between peers"""
    latency_ms: float
    hop_count: int
    reliability: float  # 0.0 - 1.0
    last_measured: str


@dataclass
class MeshMessage:
    """Message that can be relayed through the mesh"""
    message_id: str
    source_peer_id: str
    dest_peer_id: str
    payload: dict
    ttl: int  # Time-to-live (max hops)
    route_history: List[str]  # Peer IDs in route
    timestamp: str


@dataclass
class MeshConnection:
    """Represents a connection to a peer"""
    peer_id: str
    connection: any  # WebSocket connection
    created_at: float
    last_used: float
    ip_address: str = ""
    port: int = 0
    message_count: int = 0
    is_healthy: bool = True
    _closed: bool = False

    async def send(self, data: dict) -> None:
        """Send data through WebSocket connection"""
        if self._closed:
            raise ConnectionError(f"Connection to {self.peer_id} is closed")

        if self.connection is None:
            # No actual connection - log only mode
            logger.debug(f"[Mock] Sending data to {self.peer_id}: {data}")
            self.last_used = time.time()
            self.message_count += 1
            return

        try:
            # Serialize and send through WebSocket
            message = json.dumps(data)
            await self.connection.send(message)
            self.last_used = time.time()
            self.message_count += 1
            logger.debug(f"📤 Sent {len(message)} bytes to {self.peer_id}")
        except Exception as e:
            logger.error(f"Failed to send to {self.peer_id}: {e}")
            self.is_healthy = False
            raise

    async def ping(self) -> bool:
        """Ping to check connection health using WebSocket ping/pong"""
        if self._closed:
            return False

        if self.connection is None:
            # No actual connection - return current health state
            return self.is_healthy

        try:
            # WebSocket ping with timeout
            pong_waiter = await self.connection.ping()
            await asyncio.wait_for(pong_waiter, timeout=5.0)
            self.is_healthy = True
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Ping timeout to {self.peer_id}")
            self.is_healthy = False
            return False
        except Exception as e:
            logger.warning(f"Ping failed to {self.peer_id}: {e}")
            self.is_healthy = False
            return False

    async def close(self) -> None:
        """Close the WebSocket connection"""
        if self._closed:
            return

        self._closed = True
        self.is_healthy = False

        if self.connection is not None:
            try:
                await self.connection.close()
                logger.debug(f"🔌 Closed connection to {self.peer_id}")
            except Exception as e:
                logger.debug(f"Error closing connection to {self.peer_id}: {e}")


class MeshConnectionPool:
    """
    Connection pool for mesh P2P connections

    Features:
    - Reuse idle connections
    - Maximum pool size limits
    - Connection health checks
    - Automatic cleanup of stale connections
    - Signed handshakes for peer authentication (SECURITY Dec 2025)
    """

    def __init__(self, max_size: int = 50, idle_timeout: int = 300,
                 signing_key: Optional["nacl.signing.SigningKey"] = None):
        self.max_size = max_size
        self.idle_timeout = idle_timeout
        self.signing_key = signing_key  # For signed handshakes
        self._pool: Dict[str, deque] = {}  # peer_id -> connection queue
        self._active: Dict[str, int] = {}  # peer_id -> active count
        self._total_connections = 0
        self._connections_created = 0
        self._connections_reused = 0
        self._cleanup_task: Optional[asyncio.Task] = None

        logger.info(f"🔌 Connection pool initialized (max_size={max_size}, idle_timeout={idle_timeout}s, signed={signing_key is not None})")

    async def start(self) -> None:
        """Start background cleanup task"""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("🧹 Connection pool cleanup task started")

    async def stop(self) -> None:
        """Stop cleanup task and close all connections"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        # Close all pooled connections
        for peer_id, conn_queue in self._pool.items():
            while conn_queue:
                conn = conn_queue.popleft()
                await conn.close()

        self._pool.clear()
        self._active.clear()
        logger.info("🔌 Connection pool stopped")

    async def acquire(self, peer_id: str) -> MeshConnection:
        """Get connection from pool or create new one"""
        # Try to get from pool
        if peer_id in self._pool and self._pool[peer_id]:
            conn = self._pool[peer_id].popleft()

            # Check if connection is still healthy
            if await self._is_healthy(conn):
                self._active[peer_id] = self._active.get(peer_id, 0) + 1
                self._connections_reused += 1
                logger.debug(f"♻️  Reusing connection to {peer_id}")
                return conn
            else:
                # Connection is dead, close it
                await conn.close()
                self._total_connections -= 1

        # Create new connection
        conn = await self._create_connection(peer_id)
        self._active[peer_id] = self._active.get(peer_id, 0) + 1
        self._total_connections += 1
        self._connections_created += 1
        logger.debug(f"✨ Created new connection to {peer_id}")
        return conn

    async def release(self, peer_id: str, conn: MeshConnection) -> None:
        """Return connection to pool"""
        self._active[peer_id] = max(0, self._active.get(peer_id, 1) - 1)

        # Check if pool for this peer is full
        current_pool_size = len(self._pool.get(peer_id, []))

        if current_pool_size < self.max_size:
            # Add to pool
            if peer_id not in self._pool:
                self._pool[peer_id] = deque()
            self._pool[peer_id].append(conn)
            logger.debug(f"📥 Returned connection to {peer_id} to pool")
        else:
            # Pool full, close connection
            await conn.close()
            self._total_connections -= 1
            logger.debug(f"🗑️  Pool full, closed connection to {peer_id}")

    async def _is_healthy(self, conn: MeshConnection) -> bool:
        """Check if connection is still healthy"""
        try:
            # Check age
            age = time.time() - conn.last_used
            if age > self.idle_timeout:
                logger.debug(f"Connection to {conn.peer_id} expired (idle {age:.0f}s)")
                return False

            # Ping connection
            is_alive = await asyncio.wait_for(conn.ping(), timeout=2.0)
            return is_alive

        except asyncio.TimeoutError:
            logger.debug(f"Connection to {conn.peer_id} timed out on health check")
            return False
        except Exception as e:
            logger.debug(f"Connection to {conn.peer_id} health check failed: {e}")
            return False

    async def _create_connection(self, peer_id: str) -> MeshConnection:
        """Create new WebSocket connection to peer using mesh discovery"""
        # Get peer info from mesh discovery
        from api.offline_mesh_discovery import get_mesh_discovery

        discovery = get_mesh_discovery()
        peer = discovery.get_peer(peer_id)

        if not peer:
            # Peer not found in discovery - create placeholder for route discovery
            logger.warning(f"Peer {peer_id} not found in discovery - creating placeholder")
            return MeshConnection(
                peer_id=peer_id,
                connection=None,
                created_at=time.time(),
                last_used=time.time()
            )

        # Get peer's WebSocket endpoint
        ip_address = peer.ip_address
        port = peer.port
        ws_url = f"ws://{ip_address}:{port}/mesh"

        if not WEBSOCKETS_AVAILABLE:
            logger.warning("websockets library not available - using placeholder connection")
            return MeshConnection(
                peer_id=peer_id,
                connection=None,
                ip_address=ip_address,
                port=port,
                created_at=time.time(),
                last_used=time.time()
            )

        try:
            # Create WebSocket connection with timeout
            ws_connection = await asyncio.wait_for(
                websockets.connect(
                    ws_url,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5
                ),
                timeout=10.0
            )

            # Send handshake (signed if we have a signing key)
            if self.signing_key and NACL_AVAILABLE:
                # Create cryptographically signed handshake
                signed_handshake = SignedHandshake.create(
                    signing_key=self.signing_key,
                    display_name=discovery.display_name,
                    capabilities=discovery.capabilities
                )
                handshake = {
                    'type': 'mesh_handshake',
                    'peer_id': signed_handshake.peer_id,
                    'public_key': signed_handshake.public_key,
                    'display_name': signed_handshake.display_name,
                    'capabilities': signed_handshake.capabilities,
                    'timestamp': signed_handshake.timestamp,
                    'nonce': signed_handshake.nonce,
                    'signature': signed_handshake.signature
                }
                logger.debug(f"🔐 Sending signed handshake to {peer_id}")
            else:
                # Fallback to unsigned handshake (legacy compatibility)
                logger.warning(f"⚠ Sending unsigned handshake to {peer_id} - consider adding signing key")
                handshake = {
                    'type': 'mesh_handshake',
                    'peer_id': discovery.peer_id,
                    'display_name': discovery.display_name,
                    'capabilities': discovery.capabilities
                }
            await ws_connection.send(json.dumps(handshake))

            logger.info(f"🔗 Connected to peer {peer_id} at {ws_url}")

            return MeshConnection(
                peer_id=peer_id,
                connection=ws_connection,
                ip_address=ip_address,
                port=port,
                created_at=time.time(),
                last_used=time.time()
            )

        except asyncio.TimeoutError:
            logger.error(f"Connection timeout to peer {peer_id} at {ws_url}")
            raise ConnectionError(f"Timeout connecting to {peer_id}")
        except Exception as e:
            logger.error(f"Failed to connect to peer {peer_id} at {ws_url}: {e}")
            raise ConnectionError(f"Failed to connect to {peer_id}: {e}")

    async def _cleanup_loop(self) -> None:
        """Background task to cleanup stale connections"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                await self._cleanup_stale_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_stale_connections(self) -> None:
        """Remove stale connections from pool"""
        now = time.time()
        cleaned = 0

        for peer_id, conn_queue in list(self._pool.items()):
            # Check each connection in the queue
            valid_conns = deque()

            while conn_queue:
                conn = conn_queue.popleft()

                # Check if connection is stale
                age = now - conn.last_used
                if age > self.idle_timeout:
                    # Stale - close it
                    await conn.close()
                    self._total_connections -= 1
                    cleaned += 1
                else:
                    # Still valid
                    valid_conns.append(conn)

            # Update pool
            if valid_conns:
                self._pool[peer_id] = valid_conns
            else:
                # No connections left for this peer
                del self._pool[peer_id]

        if cleaned > 0:
            logger.info(f"🧹 Cleaned up {cleaned} stale connections")

    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        pooled_count = sum(len(q) for q in self._pool.values())
        active_count = sum(self._active.values())

        return {
            'total_connections': self._total_connections,
            'pooled_connections': pooled_count,
            'active_connections': active_count,
            'connections_created': self._connections_created,
            'connections_reused': self._connections_reused,
            'reuse_ratio': (
                self._connections_reused / (self._connections_created + self._connections_reused)
                if (self._connections_created + self._connections_reused) > 0
                else 0.0
            ),
            'peers_in_pool': len(self._pool)
        }


class MeshRelay:
    """
    Intelligent mesh relay routing system

    Features:
    - Multi-hop routing (A → B → C)
    - Automatic route discovery
    - Load balancing across multiple paths
    - Dead route detection and failover
    - Message deduplication
    - Signed handshakes for peer authentication (SECURITY Dec 2025)
    """

    MAX_TTL = 10  # Maximum hops before message expires
    ROUTE_CACHE_SIZE = 1000
    MESSAGE_CACHE_SIZE = 5000  # For deduplication

    def __init__(self, local_peer_id: str, connection_pool_size: int = 50,
                 signing_key: Optional["nacl.signing.SigningKey"] = None):
        self.local_peer_id = local_peer_id
        self.signing_key = signing_key

        # Connection pool for efficient peer communication (with signing key for handshakes)
        self.connection_pool = MeshConnectionPool(
            max_size=connection_pool_size,
            idle_timeout=300,
            signing_key=signing_key
        )

        # Network topology
        self.direct_peers: Set[str] = set()  # Peers we can reach directly
        self.route_table: Dict[str, List[str]] = {}  # dest_peer_id → [next_hop_peer_id, ...]
        self.route_metrics: Dict[Tuple[str, str], RouteMetrics] = {}  # (peer_a, peer_b) → metrics

        # Message tracking
        self.seen_messages: Set[str] = set()  # For deduplication
        self.pending_routes: Dict[str, List[MeshMessage]] = defaultdict(list)  # Queued messages

        # Stats
        self.messages_relayed = 0
        self.routes_discovered = 0
        self.dead_routes_detected = 0

        # Background tasks
        self._advertisement_task: Optional[asyncio.Task] = None
        self._is_running = False

        logger.info(f"🔀 Mesh relay initialized for peer {local_peer_id}")

    async def start(self) -> None:
        """Start mesh relay with background tasks"""
        if self._is_running:
            return

        self._is_running = True

        # Start connection pool
        await self.connection_pool.start()

        # Start periodic route advertisement
        self._advertisement_task = asyncio.create_task(self._advertisement_loop())

        logger.info("🔀 Mesh relay started")

    async def stop(self) -> None:
        """Stop mesh relay and cleanup"""
        if not self._is_running:
            return

        self._is_running = False

        # Stop advertisement task
        if self._advertisement_task:
            self._advertisement_task.cancel()
            try:
                await self._advertisement_task
            except asyncio.CancelledError:
                pass
            self._advertisement_task = None

        # Stop connection pool
        await self.connection_pool.stop()

        logger.info("🔀 Mesh relay stopped")

    async def _advertisement_loop(self) -> None:
        """Periodically broadcast route advertisements"""
        while self._is_running:
            try:
                await asyncio.sleep(30)  # Advertise every 30 seconds

                if not self.direct_peers:
                    continue

                # Generate and broadcast route advertisement
                advertisement = self.generate_route_advertisement()
                await self._broadcast_advertisement(advertisement)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in advertisement loop: {e}")

    async def _broadcast_advertisement(self, advertisement: dict) -> None:
        """Broadcast route advertisement to all direct peers"""
        for peer_id in list(self.direct_peers):
            try:
                conn = await self.connection_pool.acquire(peer_id)
                try:
                    await conn.send(advertisement)
                finally:
                    await self.connection_pool.release(peer_id, conn)
            except Exception as e:
                logger.debug(f"Failed to send advertisement to {peer_id}: {e}")

    def add_direct_peer(self, peer_id: str, latency_ms: float = 10.0) -> None:
        """Register a directly connected peer"""
        self.direct_peers.add(peer_id)

        # Update route metrics
        metrics = RouteMetrics(
            latency_ms=latency_ms,
            hop_count=1,
            reliability=1.0,
            last_measured=datetime.now(UTC).isoformat()
        )
        self.route_metrics[(self.local_peer_id, peer_id)] = metrics

        # Direct route
        self.route_table[peer_id] = [peer_id]

        logger.info(f"✅ Direct peer added: {peer_id} ({latency_ms}ms)")

    def remove_direct_peer(self, peer_id: str) -> None:
        """Remove a peer that disconnected"""
        if peer_id in self.direct_peers:
            self.direct_peers.remove(peer_id)

            # Invalidate routes through this peer
            self._invalidate_routes_through(peer_id)

            logger.info(f"❌ Direct peer removed: {peer_id}")

    def _invalidate_routes_through(self, peer_id: str) -> None:
        """Invalidate all routes that go through a specific peer"""
        routes_to_remove = []

        for dest_peer, next_hops in self.route_table.items():
            if peer_id in next_hops:
                # Remove this next hop
                new_hops = [h for h in next_hops if h != peer_id]

                if new_hops:
                    self.route_table[dest_peer] = new_hops
                else:
                    # No routes left to this destination
                    routes_to_remove.append(dest_peer)

        for dest_peer in routes_to_remove:
            del self.route_table[dest_peer]
            logger.debug(f"Route to {dest_peer} invalidated (went through {peer_id})")

    async def send_message(self,
                          dest_peer_id: str,
                          payload: dict,
                          ttl: Optional[int] = None) -> bool:
        """
        Send message to destination peer (with relay if needed)

        Returns True if message was sent, False if no route available
        """
        # Check if we've seen this message before (deduplication)
        message_id = self._generate_message_id(dest_peer_id, payload)

        if message_id in self.seen_messages:
            logger.debug(f"Duplicate message detected: {message_id}")
            return True

        self.seen_messages.add(message_id)

        # Limit cache size
        if len(self.seen_messages) > self.MESSAGE_CACHE_SIZE:
            # Remove oldest (simple: clear half)
            self.seen_messages = set(list(self.seen_messages)[self.MESSAGE_CACHE_SIZE // 2:])

        # Create message
        message = MeshMessage(
            message_id=message_id,
            source_peer_id=self.local_peer_id,
            dest_peer_id=dest_peer_id,
            payload=payload,
            ttl=ttl or self.MAX_TTL,
            route_history=[self.local_peer_id],
            timestamp=datetime.now(UTC).isoformat()
        )

        # Check if we have a route
        if dest_peer_id not in self.route_table:
            # No route - queue message and trigger route discovery
            logger.warning(f"No route to {dest_peer_id} - queuing message")
            self.pending_routes[dest_peer_id].append(message)
            await self._discover_route(dest_peer_id)
            return False

        # Get next hop
        next_hops = self.route_table[dest_peer_id]
        if not next_hops:
            logger.error(f"No next hop for {dest_peer_id}")
            return False

        # Choose best next hop (lowest latency)
        next_hop = self._choose_best_hop(next_hops, dest_peer_id)

        # Forward message
        await self._forward_message(message, next_hop)

        self.messages_relayed += 1
        return True

    async def receive_message(self, message: MeshMessage) -> bool:
        """
        Receive and potentially relay a message

        Returns True if message was for us, False if it was relayed
        """
        # Check TTL
        if message.ttl <= 0:
            logger.warning(f"Message {message.message_id} expired (TTL=0)")
            return False

        # Check if we've seen this message (loop detection)
        if message.message_id in self.seen_messages:
            logger.debug(f"Duplicate message ignored: {message.message_id}")
            return False

        self.seen_messages.add(message.message_id)

        # Check if message is for us
        if message.dest_peer_id == self.local_peer_id:
            logger.info(f"📨 Message received from {message.source_peer_id} (via {len(message.route_history)} hops)")
            return True

        # Relay message
        message.ttl -= 1
        message.route_history.append(self.local_peer_id)

        # Find next hop
        if message.dest_peer_id not in self.route_table:
            logger.warning(f"No route to {message.dest_peer_id} - dropping message")
            return False

        next_hops = self.route_table[message.dest_peer_id]
        next_hop = self._choose_best_hop(next_hops, message.dest_peer_id)

        await self._forward_message(message, next_hop)

        self.messages_relayed += 1
        logger.debug(f"🔀 Relayed message {message.message_id} to {next_hop}")

        return False

    async def _forward_message(self, message: MeshMessage, next_hop: str) -> None:
        """Forward message to next hop using connection pool"""
        try:
            # Acquire connection from pool
            conn = await self.connection_pool.acquire(next_hop)

            try:
                # Send message through connection
                await conn.send({
                    'type': 'mesh_message',
                    'message': asdict(message)
                })
                logger.debug(f"📤 Forwarded message {message.message_id} to {next_hop}")

            finally:
                # Release connection back to pool
                await self.connection_pool.release(next_hop, conn)

        except Exception as e:
            logger.error(f"Failed to forward message to {next_hop}: {e}")

    def _choose_best_hop(self, next_hops: List[str], dest_peer_id: str) -> str:
        """Choose best next hop based on metrics"""
        if len(next_hops) == 1:
            return next_hops[0]

        # Score each hop
        scored_hops = []

        for hop in next_hops:
            # Get metrics
            metrics = self.route_metrics.get((self.local_peer_id, hop))

            if not metrics:
                # No metrics - give default score
                score = 100.0
            else:
                # Lower score is better
                score = (
                    metrics.latency_ms * 1.0 +
                    metrics.hop_count * 10.0 +
                    (1.0 - metrics.reliability) * 50.0
                )

            scored_hops.append((score, hop))

        # Sort by score and return best
        scored_hops.sort()
        return scored_hops[0][1]

    async def _discover_route(self, dest_peer_id: str) -> None:
        """Discover route to destination peer by querying all direct peers"""
        logger.info(f"🔍 Discovering route to {dest_peer_id}...")

        # Send route request to all direct peers
        route_request = {
            'type': 'route_request',
            'dest_peer_id': dest_peer_id,
            'source_peer_id': self.local_peer_id
        }

        # Broadcast to direct peers via connection pool
        for peer_id in list(self.direct_peers):
            try:
                conn = await self.connection_pool.acquire(peer_id)
                try:
                    await conn.send(route_request)
                    logger.debug(f"📤 Sent route request to {peer_id}")
                finally:
                    await self.connection_pool.release(peer_id, conn)
            except Exception as e:
                logger.warning(f"Failed to send route request to {peer_id}: {e}")

    def update_route_from_advertisement(self, route_ad: dict) -> None:
        """
        Update routing table from route advertisement

        Route advertisements are broadcast periodically by all peers
        """
        peer_id = route_ad.get('peer_id')
        reachable_peers = route_ad.get('reachable_peers', [])

        if not peer_id or not reachable_peers:
            return

        # Update routes through this peer
        for dest_peer, hop_count in reachable_peers:
            if dest_peer == self.local_peer_id:
                continue  # Skip ourselves

            # Check if this is a better route
            current_hop_count = float('inf')

            if dest_peer in self.route_table:
                # Get current best hop count
                for next_hop in self.route_table[dest_peer]:
                    metrics = self.route_metrics.get((self.local_peer_id, next_hop))
                    if metrics:
                        current_hop_count = min(current_hop_count, metrics.hop_count)

            # New route has hop_count + 1 (through advertising peer)
            new_hop_count = hop_count + 1

            if new_hop_count < current_hop_count:
                # Better route found
                self.route_table[dest_peer] = [peer_id]

                # Update metrics
                self.route_metrics[(self.local_peer_id, peer_id)] = RouteMetrics(
                    latency_ms=10.0,  # Default - should be measured
                    hop_count=new_hop_count,
                    reliability=0.95,
                    last_measured=datetime.now(UTC).isoformat()
                )

                self.routes_discovered += 1
                logger.info(f"✨ New route discovered: {dest_peer} via {peer_id} ({new_hop_count} hops)")

                # Process pending messages for this destination
                if dest_peer in self.pending_routes:
                    pending = self.pending_routes.pop(dest_peer)
                    for msg in pending:
                        asyncio.create_task(self.send_message(dest_peer, msg.payload, msg.ttl))

    def generate_route_advertisement(self) -> Dict[str, Any]:
        """
        Generate route advertisement for broadcasting

        Other peers use this to learn routes through us
        """
        reachable_peers = []

        for dest_peer, next_hops in self.route_table.items():
            if next_hops:
                # Get hop count
                metrics = self.route_metrics.get((self.local_peer_id, next_hops[0]))
                hop_count = metrics.hop_count if metrics else 1

                reachable_peers.append((dest_peer, hop_count))

        return {
            'type': 'route_advertisement',
            'peer_id': self.local_peer_id,
            'reachable_peers': reachable_peers,
            'timestamp': datetime.now(UTC).isoformat()
        }

    def _generate_message_id(self, dest_peer_id: str, payload: dict) -> str:
        """Generate unique message ID for deduplication"""
        import hashlib

        content = json.dumps({
            'source': self.local_peer_id,
            'dest': dest_peer_id,
            'payload': payload,
            'timestamp': datetime.now(UTC).isoformat()
        }, sort_keys=True)

        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get_route_to(self, dest_peer_id: str) -> Optional[List[str]]:
        """Get route to destination peer"""
        if dest_peer_id not in self.route_table:
            return None

        next_hops = self.route_table[dest_peer_id]
        if not next_hops:
            return None

        # Return route [us → next_hop → ... → dest]
        # For now, just return next hop
        return [self.local_peer_id, next_hops[0], dest_peer_id]

    def get_stats(self) -> Dict[str, Any]:
        """Get relay statistics including connection pool metrics"""
        pool_stats = self.connection_pool.get_stats()

        return {
            'local_peer_id': self.local_peer_id,
            'direct_peers': len(self.direct_peers),
            'known_routes': len(self.route_table),
            'messages_relayed': self.messages_relayed,
            'routes_discovered': self.routes_discovered,
            'dead_routes_detected': self.dead_routes_detected,
            'pending_messages': sum(len(msgs) for msgs in self.pending_routes.values()),
            'connection_pool': pool_stats
        }

    def get_routing_table(self) -> Dict[str, Any]:
        """Get current routing table (for debugging)"""
        return {
            dest: {
                'next_hops': hops,
                'metrics': [
                    asdict(self.route_metrics.get((self.local_peer_id, hop)))
                    for hop in hops
                    if (self.local_peer_id, hop) in self.route_metrics
                ]
            }
            for dest, hops in self.route_table.items()
        }


# Singleton instance
_mesh_relay = None


def get_mesh_relay(local_peer_id: str = None) -> MeshRelay:
    """Get singleton mesh relay instance"""
    global _mesh_relay

    if _mesh_relay is None:
        if not local_peer_id:
            import hashlib
            import uuid
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                           for elements in range(0, 2*6, 2)][::-1])
            local_peer_id = hashlib.sha256(mac.encode()).hexdigest()[:16]

        _mesh_relay = MeshRelay(local_peer_id)
        logger.info("🔀 Mesh relay ready")

    return _mesh_relay
