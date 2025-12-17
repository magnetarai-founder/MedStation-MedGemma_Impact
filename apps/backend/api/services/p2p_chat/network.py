"""
P2P Chat Service - libp2p Networking Layer

Handles:
- libp2p host creation and lifecycle
- mDNS peer discovery
- Stream handlers for chat and file protocols
- Peer connection management and auto-reconnection
- Heartbeat and stale peer detection
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable, TYPE_CHECKING
from datetime import datetime, UTC

# Conditional libp2p import
try:
    from libp2p import new_host, create_new_key_pair
    from libp2p.network.stream.net_stream import NetStream as INetStream
    from libp2p.peer.id import ID as PeerID
    from multiaddr import Multiaddr
    LIBP2P_AVAILABLE = True
except ImportError as e:
    LIBP2P_AVAILABLE = False
    INetStream = None
    PeerID = None
    Multiaddr = None
    logging.warning(f"libp2p not installed - P2P features will be unavailable: {e}")

if TYPE_CHECKING:
    from .service import P2PChatService

try:
    from api.p2p_chat_models import Message, MessageType, PeerStatus
except ImportError:
    from p2p_chat_models import Message, MessageType, PeerStatus

from .types import PROTOCOL_ID, FILE_PROTOCOL_ID
from . import storage

logger = logging.getLogger(__name__)


async def start_network(service: 'P2PChatService') -> None:
    """
    Start the P2P network with libp2p.

    Args:
        service: P2PChatService instance

    Raises:
        RuntimeError: If libp2p is not available
    """
    if not LIBP2P_AVAILABLE:
        raise RuntimeError("libp2p is not installed. Install with: pip install libp2p")

    # Generate or load key pair
    service.key_pair = create_new_key_pair()

    # Create libp2p host with transports
    listen_addrs = [
        Multiaddr("/ip4/0.0.0.0/tcp/0"),  # TCP on random port
    ]

    service.host = new_host(
        key_pair=service.key_pair,
        listen_addrs=listen_addrs,
    )

    service.peer_id = service.host.get_id().pretty()

    # Get our listening addresses
    addrs = [str(addr) for addr in service.host.get_addrs()]
    logger.info(f"P2P Host started")
    logger.info(f"  Peer ID: {service.peer_id}")
    logger.info(f"  Listening on: {addrs}")

    # Register protocol handlers
    service.host.set_stream_handler(PROTOCOL_ID, lambda s: _handle_chat_stream(service, s))
    service.host.set_stream_handler(FILE_PROTOCOL_ID, lambda s: _handle_file_stream(service, s))

    # Start mDNS discovery
    await _start_mdns_discovery(service)

    # Start heartbeat to maintain peer connections
    asyncio.create_task(_heartbeat_loop(service))

    # Save self as peer
    await _save_self_peer(service)

    service.is_running = True
    logger.info("✓ P2P service started successfully")


async def stop_network(service: 'P2PChatService') -> None:
    """
    Stop the P2P network.

    Args:
        service: P2PChatService instance
    """
    if service.host:
        await service.host.close()
    service.is_running = False
    logger.info("P2P service stopped")


async def close_all_connections(service: 'P2PChatService') -> None:
    """
    Emergency: Close all P2P connections immediately (for panic mode).

    Args:
        service: P2PChatService instance
    """
    if not service.host:
        logger.debug("No P2P host active - skipping connection close")
        return

    try:
        # Close all active streams
        network = service.host.get_network()
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
        service.discovered_peers.clear()
        service.active_channels.clear()

        logger.info("✓ All P2P connections closed (panic mode)")
    except Exception as e:
        logger.error(f"Error closing P2P connections: {e}")
        raise


# ===== Internal Network Functions =====

async def _start_mdns_discovery(service: 'P2PChatService') -> None:
    """Start mDNS peer discovery on local network."""
    try:
        # libp2p uses mDNS for automatic peer discovery on LAN
        # The host automatically advertises itself and discovers other peers
        # We need to monitor the peer store for new connections

        # Start background task to monitor discovered peers
        asyncio.create_task(_monitor_peer_discovery(service))

        logger.info("✓ mDNS discovery started - listening for peers on local network")

    except Exception as e:
        logger.error(f"Failed to start mDNS discovery: {e}")


async def _monitor_peer_discovery(service: 'P2PChatService') -> None:
    """Monitor for newly discovered peers and handle reconnections."""
    seen_peers = set()
    last_peer_count = 0

    while service.is_running:
        try:
            # Get currently connected peers from the peerstore
            peerstore = service.host.get_network().peerstore
            peer_ids = peerstore.peer_ids()
            current_peer_count = len(peer_ids)

            # Detect peer loss (network interruption)
            if current_peer_count < last_peer_count:
                lost_count = last_peer_count - current_peer_count
                logger.warning(f"⚠️ Lost {lost_count} peer(s) - attempting auto-reconnect...")

                # Trigger reconnection for known peers
                await _auto_reconnect_lost_peers(service, peer_ids)

            last_peer_count = current_peer_count

            for peer_id in peer_ids:
                peer_id_str = peer_id.pretty()

                if peer_id_str not in seen_peers and peer_id_str != service.peer_id:
                    seen_peers.add(peer_id_str)
                    logger.info(f"📡 Discovered new peer: {peer_id_str}")

                    # Get peer's multiaddrs from peerstore
                    try:
                        addrs = peerstore.addrs(peer_id)
                        addr_strs = [str(addr) for addr in addrs]
                    except Exception:
                        addr_strs = []

                    # Save peer to database
                    await _save_discovered_peer(service, peer_id_str, addr_strs)

                    # Request peer info (display name, etc.) via custom protocol
                    await _request_peer_info(service, peer_id_str)

            await asyncio.sleep(5)  # Check every 5 seconds

        except Exception as e:
            logger.error(f"Error in peer discovery monitor: {e}")
            # On error, try to restart host connection
            if service.is_running:
                logger.info("Attempting to recover from peer discovery error...")
                await asyncio.sleep(10)


async def _auto_reconnect_lost_peers(service: 'P2PChatService', current_peer_ids) -> None:
    """
    Auto-reconnect to previously known peers that were lost.

    Implements exponential backoff retry (max 3 attempts).

    Args:
        service: P2PChatService instance
        current_peer_ids: List of currently connected peer IDs
    """
    try:
        # Get all known peers from database
        import sqlite3
        conn = sqlite3.connect(str(service.db_path))
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
                        await service.host.connect(peer_id_str)
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
                            storage.update_peer_status(service.db_path, peer_id_str, PeerStatus.OFFLINE.value)

    except Exception as e:
        logger.error(f"Error in auto-reconnect: {e}")


async def _save_discovered_peer(service: 'P2PChatService', peer_id: str, multiaddrs: List[str]) -> None:
    """Save a discovered peer to the database."""
    import sqlite3
    conn = sqlite3.connect(str(service.db_path))
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
            datetime.now(UTC).isoformat()
        ))
    else:
        cursor.execute("""
            UPDATE peers
            SET status = ?, last_seen = ?
            WHERE peer_id = ?
        """, (
            PeerStatus.ONLINE.value,
            datetime.now(UTC).isoformat(),
            peer_id
        ))

    conn.commit()
    conn.close()


async def _request_peer_info(service: 'P2PChatService', peer_id_str: str) -> None:
    """Request display name and device info from a peer."""
    try:
        # Open a stream to the peer to exchange metadata
        peer_id = PeerID.from_base58(peer_id_str)
        stream = await service.host.new_stream(peer_id, [PROTOCOL_ID])

        # Send info request
        request = {
            "type": "info_request",
            "peer_id": service.peer_id,
            "display_name": service.display_name,
            "device_name": service.device_name,
            "timestamp": datetime.now(UTC).isoformat()
        }

        await stream.write(json.dumps(request).encode())

        # Read response
        response_data = await stream.read()
        response = json.loads(response_data.decode())

        if response.get("type") == "info_response":
            # Update peer info in database
            import sqlite3
            conn = sqlite3.connect(str(service.db_path))
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


async def _heartbeat_loop(service: 'P2PChatService') -> None:
    """Send periodic heartbeats to maintain connections."""
    while service.is_running:
        try:
            # Update our last_seen timestamp
            import sqlite3
            conn = sqlite3.connect(str(service.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE peers
                SET last_seen = ?
                WHERE peer_id = ?
            """, (datetime.now(UTC).isoformat(), service.peer_id))

            conn.commit()
            conn.close()

            # Check for stale peers (not seen in 30 seconds)
            await _check_stale_peers(service)

            await asyncio.sleep(10)  # Heartbeat every 10 seconds

        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            await asyncio.sleep(30)


