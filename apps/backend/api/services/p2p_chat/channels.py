"""
P2P Chat Service - Channel Operations

High-level channel management:
- Create channels (group/DM)
- List channels
- Get channel details
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Optional, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .service import P2PChatService

try:
    from api.p2p_chat_models import Channel, ChannelType, CreateChannelRequest
except ImportError:
    from p2p_chat_models import Channel, ChannelType, CreateChannelRequest

from . import storage

logger = logging.getLogger(__name__)


async def create_channel(service: 'P2PChatService', request: CreateChannelRequest) -> Channel:
    """
    Create a new channel.

    Args:
        service: P2PChatService instance
        request: Channel creation request

    Returns:
        Created Channel object
    """
    channel = Channel(
        name=request.name,
        type=request.type,
        created_by=service.peer_id,
        description=request.description,
        topic=request.topic,
        members=[service.peer_id] + request.members,
        admins=[service.peer_id]
    )

    # Store in database
    storage.save_channel(
        service.db_path,
        channel.id,
        channel.name,
        channel.type.value,
        channel.created_by,
        channel.members,
        channel.admins,
        None,  # dm_participants
        channel.description,
        channel.topic
    )

    service.active_channels[channel.id] = channel
    logger.info(f"Created channel: {channel.name} ({channel.id})")

    return channel


async def get_channel(service: 'P2PChatService', channel_id: str) -> Optional[Channel]:
    """
    Get a channel by ID.

    Args:
        service: P2PChatService instance
        channel_id: Channel identifier

    Returns:
        Channel object or None if not found
    """
    # Check cache first
    if channel_id in service.active_channels:
        return service.active_channels[channel_id]

    # Query database
    channel_data = storage.get_channel(service.db_path, channel_id)

    if not channel_data:
        return None

    channel = Channel(
        id=channel_data['id'],
        name=channel_data['name'],
        type=ChannelType(channel_data['type']),
        created_at=channel_data['created_at'],
        created_by=channel_data['created_by'],
        description=channel_data['description'],
        topic=channel_data['topic'],
        members=channel_data['members'],
        admins=channel_data['admins']
    )

    service.active_channels[channel_id] = channel
    return channel


async def list_channels(service: 'P2PChatService') -> List[Channel]:
    """
    List all channels.

    Args:
        service: P2PChatService instance

    Returns:
        List of Channel objects
    """
    channels_data = storage.list_channels(service.db_path)

    channels = []
    for data in channels_data:
        channel = Channel(
            id=data['id'],
            name=data['name'],
            type=ChannelType(data['type']),
            created_at=data['created_at'],
            created_by=data['created_by'],
            description=data['description'],
            topic=data['topic'],
            members=data['members'],
            admins=data['admins']
        )
        channels.append(channel)

    return channels
