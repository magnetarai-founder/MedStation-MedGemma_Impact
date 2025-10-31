"""
FastAPI Router for P2P Team Chat
Provides REST API endpoints for the frontend
"""

import asyncio
from typing import List, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request
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
async def initialize_p2p_service(request: Request, display_name: str, device_name: str):
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
async def create_channel(request: Request, body: CreateChannelRequest):
    """Create a new channel"""
    service = get_p2p_chat_service()

    if not service or not service.is_running:
        raise HTTPException(status_code=503, detail="P2P service not running")

    try:
        channel = await service.create_channel(body)

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
async def create_direct_message(request: Request, body: CreateDMRequest):
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
             set(ch.dm_participants or []) == {service.peer_id, body.peer_id}),
            None
        )

        if existing_dm:
            return existing_dm

        # Get peer info for DM name
        peers = await service.list_peers()
        peer = next((p for p in peers if p.peer_id == body.peer_id), None)

        if not peer:
            raise HTTPException(status_code=404, detail="Peer not found")

        # Create DM channel
        dm_request = CreateChannelRequest(
            name=f"DM with {peer.display_name}",
            type=ChannelType.DIRECT,
            members=[body.peer_id]
        )

        channel = await service.create_channel(dm_request)
        channel.dm_participants = [service.peer_id, body.peer_id]

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
async def invite_to_channel(request: Request, channel_id: str, body: InviteToChannelRequest):
    """Invite peers to a channel"""
    service = get_p2p_chat_service()

    if not service or not service.is_running:
        raise HTTPException(status_code=503, detail="P2P service not running")

    channel = await service.get_channel(channel_id)

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # TODO: Implement invitation system
    # For now, just add members directly

    return {"status": "invited", "channel_id": channel_id, "peer_ids": body.peer_ids}


# ===== Messages =====

@router.post("/channels/{channel_id}/messages", response_model=Message)
async def send_message(request: Request, channel_id: str, body: SendMessageRequest):
    """Send a message to a channel"""
    service = get_p2p_chat_service()

    if not service or not service.is_running:
        raise HTTPException(status_code=503, detail="P2P service not running")

    # Ensure channel_id matches
    body.channel_id = channel_id

    try:
        message = await service.send_message(body)

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
async def mark_message_as_read(request: Request, channel_id: str, message_id: str):
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


# ===== E2E Encryption Endpoints =====

@router.post("/e2e/init")
async def initialize_e2e_keys(request: Request, device_id: str, passphrase: str):
    """
    Initialize E2E encryption keys for this device

    Args:
        device_id: Unique device identifier
        passphrase: User's passphrase for Secure Enclave

    Returns:
        Dict with public_key and fingerprint
    """
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    try:
        result = service.init_device_keys(device_id, passphrase)
        return result
    except Exception as e:
        logger.error(f"Failed to initialize E2E keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/e2e/peers/{peer_id}/keys")
async def store_peer_public_key(request: Request, peer_id: str, public_key_hex: str, verify_key_hex: str):
    """
    Store a peer's public key and generate safety number

    Args:
        peer_id: Peer's device identifier
        public_key_hex: Peer's Curve25519 public key (hex encoded)
        verify_key_hex: Peer's Ed25519 verify key (hex encoded)

    Returns:
        Dict with safety_number and fingerprint
    """
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    try:
        public_key = bytes.fromhex(public_key_hex)
        verify_key = bytes.fromhex(verify_key_hex)
        result = service.store_peer_key(peer_id, public_key, verify_key)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid key format: {e}")
    except Exception as e:
        logger.error(f"Failed to store peer key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/e2e/peers/{peer_id}/verify")
async def verify_peer(request: Request, peer_id: str):
    """
    Mark a peer's fingerprint as verified

    Args:
        peer_id: Peer's device identifier

    Returns:
        Success status
    """
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    try:
        result = service.verify_peer_fingerprint(peer_id)
        return {"status": "verified", "peer_id": peer_id}
    except Exception as e:
        logger.error(f"Failed to verify peer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/e2e/safety-changes")
async def get_safety_changes():
    """
    Get list of unacknowledged safety number changes

    Returns:
        List of safety number changes that need user acknowledgment
    """
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    try:
        changes = service.get_unacknowledged_safety_changes()
        return {"changes": changes, "total": len(changes)}
    except Exception as e:
        logger.error(f"Failed to get safety changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/e2e/safety-changes/{change_id}/acknowledge")
async def acknowledge_safety_change(request: Request, change_id: int):
    """
    Mark a safety number change as acknowledged

    Args:
        change_id: ID of the safety number change

    Returns:
        Success status
    """
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    try:
        result = service.acknowledge_safety_change(change_id)
        return {"status": "acknowledged", "change_id": change_id}
    except Exception as e:
        logger.error(f"Failed to acknowledge safety change: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/e2e/export")
async def export_identity(request: Request, passphrase: str):
    """
    Export identity keypair for linking to another device (QR code)

    Args:
        passphrase: User's passphrase

    Returns:
        Encrypted bundle for QR code scanning
    """
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    try:
        bundle = service.e2e_service.export_identity_for_linking(passphrase)
        return bundle
    except Exception as e:
        logger.error(f"Failed to export identity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/e2e/import")
async def import_identity(
    request: Request,
    encrypted_bundle: str,
    salt: str,
    nonce: str,
    passphrase: str,
    new_device_id: str
):
    """
    Import identity keypair from another device (from QR code)

    Args:
        encrypted_bundle: Encrypted bundle (hex)
        salt: Salt (hex)
        nonce: Nonce (hex)
        passphrase: User's passphrase
        new_device_id: Device ID for this device

    Returns:
        Dict with public_key and fingerprint
    """
    service = get_p2p_chat_service()

    if not service:
        raise HTTPException(status_code=503, detail="P2P service not initialized")

    try:
        encrypted_data = {
            "encrypted_bundle": encrypted_bundle,
            "salt": salt,
            "nonce": nonce
        }

        public_key, fingerprint = service.e2e_service.import_identity_from_link(
            encrypted_data,
            passphrase,
            new_device_id
        )

        return {
            "public_key": public_key.hex(),
            "fingerprint": service.e2e_service.format_fingerprint(fingerprint),
            "device_id": new_device_id
        }
    except Exception as e:
        logger.error(f"Failed to import identity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export router
__all__ = ["router"]
