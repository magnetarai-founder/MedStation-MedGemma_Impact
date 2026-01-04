"""
P2P Chat Service - Main Orchestrator

Coordinates all P2P chat functionality:
- Network lifecycle (start/stop)
- Channel operations
- Message operations
- File transfers
- E2E encryption integration
- Peer management
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable

try:
    from api.p2p_chat_models import (
        Peer, Channel, Message, SendMessageRequest, CreateChannelRequest, PeerStatus
    )
except ImportError:
    from p2p_chat_models import (
        Peer, Channel, Message, SendMessageRequest, CreateChannelRequest, PeerStatus
    )

from .types import DB_PATH
from . import storage
from . import encryption
from . import network
from . import channels as channel_ops
from . import messages as message_ops
from . import files as file_ops

logger = logging.getLogger(__name__)


class P2PChatService:
    """
    Main P2P chat service using libp2p for mesh networking.
    Handles peer discovery, messaging, and file transfers.
    """

    def __init__(self, display_name: str, device_name: str):
        """
        Initialize P2P Chat Service.

        Args:
            display_name: User's display name
            device_name: Device name
        """
        self.display_name = display_name
        self.device_name = device_name

        # libp2p host (will be initialized in start())
        self.host = None
        self.peer_id = None
        self.key_pair = None

        # E2E Encryption service
        self.e2e_service = encryption.get_e2e_service()

        # Local storage
        self.db_path = DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        storage.init_db(self.db_path)

        # In-memory state
        self.discovered_peers: Dict[str, Peer] = {}
        self.active_channels: Dict[str, Channel] = {}
        self.message_handlers: List[Callable] = []

        # Running state
        self.is_running = False

        logger.info(f"P2P Chat Service initialized for {display_name} on {device_name}")

    # ===== E2E Encryption Methods =====

    def init_device_keys(self, device_id: str, passphrase: str) -> Dict:
        """
        Initialize E2E encryption keys for this device.

        Args:
            device_id: Unique device identifier
            passphrase: User's passphrase for Secure Enclave

        Returns:
            Dict with public_key and fingerprint
        """
        return encryption.init_device_keys(self.db_path, device_id, passphrase)

    def store_peer_key(self, peer_device_id: str, public_key: bytes, verify_key: bytes) -> Dict:
        """
        Store a peer's public key and generate safety number.

        Args:
            peer_device_id: Peer's device identifier
            public_key: Peer's Curve25519 public key
            verify_key: Peer's Ed25519 verify key

        Returns:
            Dict with safety_number and fingerprint
        """
        return encryption.store_peer_key(self.db_path, peer_device_id, public_key, verify_key)

    def verify_peer_fingerprint(self, peer_device_id: str) -> bool:
        """
        Mark a peer's fingerprint as verified.

        Args:
            peer_device_id: Peer's device identifier

        Returns:
            True if marked verified
        """
        return encryption.verify_peer_fingerprint(self.db_path, peer_device_id)

    def get_unacknowledged_safety_changes(self) -> List[Dict]:
        """
        Get list of unacknowledged safety number changes (for yellow warning UI).

        Returns:
            List of safety number changes that need user acknowledgment
        """
        return encryption.get_unacknowledged_safety_changes(self.db_path)

    def acknowledge_safety_change(self, change_id: int) -> bool:
        """
        Mark a safety number change as acknowledged.

        Args:
            change_id: ID of the safety_number_changes record

        Returns:
            True if acknowledged
        """
        return encryption.acknowledge_safety_change(self.db_path, change_id)

    # ===== Network Lifecycle =====

    async def start(self) -> None:
        """Start the P2P service with libp2p."""
        await network.start_network(self)

    async def stop(self) -> None:
        """Stop the P2P service."""
        await network.stop_network(self)

    async def close_all_connections(self) -> None:
        """Emergency: Close all P2P connections immediately (for panic mode)."""
        await network.close_all_connections(self)

    # ===== Channel Operations =====

    async def create_channel(self, request: CreateChannelRequest) -> Channel:
        """
        Create a new channel.

        Args:
            request: Channel creation request

        Returns:
            Created Channel object
        """
        return await channel_ops.create_channel(self, request)

    async def get_channel(self, channel_id: str) -> Optional[Channel]:
        """
        Get a channel by ID.

        Args:
            channel_id: Channel identifier

        Returns:
            Channel object or None if not found
        """
        return await channel_ops.get_channel(self, channel_id)

    async def list_channels(self) -> List[Channel]:
        """
        List all channels.

        Returns:
            List of Channel objects
        """
        return await channel_ops.list_channels(self)

    # ===== Message Operations =====

    async def send_message(self, request: SendMessageRequest) -> Message:
        """
        Send a message to a channel.

        Args:
            request: Message send request

        Returns:
            Created Message object

        Raises:
            RuntimeError: If P2P service not running
            ValueError: If channel not found
        """
        return await message_ops.send_message(self, request)

    async def get_messages(self, channel_id: str, limit: int = 50) -> List[Message]:
        """
        Get messages for a channel.

        Args:
            channel_id: Channel identifier
            limit: Maximum number of messages to retrieve

        Returns:
            List of Message objects in chronological order
        """
        return await message_ops.get_messages(self, channel_id, limit)

    # ===== Peer Operations =====

    async def list_peers(self) -> List[Peer]:
        """
        List discovered peers.

        Returns:
            List of Peer objects
        """
        peers_data = storage.get_peers(self.db_path)

        peers = []
        for data in peers_data:
            peer = Peer(
                peer_id=data['peer_id'],
                display_name=data['display_name'],
                device_name=data['device_name'],
                public_key=data['public_key'] or "",
                status=PeerStatus(data['status']),
                last_seen=data['last_seen'],
                avatar_hash=data.get('avatar_hash'),
                bio=data.get('bio')
            )
            peers.append(peer)

        return peers

    # ===== File Transfer Operations =====

    async def initiate_file_transfer(self, file_name: str, file_size: int,
                                     mime_type: str, channel_id: str,
                                     recipient_ids: list) -> Dict:
        """
        Initiate a file transfer.

        Args:
            file_name: Name of the file
            file_size: File size in bytes
            mime_type: MIME type of the file
            channel_id: Target channel
            recipient_ids: List of recipient peer IDs

        Returns:
            Dict with transfer_id and metadata
        """
        return await file_ops.initiate_file_transfer(
            self, file_name, file_size, mime_type, channel_id, recipient_ids
        )

    async def update_transfer_progress(self, transfer_id: str, chunks_received: int,
                                       progress_percent: float) -> None:
        """
        Update file transfer progress.

        Args:
            transfer_id: Transfer identifier
            chunks_received: Number of chunks received
            progress_percent: Progress percentage (0-100)
        """
        await file_ops.update_transfer_progress(self, transfer_id, chunks_received, progress_percent)

    async def get_transfer_status(self, transfer_id: str) -> Optional[Dict]:
        """
        Get file transfer status.

        Args:
            transfer_id: Transfer identifier

        Returns:
            Transfer metadata dict or None if not found
        """
        return await file_ops.get_transfer_status(self, transfer_id)

    async def send_file(self, file_path: str, channel_id: str,
                        recipient_ids: list, mime_type: Optional[str] = None) -> Dict:
        """
        Send a file to peers via chunked transfer.

        Args:
            file_path: Path to the file to send
            channel_id: Target channel
            recipient_ids: List of recipient peer IDs
            mime_type: MIME type (auto-detected if not provided)

        Returns:
            Dict with transfer_id, status, and metadata
        """
        from pathlib import Path
        return await file_ops.send_file(
            self, Path(file_path), channel_id, recipient_ids, mime_type
        )

    async def cancel_file_transfer(self, transfer_id: str) -> Dict:
        """
        Cancel an active file transfer.

        Args:
            transfer_id: Transfer to cancel

        Returns:
            Status dict
        """
        return await file_ops.cancel_file_transfer(self, transfer_id)

    async def list_active_transfers(self) -> list:
        """
        List all active file transfers.

        Returns:
            List of active transfer metadata dicts
        """
        return await file_ops.list_active_transfers(self)

    # ===== Message Handler Registration =====

    def register_message_handler(self, handler: Callable) -> None:
        """
        Register a callback for new messages.

        Args:
            handler: Async callable that receives Message objects
        """
        self.message_handlers.append(handler)


# ===== Singleton Management =====

_service_instance: Optional[P2PChatService] = None


def get_p2p_chat_service() -> Optional[P2PChatService]:
    """
    Get the singleton P2P chat service instance.

    Returns:
        P2PChatService instance or None if not initialized
    """
    return _service_instance


def init_p2p_chat_service(display_name: str, device_name: str) -> P2PChatService:
    """
    Initialize the P2P chat service.

    Args:
        display_name: User's display name
        device_name: Device name

    Returns:
        P2PChatService instance (singleton)
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = P2PChatService(display_name, device_name)
    return _service_instance
