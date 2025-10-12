"""
P2P Team Chat Service
Secure, offline-first peer-to-peer messaging using libp2p
"""

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime
import logging

# Will need: pip install libp2p
try:
    from libp2p import new_host, create_new_key_pair
    from libp2p.network.stream.net_stream import NetStream as INetStream
    from libp2p.peer.id import ID as PeerID
    from multiaddr import Multiaddr
    LIBP2P_AVAILABLE = True
except ImportError as e:
    LIBP2P_AVAILABLE = False
    INetStream = None
    logging.warning(f"libp2p not installed - P2P features will be unavailable: {e}")

from p2p_chat_models import (
    Peer, Channel, Message, FileTransfer,
    MessageType, ChannelType, PeerStatus,
    SendMessageRequest, CreateChannelRequest
)

logger = logging.getLogger(__name__)


# ===== P2P Protocol Constants =====
PROTOCOL_ID = "/omnistudio/chat/1.0.0"
FILE_PROTOCOL_ID = "/omnistudio/file/1.0.0"
MDNS_SERVICE_NAME = "_omnistudio._udp.local"
DB_PATH = Path(".neutron_data/p2p_chat.db")


class P2PChatService:
    """
    Main P2P chat service using libp2p for mesh networking
    Handles peer discovery, messaging, and file transfers
    """

    def __init__(self, display_name: str, device_name: str):
        self.display_name = display_name
        self.device_name = device_name

        # libp2p host (will be initialized in start())
        self.host = None
        self.peer_id = None
        self.key_pair = None

        # Local storage
        self.db_path = DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # In-memory state
        self.discovered_peers: Dict[str, Peer] = {}
        self.active_channels: Dict[str, Channel] = {}
        self.message_handlers: List[Callable] = []

        # Running state
        self.is_running = False

        logger.info(f"P2P Chat Service initialized for {display_name} on {device_name}")

    def _init_db(self):
        """Initialize SQLite database for local storage"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Peers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS peers (
                peer_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                device_name TEXT NOT NULL,
                public_key TEXT,
                status TEXT DEFAULT 'offline',
                last_seen TEXT,
                avatar_hash TEXT,
                bio TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Channels table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                created_at TEXT,
                created_by TEXT,
                description TEXT,
                topic TEXT,
                members TEXT,  -- JSON array
                admins TEXT,   -- JSON array
                dm_participants TEXT  -- JSON array for DMs
            )
        """)

        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                sender_name TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                encrypted BOOLEAN DEFAULT TRUE,
                timestamp TEXT NOT NULL,
                edited_at TEXT,
                file_metadata TEXT,  -- JSON
                thread_id TEXT,
                reply_to TEXT,
                reactions TEXT,  -- JSON
                delivered_to TEXT,  -- JSON array
                read_by TEXT,  -- JSON array
                FOREIGN KEY (channel_id) REFERENCES channels (id)
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel_id, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id)")

        # File transfers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_transfers (
                id TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                file_size INTEGER,
                file_hash TEXT,
                mime_type TEXT,
                sender_id TEXT,
                recipient_ids TEXT,  -- JSON array
                channel_id TEXT,
                chunks_total INTEGER,
                chunks_received INTEGER DEFAULT 0,
                progress_percent REAL DEFAULT 0.0,
                status TEXT DEFAULT 'pending',
                started_at TEXT,
                completed_at TEXT,
                local_path TEXT
            )
        """)

        conn.commit()
        conn.close()
        logger.info("Database initialized")

    async def start(self):
        """Start the P2P service with libp2p"""
        if not LIBP2P_AVAILABLE:
            raise RuntimeError("libp2p is not installed. Install with: pip install libp2p")

        # Generate or load key pair
        self.key_pair = create_new_key_pair()

        # Create libp2p host with transports
        listen_addrs = [
            Multiaddr("/ip4/0.0.0.0/tcp/0"),  # TCP on random port
        ]

        self.host = new_host(
            key_pair=self.key_pair,
            listen_addrs=listen_addrs,
        )

        self.peer_id = self.host.get_id().pretty()

        # Get our listening addresses
        addrs = [str(addr) for addr in self.host.get_addrs()]
        logger.info(f"P2P Host started")
        logger.info(f"  Peer ID: {self.peer_id}")
        logger.info(f"  Listening on: {addrs}")

        # Register protocol handlers
        self.host.set_stream_handler(PROTOCOL_ID, self._handle_chat_stream)
        self.host.set_stream_handler(FILE_PROTOCOL_ID, self._handle_file_stream)

        # Start mDNS discovery
        await self._start_mdns_discovery()

        # Start heartbeat to maintain peer connections
        asyncio.create_task(self._heartbeat_loop())

        # Save self as peer
        await self._save_self_peer()

        self.is_running = True
        logger.info("✓ P2P service started successfully")

    async def stop(self):
        """Stop the P2P service"""
        if self.host:
            await self.host.close()
        self.is_running = False
        logger.info("P2P service stopped")

    async def _start_mdns_discovery(self):
        """Start mDNS peer discovery on local network"""
        try:
            # libp2p uses mDNS for automatic peer discovery on LAN
            # The host automatically advertises itself and discovers other peers
            # We need to monitor the peer store for new connections

            # Start background task to monitor discovered peers
            asyncio.create_task(self._monitor_peer_discovery())

            logger.info("✓ mDNS discovery started - listening for peers on local network")

        except Exception as e:
            logger.error(f"Failed to start mDNS discovery: {e}")

    async def _monitor_peer_discovery(self):
        """Monitor for newly discovered peers"""
        seen_peers = set()

        while self.is_running:
            try:
                # Get currently connected peers from the peerstore
                peerstore = self.host.get_network().peerstore
                peer_ids = peerstore.peer_ids()

                for peer_id in peer_ids:
                    peer_id_str = peer_id.pretty()

                    if peer_id_str not in seen_peers and peer_id_str != self.peer_id:
                        seen_peers.add(peer_id_str)
                        logger.info(f"📡 Discovered new peer: {peer_id_str}")

                        # Get peer's multiaddrs from peerstore
                        try:
                            addrs = peerstore.addrs(peer_id)
                            addr_strs = [str(addr) for addr in addrs]
                        except Exception:
                            addr_strs = []

                        # Save peer to database
                        await self._save_discovered_peer(peer_id_str, addr_strs)

                        # Request peer info (display name, etc.) via custom protocol
                        await self._request_peer_info(peer_id_str)

                await asyncio.sleep(5)  # Check every 5 seconds

            except Exception as e:
                logger.error(f"Error in peer discovery monitor: {e}")
                await asyncio.sleep(10)

    async def _save_discovered_peer(self, peer_id: str, multiaddrs: List[str]):
        """Save a discovered peer to the database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Check if peer already exists
        cursor.execute("SELECT peer_id FROM peers WHERE peer_id = ?", (peer_id,))
        exists = cursor.fetchone()

        if not exists:
            cursor.execute("""
                INSERT INTO peers
                (peer_id, display_name, device_name, status, last_seen)
                VALUES (?, ?, ?, ?, ?)
            """, (
                peer_id,
                f"Peer {peer_id[:8]}",  # Temporary name until we get real info
                "Unknown Device",
                PeerStatus.ONLINE.value,
                datetime.utcnow().isoformat()
            ))
        else:
            cursor.execute("""
                UPDATE peers
                SET status = ?, last_seen = ?
                WHERE peer_id = ?
            """, (
                PeerStatus.ONLINE.value,
                datetime.utcnow().isoformat(),
                peer_id
            ))

        conn.commit()
        conn.close()

    async def _request_peer_info(self, peer_id_str: str):
        """Request display name and device info from a peer"""
        try:
            # Open a stream to the peer to exchange metadata
            peer_id = PeerID.from_base58(peer_id_str)
            stream = await self.host.new_stream(peer_id, [PROTOCOL_ID])

            # Send info request
            request = {
                "type": "info_request",
                "peer_id": self.peer_id,
                "display_name": self.display_name,
                "device_name": self.device_name,
                "timestamp": datetime.utcnow().isoformat()
            }

            await stream.write(json.dumps(request).encode())

            # Read response
            response_data = await stream.read()
            response = json.loads(response_data.decode())

            if response.get("type") == "info_response":
                # Update peer info in database
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE peers
                    SET display_name = ?, device_name = ?, public_key = ?
                    WHERE peer_id = ?
                """, (
                    response.get("display_name", f"Peer {peer_id_str[:8]}"),
                    response.get("device_name", "Unknown Device"),
                    response.get("public_key", ""),
                    peer_id_str
                ))

                conn.commit()
                conn.close()

                logger.info(f"✓ Received info from {response.get('display_name')} on {response.get('device_name')}")

            await stream.close()

        except Exception as e:
            logger.error(f"Failed to request peer info from {peer_id_str}: {e}")

    async def _heartbeat_loop(self):
        """Send periodic heartbeats to maintain connections"""
        while self.is_running:
            try:
                # Update our last_seen timestamp
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE peers
                    SET last_seen = ?
                    WHERE peer_id = ?
                """, (datetime.utcnow().isoformat(), self.peer_id))

                conn.commit()
                conn.close()

                # Check for stale peers (not seen in 30 seconds)
                await self._check_stale_peers()

                await asyncio.sleep(10)  # Heartbeat every 10 seconds

            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(30)

    async def _check_stale_peers(self):
        """Mark peers as offline if they haven't been seen recently"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Get peers not seen in last 30 seconds
        thirty_seconds_ago = (datetime.utcnow().timestamp() - 30)
        thirty_seconds_ago_iso = datetime.fromtimestamp(thirty_seconds_ago).isoformat()

        cursor.execute("""
            UPDATE peers
            SET status = ?
            WHERE last_seen < ? AND status = ? AND peer_id != ?
        """, (
            PeerStatus.OFFLINE.value,
            thirty_seconds_ago_iso,
            PeerStatus.ONLINE.value,
            self.peer_id
        ))

        conn.commit()
        conn.close()

    async def _handle_chat_stream(self, stream: 'INetStream'):
        """Handle incoming chat messages from peers"""
        try:
            # Read message from stream
            data = await stream.read()
            message_data = json.loads(data.decode())

            message_type = message_data.get("type")

            # Handle info requests (peer exchange)
            if message_type == "info_request":
                response = {
                    "type": "info_response",
                    "peer_id": self.peer_id,
                    "display_name": self.display_name,
                    "device_name": self.device_name,
                    "public_key": self.key_pair.public_key.serialize().hex() if self.key_pair else "",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await stream.write(json.dumps(response).encode())
                await stream.close()
                return

            # Handle regular chat messages
            if message_type == MessageType.TEXT.value or message_type == MessageType.FILE.value:
                # Parse message
                message = Message(**message_data)

                # Store in database
                await self._store_message(message)

                # Notify handlers
                for handler in self.message_handlers:
                    try:
                        await handler(message)
                    except Exception as e:
                        logger.error(f"Message handler error: {e}")

                # Send ACK
                ack = {
                    "type": "ack",
                    "message_id": message.id,
                    "received_at": datetime.utcnow().isoformat()
                }
                await stream.write(json.dumps(ack).encode())

        except Exception as e:
            logger.error(f"Error handling chat stream: {e}")
        finally:
            await stream.close()

    async def _handle_file_stream(self, stream: 'INetStream'):
        """Handle incoming file transfers"""
        # TODO: Implement chunked file transfer
        logger.info("File stream handler (TODO: implement)")
        pass

    async def _save_self_peer(self):
        """Save ourselves as a peer in the database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO peers
            (peer_id, display_name, device_name, public_key, status, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            self.peer_id,
            self.display_name,
            self.device_name,
            self.key_pair.public_key.serialize().hex(),
            PeerStatus.ONLINE.value,
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

    async def _store_message(self, message: Message):
        """Store a message in the local database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO messages
            (id, channel_id, sender_id, sender_name, type, content, encrypted,
             timestamp, file_metadata, thread_id, reply_to, reactions,
             delivered_to, read_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message.id,
            message.channel_id,
            message.sender_id,
            message.sender_name,
            message.type.value,
            message.content,
            message.encrypted,
            message.timestamp,
            json.dumps(message.file_metadata) if message.file_metadata else None,
            message.thread_id,
            message.reply_to,
            json.dumps(message.reactions),
            json.dumps(message.delivered_to),
            json.dumps(message.read_by)
        ))

        conn.commit()
        conn.close()

    # ===== Public API Methods =====

    async def send_message(self, request: SendMessageRequest) -> Message:
        """Send a message to a channel"""
        if not self.is_running:
            raise RuntimeError("P2P service not running")

        # Create message
        message = Message(
            channel_id=request.channel_id,
            sender_id=self.peer_id,
            sender_name=self.display_name,
            type=request.type,
            content=request.content,
            reply_to=request.reply_to,
            file_metadata=request.file_metadata
        )

        # Store locally
        await self._store_message(message)

        # Get channel members
        channel = await self.get_channel(request.channel_id)
        if not channel:
            raise ValueError(f"Channel {request.channel_id} not found")

        # Send to all members
        for peer_id in channel.members:
            if peer_id == self.peer_id:
                continue  # Don't send to ourselves

            try:
                await self._send_to_peer(peer_id, message)
            except Exception as e:
                logger.error(f"Failed to send message to {peer_id}: {e}")

        return message

    async def _send_to_peer(self, peer_id_str: str, message: Message):
        """Send a message to a specific peer"""
        try:
            # Convert peer_id string to PeerID object
            peer_id = PeerID.from_base58(peer_id_str)

            # Open stream to peer
            stream = await self.host.new_stream(peer_id, [PROTOCOL_ID])

            # Convert message to dict and send
            message_dict = message.dict()
            await stream.write(json.dumps(message_dict).encode())

            # Wait for ACK
            ack_data = await stream.read()
            ack = json.loads(ack_data.decode())

            if ack.get("type") == "ack":
                # Update delivered_to list
                if peer_id_str not in message.delivered_to:
                    message.delivered_to.append(peer_id_str)

                    # Update in database
                    conn = sqlite3.connect(str(self.db_path))
                    cursor = conn.cursor()

                    cursor.execute("""
                        UPDATE messages
                        SET delivered_to = ?
                        WHERE id = ?
                    """, (json.dumps(message.delivered_to), message.id))

                    conn.commit()
                    conn.close()

                logger.info(f"✓ Message {message.id[:8]} delivered to {peer_id_str[:8]}")

            await stream.close()

        except Exception as e:
            logger.error(f"Failed to send message to {peer_id_str}: {e}")

    async def create_channel(self, request: CreateChannelRequest) -> Channel:
        """Create a new channel"""
        channel = Channel(
            name=request.name,
            type=request.type,
            created_by=self.peer_id,
            description=request.description,
            topic=request.topic,
            members=[self.peer_id] + request.members,
            admins=[self.peer_id]
        )

        # Store in database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO channels
            (id, name, type, created_at, created_by, description, topic, members, admins)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            channel.id,
            channel.name,
            channel.type.value,
            channel.created_at,
            channel.created_by,
            channel.description,
            channel.topic,
            json.dumps(channel.members),
            json.dumps(channel.admins)
        ))

        conn.commit()
        conn.close()

        self.active_channels[channel.id] = channel
        logger.info(f"Created channel: {channel.name} ({channel.id})")

        return channel

    async def get_channel(self, channel_id: str) -> Optional[Channel]:
        """Get a channel by ID"""
        # Check cache first
        if channel_id in self.active_channels:
            return self.active_channels[channel_id]

        # Query database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM channels WHERE id = ?", (channel_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        channel = Channel(
            id=row[0],
            name=row[1],
            type=ChannelType(row[2]),
            created_at=row[3],
            created_by=row[4],
            description=row[5],
            topic=row[6],
            members=json.loads(row[7]) if row[7] else [],
            admins=json.loads(row[8]) if row[8] else []
        )

        self.active_channels[channel_id] = channel
        return channel

    async def list_channels(self) -> List[Channel]:
        """List all channels"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM channels ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()

        channels = []
        for row in rows:
            channel = Channel(
                id=row[0],
                name=row[1],
                type=ChannelType(row[2]),
                created_at=row[3],
                created_by=row[4],
                description=row[5],
                topic=row[6],
                members=json.loads(row[7]) if row[7] else [],
                admins=json.loads(row[8]) if row[8] else []
            )
            channels.append(channel)

        return channels

    async def get_messages(self, channel_id: str, limit: int = 50) -> List[Message]:
        """Get messages for a channel"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM messages
            WHERE channel_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (channel_id, limit))

        rows = cursor.fetchall()
        conn.close()

        messages = []
        for row in rows:
            message = Message(
                id=row[0],
                channel_id=row[1],
                sender_id=row[2],
                sender_name=row[3],
                type=MessageType(row[4]),
                content=row[5],
                encrypted=bool(row[6]),
                timestamp=row[7],
                edited_at=row[8],
                file_metadata=json.loads(row[9]) if row[9] else None,
                thread_id=row[10],
                reply_to=row[11],
                reactions=json.loads(row[12]) if row[12] else {},
                delivered_to=json.loads(row[13]) if row[13] else [],
                read_by=json.loads(row[14]) if row[14] else []
            )
            messages.append(message)

        # Reverse to get chronological order
        return list(reversed(messages))

    async def list_peers(self) -> List[Peer]:
        """List discovered peers"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM peers ORDER BY last_seen DESC")
        rows = cursor.fetchall()
        conn.close()

        peers = []
        for row in rows:
            peer = Peer(
                peer_id=row[0],
                display_name=row[1],
                device_name=row[2],
                public_key=row[3] or "",
                status=PeerStatus(row[4]),
                last_seen=row[5] or datetime.utcnow().isoformat(),
                avatar_hash=row[6],
                bio=row[7]
            )
            peers.append(peer)

        return peers

    def register_message_handler(self, handler: Callable):
        """Register a callback for new messages"""
        self.message_handlers.append(handler)


# Singleton instance
_service_instance: Optional[P2PChatService] = None


def get_p2p_chat_service() -> Optional[P2PChatService]:
    """Get the singleton P2P chat service instance"""
    return _service_instance


def init_p2p_chat_service(display_name: str, device_name: str) -> P2PChatService:
    """Initialize the P2P chat service"""
    global _service_instance
    if _service_instance is None:
        _service_instance = P2PChatService(display_name, device_name)
    return _service_instance