async def _check_stale_peers(service: 'P2PChatService') -> None:
    """Mark peers as offline if they haven't been seen recently."""
    import sqlite3
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    # Get peers not seen in last 30 seconds
    thirty_seconds_ago = (datetime.now(UTC).timestamp() - 30)
    thirty_seconds_ago_iso = datetime.fromtimestamp(thirty_seconds_ago).isoformat()

    cursor.execute("""
        UPDATE peers
        SET status = ?
        WHERE last_seen < ? AND status = ? AND peer_id != ?
    """, (
        PeerStatus.OFFLINE.value,
        thirty_seconds_ago_iso,
        PeerStatus.ONLINE.value,
        service.peer_id
    ))

    conn.commit()
    conn.close()


async def _save_self_peer(service: 'P2PChatService') -> None:
    """Save ourselves as a peer in the database."""
    import sqlite3
    conn = sqlite3.connect(str(service.db_path))
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO peers
        (peer_id, display_name, device_name, public_key, status, last_seen)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        service.peer_id,
        service.display_name,
        service.device_name,
        service.key_pair.public_key.serialize().hex(),
        PeerStatus.ONLINE.value,
        datetime.now(UTC).isoformat()
    ))

    conn.commit()
    conn.close()


# ===== Stream Handlers =====

async def _handle_chat_stream(service: 'P2PChatService', stream: 'INetStream') -> None:
    """Handle incoming chat messages from peers."""
    try:
        # Read message from stream
        data = await stream.read()
        message_data = json.loads(data.decode())

        message_type = message_data.get("type")

        # Handle info requests (peer exchange)
        if message_type == "info_request":
            response = {
                "type": "info_response",
                "peer_id": service.peer_id,
                "display_name": service.display_name,
                "device_name": service.device_name,
                "public_key": service.key_pair.public_key.serialize().hex() if service.key_pair else "",
                "timestamp": datetime.now(UTC).isoformat()
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
                    decrypted_content = service.e2e_service.decrypt_message(encrypted_content)
                    message_data["content"] = decrypted_content
                    logger.debug(f"🔓 Decrypted message from {message_data.get('sender_id', 'unknown')[:8]}")
                except Exception as e:
                    logger.error(f"Failed to decrypt message: {e}")
                    message_data["content"] = "[⚠️ Failed to decrypt message]"

            # Parse message
            message = Message(**message_data)

            # Store in database
            storage.save_message(
                service.db_path,
                message.id,
                message.channel_id,
                message.sender_id,
                message.sender_name,
                message.type.value,
                message.content,
                message.timestamp,
                message.encrypted,
                message.file_metadata,
                message.thread_id,
                message.reply_to
            )

            # Notify handlers
            for handler in service.message_handlers:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"Message handler error: {e}")

            # Send ACK
            ack = {
                "type": "ack",
                "message_id": message.id,
                "received_at": datetime.now(UTC).isoformat()
            }
            await stream.write(json.dumps(ack).encode())

    except Exception as e:
        logger.error(f"Error handling chat stream: {e}")
    finally:
        await stream.close()


async def _handle_file_stream(service: 'P2PChatService', stream: 'INetStream') -> None:
    """Handle incoming file transfers."""
    # TODO: Implement chunked file transfer
    logger.info("File stream handler (TODO: implement)")
    pass
