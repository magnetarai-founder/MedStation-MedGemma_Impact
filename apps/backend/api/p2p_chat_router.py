"""
FastAPI Router for P2P Team Chat
Provides REST API endpoints for the frontend
"""

import asyncio
from typing import List, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import logging

from p2p_chat_models import (
    Peer, Channel, Message,
    SendMessageRequest, CreateChannelRequest, CreateDMRequest,
    InviteToChannelRequest, UpdatePresenceRequest,
    PeerListResponse, ChannelListResponse, MessageListResponse,
    P2PStatusResponse, ChannelType
)
from p2p_chat_service import get_p2p_chat_service, init_p2p_chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/team", tags=["Team Chat"])

# WebSocket connections for real-time updates
active_connections: List[WebSocket] = []


# ===== Initialization Endpoint =====

@router.post("/initialize")
async def initialize_p2p_service(display_name: str, device_name: str):
    """
    Initialize the P2P chat service
    Called once when the app starts
    """
    try:
        service = init_p2p_chat_service(display_name, device_name)
        await service.start()

        return {
            "status": "started",
            "peer_id": service.peer_id,
            "display_name": display_name,
            "device_name": device_name
        }

    except Exception as e:
        logger.error(f"Failed to initialize P2P service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Status & Peers =====

@router.get("/status", response_model=P2PStatusResponse)
async def get_p2p_status():
    """Get current P2P network status"""
    service = get_p2p_chat_service()

    if not service or not service.is_running:
        raise HTTPException(status_code=503, detail="P2P service not running")

    peers = await service.list_peers()
    online_peers = [p for p in peers if p.status == "online" and p.peer_id != service.peer_id]

    channels = await service.list_channels()

    # Get multiaddrs if host is available
    addrs = []
    if service.host:
        addrs = [str(addr) for addr in service.host.get_addrs()]

    return P2PStatusResponse(
        peer_id=service.peer_id,
        is_connected=service.is_running,
        discovered_peers=len(online_peers),
        active_channels=len(channels),
        multiaddrs=addrs
    )


@router.get("/peers", response_model=PeerListResponse)
async def list_peers():
    """List all discovered peers"""
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    peers = await service.list_peers()

    return PeerListResponse(
        peers=peers,
        total=len(peers)
    )


@router.get("/peers/{peer_id}", response_model=Peer)
async def get_peer(peer_id: str):
    """Get details about a specific peer"""
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    peers = await service.list_peers()
    peer = next((p for p in peers if p.peer_id == peer_id), None)

    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")

    return peer


# ===== Channels =====

@router.post("/channels", response_model=Channel)
async def create_channel(request: CreateChannelRequest):
    """Create a new channel"""
    service = get_p2p_chat_service()

    if not service or not service.is_running:
        raise HTTPException(status_code=503, detail="P2P service not running")

    try:
        channel = await service.create_channel(request)

        # Notify all connected WebSocket clients
        await broadcast_event({
            "type": "channel_created",
            "channel": channel.dict()
        })

        return channel

    except Exception as e:
        logger.error(f"Failed to create channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dm", response_model=Channel)
async def create_direct_message(request: CreateDMRequest):
    """Create a direct message channel with another peer"""
    service = get_p2p_chat_service()

    if not service or not service.is_running:
        raise HTTPException(status_code=503, detail="P2P service not running")

    try:
        # Check if DM already exists
        channels = await service.list_channels()
        existing_dm = next(
            (ch for ch in channels
             if ch.type == ChannelType.DIRECT and
             set(ch.dm_participants or []) == {service.peer_id, request.peer_id}),
            None
        )

        if existing_dm:
            return existing_dm

        # Get peer info for DM name
        peers = await service.list_peers()
        peer = next((p for p in peers if p.peer_id == request.peer_id), None)

        if not peer:
            raise HTTPException(status_code=404, detail="Peer not found")

        # Create DM channel
        dm_request = CreateChannelRequest(
            name=f"DM with {peer.display_name}",
            type=ChannelType.DIRECT,
            members=[request.peer_id]
        )

        channel = await service.create_channel(dm_request)
        channel.dm_participants = [service.peer_id, request.peer_id]

        return channel

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create DM: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channels", response_model=ChannelListResponse)
async def list_channels():
    """List all channels (public, private, and DMs)"""
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    channels = await service.list_channels()

    return ChannelListResponse(
        channels=channels,
        total=len(channels)
    )


@router.get("/channels/{channel_id}", response_model=Channel)
async def get_channel(channel_id: str):
    """Get a specific channel"""
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    channel = await service.get_channel(channel_id)

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    return channel


@router.post("/channels/{channel_id}/invite")
async def invite_to_channel(channel_id: str, request: InviteToChannelRequest):
    """Invite peers to a channel"""
    service = get_p2p_chat_service()

    if not service or not service.is_running:
        raise HTTPException(status_code=503, detail="P2P service not running")

    channel = await service.get_channel(channel_id)

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # TODO: Implement invitation system
    # For now, just add members directly

    return {"status": "invited", "channel_id": channel_id, "peer_ids": request.peer_ids}


# ===== Messages =====

@router.post("/channels/{channel_id}/messages", response_model=Message)
async def send_message(channel_id: str, request: SendMessageRequest):
    """Send a message to a channel"""
    service = get_p2p_chat_service()

    if not service or not service.is_running:
        raise HTTPException(status_code=503, detail="P2P service not running")

    # Ensure channel_id matches
    request.channel_id = channel_id

    try:
        message = await service.send_message(request)

        # Notify all connected WebSocket clients
        await broadcast_event({
            "type": "message_sent",
            "message": message.dict()
        })

        return message

    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channels/{channel_id}/messages", response_model=MessageListResponse)
async def get_messages(channel_id: str, limit: int = 50):
    """Get messages for a channel"""
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    channel = await service.get_channel(channel_id)

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    messages = await service.get_messages(channel_id, limit=limit)

    return MessageListResponse(
        channel_id=channel_id,
        messages=messages,
        total=len(messages),
        has_more=len(messages) >= limit
    )


@router.post("/channels/{channel_id}/messages/{message_id}/read")
async def mark_message_as_read(channel_id: str, message_id: str):
    """Mark a message as read"""
    service = get_p2p_chat_service()

    if not service or not service.is_running:
        raise HTTPException(status_code=503, detail="P2P service not running")

    # TODO: Implement read receipts

    return {"status": "marked_read", "message_id": message_id}


# ===== WebSocket for Real-time Updates =====

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket connection for real-time chat updates
    Sends events for new messages, peer status changes, etc.
    """
    await websocket.accept()
    active_connections.append(websocket)

    logger.info(f"WebSocket connected. Total connections: {len(active_connections)}")

    try:
        # Keep connection alive and listen for pings
        while True:
            data = await websocket.receive_text()

            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(active_connections)}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)


async def broadcast_event(event: dict):
    """Broadcast an event to all connected WebSocket clients"""
    import json

    disconnected = []

    for connection in active_connections:
        try:
            await connection.send_json(event)
        except Exception as e:
            logger.error(f"Failed to send to WebSocket: {e}")
            disconnected.append(connection)

    # Remove disconnected clients
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)


# Export router
__all__ = ["router"]
