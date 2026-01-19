"""
P2P Chat Service - Message Operations

High-level message handling:
- Send messages
- Retrieve message history
- Peer-to-peer message delivery with E2E encryption
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime

# Conditional libp2p import
try:
    from libp2p.peer.id import ID as PeerID
    LIBP2P_AVAILABLE = True
except ImportError:
    PeerID = None
    LIBP2P_AVAILABLE = False

if TYPE_CHECKING:
    from .service import P2PChatService

from api.p2p_chat_models import Message, MessageType, SendMessageRequest

from .types import PROTOCOL_ID
from . import storage
from . import channels as channel_ops

logger = logging.getLogger(__name__)


async def send_message(service: 'P2PChatService', request: SendMessageRequest) -> Message:
    """
    Send a message to a channel.

    Args:
        service: P2PChatService instance
        request: Message send request

    Returns:
        Created Message object

    Raises:
        RuntimeError: If P2P service not running
        ValueError: If channel not found
    """
    if not service.is_running:
        raise RuntimeError("P2P service not running")

    # Create message
    message = Message(
        channel_id=request.channel_id,
        sender_id=service.peer_id,
        sender_name=service.display_name,
        type=request.type,
        content=request.content,
        reply_to=request.reply_to,
        file_metadata=request.file_metadata
    )

    # Store locally
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

    # Get channel members
    channel = await channel_ops.get_channel(service, request.channel_id)
    if not channel:
        raise ValueError(f"Channel {request.channel_id} not found")

    # Send to all members
    for peer_id in channel.members:
        if peer_id == service.peer_id:
            continue  # Don't send to ourselves

        try:
            await _send_to_peer(service, peer_id, message)
        except Exception as e:
            logger.error(f"Failed to send message to {peer_id}: {e}")

    return message


async def _send_to_peer(service: 'P2PChatService', peer_id_str: str, message: Message) -> None:
    """Send a message to a specific peer with E2E encryption."""
    try:
        # Convert peer_id string to PeerID object
        peer_id = PeerID.from_base58(peer_id_str)

        # Open stream to peer
        stream = await service.host.new_stream(peer_id, [PROTOCOL_ID])

        # Convert message to dict
        message_dict = message.dict()

        # Encrypt message content if E2E keys exist
        try:
            # Get peer's public key from database
            conn = sqlite3.connect(str(service.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT public_key FROM peer_keys WHERE peer_device_id = ?", (peer_id_str,))
            row = cursor.fetchone()
            conn.close()

            if row and row[0]:
                # Encrypt the content
                recipient_public_key = row[0]
                encrypted_content = service.e2e_service.encrypt_message(recipient_public_key, message.content)
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
            storage.mark_message_delivered(service.db_path, message.id, peer_id_str)
            logger.info(f"✓ Message {message.id[:8]} delivered to {peer_id_str[:8]}")

        await stream.close()

    except Exception as e:
        logger.error(f"Failed to send message to {peer_id_str}: {e}")


async def get_messages(service: 'P2PChatService', channel_id: str, limit: int = 50) -> List[Message]:
    """
    Get messages for a channel.

    Args:
        service: P2PChatService instance
        channel_id: Channel identifier
        limit: Maximum number of messages to retrieve

    Returns:
        List of Message objects in chronological order
    """
    messages_data = storage.get_messages(service.db_path, channel_id, limit)

    messages = []
    for data in messages_data:
        message = Message(
            id=data['id'],
            channel_id=data['channel_id'],
            sender_id=data['sender_id'],
            sender_name=data['sender_name'],
            type=MessageType(data['type']),
            content=data['content'],
            encrypted=bool(data['encrypted']),
            timestamp=data['timestamp'],
            edited_at=data['edited_at'],
            file_metadata=data['file_metadata'],
            thread_id=data['thread_id'],
            reply_to=data['reply_to'],
            reactions=data.get('reactions', {}),
            delivered_to=data['delivered_to'],
            read_by=data['read_by']
        )
        messages.append(message)

    # Reverse to get chronological order (storage returns DESC)
    return list(reversed(messages))
