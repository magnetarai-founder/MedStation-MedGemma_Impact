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

        # E2E Encryption service
        from e2e_encryption_service import get_e2e_service
        self.e2e_service = get_e2e_service()

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

        # E2E Encryption: Device keys table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_keys (
                device_id TEXT PRIMARY KEY,
                public_key BLOB NOT NULL,
                fingerprint BLOB NOT NULL,
                verify_key BLOB NOT NULL,
                created_at TEXT NOT NULL,
                last_used TEXT
            )
        """)

        # E2E Encryption: Peer keys table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS peer_keys (
                peer_device_id TEXT PRIMARY KEY,
                public_key BLOB NOT NULL,
                fingerprint BLOB NOT NULL,
                verify_key BLOB NOT NULL,
                verified BOOLEAN DEFAULT 0,
                verified_at TEXT,
                safety_number TEXT,
                first_seen TEXT NOT NULL,
                last_key_change TEXT
            )
        """)

        # E2E Encryption: Safety number changes tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS safety_number_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                peer_device_id TEXT NOT NULL,
                old_safety_number TEXT,
                new_safety_number TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                acknowledged BOOLEAN DEFAULT 0,
                acknowledged_at TEXT,
                FOREIGN KEY (peer_device_id) REFERENCES peer_keys(peer_device_id)
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_safety_changes_peer ON safety_number_changes(peer_device_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_safety_changes_ack ON safety_number_changes(acknowledged)")

        conn.commit()
        conn.close()
        logger.info("Database initialized")

    # ===== E2E Encryption Methods =====

    def init_device_keys(self, device_id: str, passphrase: str) -> Dict:
        """
        Initialize E2E encryption keys for this device

        Args:
            device_id: Unique device identifier
            passphrase: User's passphrase for Secure Enclave

        Returns:
            Dict with public_key and fingerprint
        """
        try:
            # Try to load existing keys first
            public_key, fingerprint = self.e2e_service.load_identity_keypair(device_id, passphrase)
            logger.info(f"Loaded existing E2E keys for device {device_id}")
        except:
            # Generate new keys if they don't exist
            public_key, fingerprint = self.e2e_service.generate_identity_keypair(device_id, passphrase)
            logger.info(f"Generated new E2E keys for device {device_id}")

        # Store in database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO device_keys
            (device_id, public_key, fingerprint, verify_key, created_at, last_used)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            device_id,
            public_key,
            fingerprint,
            bytes(self.e2e_service._signing_keypair.verify_key) if self.e2e_service._signing_keypair else b'',
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

        return {
            "public_key": public_key.hex(),
            "fingerprint": self.e2e_service.format_fingerprint(fingerprint),
            "device_id": device_id
        }

    def store_peer_key(self, peer_device_id: str, public_key: bytes, verify_key: bytes) -> Dict:
        """
        Store a peer's public key and generate safety number

        Args:
            peer_device_id: Peer's device identifier
            public_key: Peer's Curve25519 public key
            verify_key: Peer's Ed25519 verify key

        Returns:
            Dict with safety_number and fingerprint
        """
        fingerprint = self.e2e_service.generate_fingerprint(public_key)

        # Get our public key to generate safety number
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT public_key FROM device_keys LIMIT 1")
        row = cursor.fetchone()

        if not row:
            conn.close()
            raise RuntimeError("Device keys not initialized. Call init_device_keys() first.")

        local_public_key = row[0]
        safety_number = self.e2e_service.generate_safety_number(local_public_key, public_key)

        # Check if this is a key change
        cursor.execute("SELECT safety_number FROM peer_keys WHERE peer_device_id = ?", (peer_device_id,))
        existing = cursor.fetchone()

        if existing and existing[0] != safety_number:
            # Key change detected - log it
            cursor.execute("""
                INSERT INTO safety_number_changes
                (peer_device_id, old_safety_number, new_safety_number, changed_at)
                VALUES (?, ?, ?, ?)
            """, (peer_device_id, existing[0], safety_number, datetime.utcnow().isoformat()))
            logger.warning(f"⚠️ Safety number changed for peer {peer_device_id}")

        # Store/update peer key
        cursor.execute("""
            INSERT OR REPLACE INTO peer_keys
            (peer_device_id, public_key, fingerprint, verify_key, safety_number, first_seen, last_key_change)
            VALUES (?, ?, ?, ?, ?, COALESCE((SELECT first_seen FROM peer_keys WHERE peer_device_id = ?), ?), ?)
        """, (
            peer_device_id,
            public_key,
            fingerprint,
            verify_key,
            safety_number,
            peer_device_id,
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat() if existing else None
        ))

        conn.commit()
        conn.close()

        return {
            "safety_number": safety_number,
            "fingerprint": self.e2e_service.format_fingerprint(fingerprint),
            "key_changed": bool(existing)
        }

    def verify_peer_fingerprint(self, peer_device_id: str) -> bool:
        """
        Mark a peer's fingerprint as verified

        Args:
            peer_device_id: Peer's device identifier

        Returns:
            True if marked verified
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE peer_keys
            SET verified = 1, verified_at = ?
            WHERE peer_device_id = ?
        """, (datetime.utcnow().isoformat(), peer_device_id))

        conn.commit()
        conn.close()

        logger.info(f"✓ Verified fingerprint for peer {peer_device_id}")
        return True

    def get_unacknowledged_safety_changes(self) -> List[Dict]:
        """
        Get list of unacknowledged safety number changes (for yellow warning UI)

        Returns:
            List of safety number changes that need user acknowledgment
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                sc.id,
                sc.peer_device_id,
                pk.public_key,
                sc.old_safety_number,
                sc.new_safety_number,
                sc.changed_at,
                p.display_name
            FROM safety_number_changes sc
            JOIN peer_keys pk ON sc.peer_device_id = pk.peer_device_id
            LEFT JOIN peers p ON pk.peer_device_id = p.peer_id
            WHERE sc.acknowledged = 0
            ORDER BY sc.changed_at DESC
        """)

        changes = []
        for row in cursor.fetchall():
            changes.append({
                "id": row[0],
                "peer_device_id": row[1],
                "peer_name": row[6] or row[1],
                "old_safety_number": row[3],
                "new_safety_number": row[4],
                "changed_at": row[5]
            })

        conn.close()
        return changes

    def acknowledge_safety_change(self, change_id: int) -> bool:
        """
        Mark a safety number change as acknowledged

        Args:
            change_id: ID of the safety_number_changes record

        Returns:
            True if acknowledged
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE safety_number_changes
            SET acknowledged = 1, acknowledged_at = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), change_id))

        conn.commit()
        conn.close()

        return True

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

    async def close_all_connections(self):
        """Emergency: Close all P2P connections immediately (for panic mode)"""
        if not self.host:
            logger.debug("No P2P host active - skipping connection close")
            return

        try:
            # Close all active streams
            network = self.host.get_network()
            if network:
                # Get all connected peers
                connected_peers = list(network.connections.keys()) if hasattr(network, 'connections') else []

                for peer_id in connected_peers:
                    try:
                        # Close connection to each peer
                        await network.close_peer(peer_id)
                        logger.debug(f"Closed connection to peer: {peer_id}")
                    except Exception as e:
                        logger.debug(f"Error closing connection to {peer_id}: {e}")

            # Clear in-memory state
            self.discovered_peers.clear()
            self.active_channels.clear()

            logger.info("✓ All P2P connections closed (panic mode)")
        except Exception as e:
            logger.error(f"Error closing P2P connections: {e}")
            raise

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
        """Monitor for newly discovered peers and handle reconnections"""
        seen_peers = set()
        last_peer_count = 0

        while self.is_running:
            try:
                # Get currently connected peers from the peerstore
                peerstore = self.host.get_network().peerstore
                peer_ids = peerstore.peer_ids()
                current_peer_count = len(peer_ids)

                # Detect peer loss (network interruption)
                if current_peer_count < last_peer_count:
                    lost_count = last_peer_count - current_peer_count
                    logger.warning(f"⚠️ Lost {lost_count} peer(s) - attempting auto-reconnect...")

                    # Trigger reconnection for known peers
                    await self._auto_reconnect_lost_peers(peer_ids)

                last_peer_count = current_peer_count

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
                # On error, try to restart host connection
                if self.is_running:
                    logger.info("Attempting to recover from peer discovery error...")
                    await asyncio.sleep(10)

    async def _auto_reconnect_lost_peers(self, current_peer_ids):
        """
        Auto-reconnect to previously known peers that were lost

        Implements exponential backoff retry (max 3 attempts)
        """
        try:
            # Get all known peers from database
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT peer_id, display_name FROM peers WHERE status = 'online'")
            known_peers = cursor.fetchall()
            conn.close()

            current_peer_ids_str = {pid.pretty() for pid in current_peer_ids}

            for peer_id_str, display_name in known_peers:
                if peer_id_str not in current_peer_ids_str:
                    logger.info(f"🔄 Attempting to reconnect to {display_name or peer_id_str[:8]}...")

                    # Retry connection with exponential backoff
                    for attempt in range(1, 4):  # 3 attempts max
                        try:
                            # Try to reconnect (libp2p will use cached multiaddrs)
                            await self.host.connect(peer_id_str)
                            logger.info(f"✓ Reconnected to {display_name or peer_id_str[:8]}")
                            break  # Success

                        except Exception as e:
                            wait_time = 2 ** attempt  # 2s, 4s, 8s
                            if attempt < 3:
                                logger.debug(f"Reconnect attempt {attempt} failed, retrying in {wait_time}s...")
                                await asyncio.sleep(wait_time)
                            else:
                                logger.warning(f"Failed to reconnect to {peer_id_str[:8]} after 3 attempts")
                                # Mark peer as offline
                                await self._mark_peer_offline(peer_id_str)

        except Exception as e:
            logger.error(f"Error in auto-reconnect: {e}")

    async def _mark_peer_offline(self, peer_id: str):
        """Mark a peer as offline in the database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE peers SET status = 'offline', last_seen = ? WHERE peer_id = ?",
                (datetime.utcnow().isoformat(), peer_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to mark peer offline: {e}")

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
                # Decrypt message content if encrypted
                if message_data.get("encrypted", False):
                    try:
                        encrypted_content = bytes.fromhex(message_data["content"])
                        decrypted_content = self.e2e_service.decrypt_message(encrypted_content)
                        message_data["content"] = decrypted_content
                        logger.debug(f"🔓 Decrypted message from {message_data.get('sender_id', 'unknown')[:8]}")
                    except Exception as e:
                        logger.error(f"Failed to decrypt message: {e}")
                        message_data["content"] = "[⚠️ Failed to decrypt message]"

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

            # Convert message to dict
            message_dict = message.dict()

            # Encrypt message content if E2E keys exist
            try:
                # Get peer's public key from database
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                cursor.execute("SELECT public_key FROM peer_keys WHERE peer_device_id = ?", (peer_id_str,))
                row = cursor.fetchone()
                conn.close()

                if row and row[0]:
                    # Encrypt the content
                    recipient_public_key = row[0]
                    encrypted_content = self.e2e_service.encrypt_message(recipient_public_key, message.content)
                    message_dict["content"] = encrypted_content.hex()
                    message_dict["encrypted"] = True
                    logger.debug(f"🔒 Encrypted message for {peer_id_str[:8]}")
                else:
                    logger.warning(f"No E2E keys for peer {peer_id_str[:8]}, sending unencrypted")
                    message_dict["encrypted"] = False
            except Exception as e:
                logger.warning(f"E2E encryption failed for {peer_id_str[:8]}: {e}, sending unencrypted")
                message_dict["encrypted"] = False

            # Send message
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
