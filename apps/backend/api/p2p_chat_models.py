"""
Compatibility Shim for P2P Chat Models

The implementation now lives in the `api.p2p_chat` package:
- api.p2p_chat.models: P2P chat data models

This shim maintains backward compatibility.

NOTE: Uses importlib to avoid circular imports. Importing api.p2p_chat.models
would trigger api.p2p_chat/__init__.py, which imports routes that import services
that import back to this file.
"""

import importlib

# Load the models module directly to avoid triggering api.p2p_chat/__init__.py
_models = importlib.import_module("api.p2p_chat.models")

# Re-export all model classes
MessageType = _models.MessageType
ChannelType = _models.ChannelType
PeerStatus = _models.PeerStatus
Peer = _models.Peer
Channel = _models.Channel
Message = _models.Message
FileTransfer = _models.FileTransfer
TypingIndicator = _models.TypingIndicator
CreateChannelRequest = _models.CreateChannelRequest
SendMessageRequest = _models.SendMessageRequest
CreateDMRequest = _models.CreateDMRequest
InviteToChannelRequest = _models.InviteToChannelRequest
UpdatePresenceRequest = _models.UpdatePresenceRequest
PeerListResponse = _models.PeerListResponse
ChannelListResponse = _models.ChannelListResponse
MessageListResponse = _models.MessageListResponse
P2PStatusResponse = _models.P2PStatusResponse

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
