"""
Mesh Relay Connection Management

MeshConnection: Represents a connection to a peer
MeshConnectionPool: Connection pool for efficient peer communication
"""

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Dict, Optional, Any

# Try to import websockets for actual connections
try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketClientProtocol = None

# Try to import nacl for signed handshakes
try:
    import nacl.signing
    NACL_AVAILABLE = True
except ImportError:
    NACL_AVAILABLE = False

from api.mesh.security import SignedHandshake

logger = logging.getLogger(__name__)


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
            logger.debug(f"Sent {len(message)} bytes to {self.peer_id}")
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
                logger.debug(f"Closed connection to {self.peer_id}")
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

        logger.info(f"Connection pool initialized (max_size={max_size}, idle_timeout={idle_timeout}s, signed={signing_key is not None})")

    async def start(self) -> None:
        """Start background cleanup task"""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Connection pool cleanup task started")

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
        logger.info("Connection pool stopped")

    async def acquire(self, peer_id: str) -> MeshConnection:
        """Get connection from pool or create new one"""
        # Try to get from pool
        if peer_id in self._pool and self._pool[peer_id]:
            conn = self._pool[peer_id].popleft()

            # Check if connection is still healthy
            if await self._is_healthy(conn):
                self._active[peer_id] = self._active.get(peer_id, 0) + 1
                self._connections_reused += 1
                logger.debug(f"Reusing connection to {peer_id}")
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
        logger.debug(f"Created new connection to {peer_id}")
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
            logger.debug(f"Returned connection to {peer_id} to pool")
        else:
            # Pool full, close connection
            await conn.close()
            self._total_connections -= 1
            logger.debug(f"Pool full, closed connection to {peer_id}")

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
                logger.debug(f"Sending signed handshake to {peer_id}")
            else:
                # Fallback to unsigned handshake (legacy compatibility)
                logger.warning(f"Sending unsigned handshake to {peer_id} - consider adding signing key")
                handshake = {
                    'type': 'mesh_handshake',
                    'peer_id': discovery.peer_id,
                    'display_name': discovery.display_name,
                    'capabilities': discovery.capabilities
                }
            await ws_connection.send(json.dumps(handshake))

            logger.info(f"Connected to peer {peer_id} at {ws_url}")

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
            logger.info(f"Cleaned up {cleaned} stale connections")

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
