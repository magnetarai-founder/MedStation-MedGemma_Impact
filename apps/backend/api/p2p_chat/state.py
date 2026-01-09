"""
P2P Chat - Shared State

In-memory storage for invitations, read receipts, and WebSocket connections.
All route modules import from here to share state.

NOTE: In production, replace with persistent database storage.
"""

from typing import Dict, List
from fastapi import WebSocket

# Storage for invitations and read receipts (in-memory, replace with DB in production)
# Exported directly for test access (clear between tests)
channel_invitations: Dict[str, List[Dict]] = {}  # {channel_id: [{peer_id, invited_by, invited_at, status}]}
read_receipts: Dict[str, List[Dict]] = {}  # {message_id: [{peer_id, read_at}]}

# WebSocket connections for real-time updates
active_connections: List[WebSocket] = []


def get_channel_invitations(channel_id: str) -> List[Dict]:
    """Get invitations for a channel, initializing if needed"""
    if channel_id not in channel_invitations:
        channel_invitations[channel_id] = []
    return channel_invitations[channel_id]


def get_read_receipts(message_id: str) -> List[Dict]:
    """Get read receipts for a message, initializing if needed"""
    if message_id not in read_receipts:
        read_receipts[message_id] = []
    return read_receipts[message_id]


def get_all_read_receipts() -> Dict[str, List[Dict]]:
    """Get all read receipts (for channel-level filtering)"""
    return read_receipts
