"""
Compatibility Shim for P2P Chat Models

The implementation now lives in the `api.p2p_chat` package:
- api.p2p_chat.models: P2P chat data models

This shim maintains backward compatibility.
"""

from api.p2p_chat.models import (
    MessageType,
    ChannelType,
    PeerStatus,
    Peer,
    Channel,
    Message,
    FileTransfer,
    TypingIndicator,
    CreateChannelRequest,
    SendMessageRequest,
    CreateDMRequest,
    InviteToChannelRequest,
    UpdatePresenceRequest,
    PeerListResponse,
    ChannelListResponse,
    MessageListResponse,
    P2PStatusResponse,
)

__all__ = [
    "MessageType",
    "ChannelType",
    "PeerStatus",
    "Peer",
    "Channel",
    "Message",
    "FileTransfer",
    "TypingIndicator",
    "CreateChannelRequest",
    "SendMessageRequest",
    "CreateDMRequest",
    "InviteToChannelRequest",
    "UpdatePresenceRequest",
    "PeerListResponse",
    "ChannelListResponse",
    "MessageListResponse",
    "P2PStatusResponse",
]
