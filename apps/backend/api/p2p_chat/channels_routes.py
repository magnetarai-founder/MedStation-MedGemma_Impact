"""
P2P Chat - Channel Routes

Channel CRUD and invitation management endpoints.
"""

from typing import Dict, Any, Optional
from datetime import datetime, UTC
from fastapi import APIRouter, Request, Depends
import logging

from api.errors import http_403, http_404, http_500, http_503
from api.p2p_chat_models import (
    Channel,
    CreateChannelRequest,
    CreateDMRequest,
    InviteToChannelRequest,
    ChannelListResponse,
    ChannelType,
)
from api.services.p2p_chat import get_p2p_chat_service
from api.auth_middleware import get_current_user
from api.p2p_chat.state import get_channel_invitations
from api.p2p_chat.websocket_routes import broadcast_event

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/channels", response_model=Channel)
async def create_channel(request: Request, body: CreateChannelRequest) -> Channel:
    """Create a new channel"""
    service = get_p2p_chat_service()

    if not service or not service.is_running:
        raise http_503("P2P service not running", service="p2p_chat")

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
        raise http_500(str(e))


@router.post("/dm", response_model=Channel)
async def create_direct_message(request: Request, body: CreateDMRequest) -> Channel:
    """Create a direct message channel with another peer"""
    service = get_p2p_chat_service()

    if not service or not service.is_running:
        raise http_503("P2P service not running", service="p2p_chat")

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
            raise http_404("Peer not found", resource="peer")

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
        raise http_500(str(e))


@router.get("/channels", response_model=ChannelListResponse)
async def list_channels() -> ChannelListResponse:
    """List all channels (public, private, and DMs)"""
    service = get_p2p_chat_service()

    if not service:
        raise http_503("P2P service not initialized", service="p2p_chat")

    channels = await service.list_channels()

    return ChannelListResponse(
        channels=channels,
        total=len(channels)
    )


@router.get("/channels/{channel_id}", response_model=Channel)
async def get_channel(channel_id: str) -> Channel:
    """Get a specific channel"""
    service = get_p2p_chat_service()

    if not service:
        raise http_503("P2P service not initialized", service="p2p_chat")

    channel = await service.get_channel(channel_id)

    if not channel:
        raise http_404("Channel not found", resource="channel")

    return channel


@router.post("/channels/{channel_id}/invite")
async def invite_to_channel(
    request: Request,
    channel_id: str,
    body: InviteToChannelRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Invite peers to a channel"""
    service = get_p2p_chat_service()

    if not service or not service.is_running:
        raise http_503("P2P service not running", service="p2p_chat")

    channel = await service.get_channel(channel_id)

    if not channel:
        raise http_404("Channel not found", resource="channel")

    # Create invitations
    invitations_list = get_channel_invitations(channel_id)

    invitations = []
    user_id = current_user.get("user_id", "system")

    for peer_id in body.peer_ids:
        # Check if invitation already exists
        existing = next(
            (inv for inv in invitations_list
             if inv["peer_id"] == peer_id and inv["status"] == "pending"),
            None
        )

        if existing:
            logger.debug(f"Invitation already exists for peer {peer_id} to channel {channel_id}")
            invitations.append(existing)
            continue

        invitation = {
            "peer_id": peer_id,
            "channel_id": channel_id,
            "invited_by": user_id,
            "invited_at": datetime.now(UTC).isoformat(),
            "status": "pending"
        }
        invitations_list.append(invitation)
        invitations.append(invitation)

        logger.info(f"Created invitation for peer {peer_id} to channel {channel_id}")

    return {
        "status": "invited",
        "channel_id": channel_id,
        "invitations": invitations,
        "total": len(invitations)
    }


@router.get("/channels/{channel_id}/invitations")
async def list_channel_invitations(
    channel_id: str,
    status: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """List invitations for a channel"""
    service = get_p2p_chat_service()

    if not service:
        raise http_503("P2P service not initialized", service="p2p_chat")

    invitations = get_channel_invitations(channel_id).copy()

    # Filter by status if provided
    if status:
        invitations = [inv for inv in invitations if inv["status"] == status]

    # Filter by current user permissions
    user_id = current_user.get("user_id")
    role = current_user.get("role")

    if role != "admin":
        # Non-admins can only see their own invitations or ones they sent
        invitations = [
            inv for inv in invitations
            if inv["peer_id"] == user_id or inv["invited_by"] == user_id
        ]

    return {
        "channel_id": channel_id,
        "invitations": invitations,
        "total": len(invitations)
    }


@router.post("/channels/{channel_id}/invitations/{peer_id}/accept")
async def accept_channel_invitation(
    channel_id: str,
    peer_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Accept a channel invitation"""
    service = get_p2p_chat_service()

    if not service or not service.is_running:
        raise http_503("P2P service not running", service="p2p_chat")

    # Verify current user matches peer_id
    user_id = current_user.get("user_id")
    if peer_id != user_id:
        raise http_403("Cannot accept invitation for another user")

    # Find invitation
    invitations = get_channel_invitations(channel_id)
    invitation = next(
        (inv for inv in invitations if inv["peer_id"] == peer_id and inv["status"] == "pending"),
        None
    )

    if not invitation:
        raise http_404("Invitation not found or already processed", resource="invitation")

    # Update invitation status
    invitation["status"] = "accepted"
    invitation["accepted_at"] = datetime.now(UTC).isoformat()

    logger.info(f"User {peer_id} accepted invitation to channel {channel_id}")

    return {
        "status": "accepted",
        "channel_id": channel_id,
        "peer_id": peer_id,
        "accepted_at": invitation["accepted_at"]
    }


@router.post("/channels/{channel_id}/invitations/{peer_id}/decline")
async def decline_channel_invitation(
    channel_id: str,
    peer_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Decline a channel invitation"""
    user_id = current_user.get("user_id")
    if peer_id != user_id:
        raise http_403("Cannot decline invitation for another user")

    # Find invitation
    invitations = get_channel_invitations(channel_id)
    invitation = next(
        (inv for inv in invitations if inv["peer_id"] == peer_id and inv["status"] == "pending"),
        None
    )

    if not invitation:
        raise http_404("Invitation not found or already processed", resource="invitation")

    # Update invitation status
    invitation["status"] = "declined"
    invitation["declined_at"] = datetime.now(UTC).isoformat()

    logger.info(f"User {peer_id} declined invitation to channel {channel_id}")

    return {
        "status": "declined",
        "channel_id": channel_id,
        "peer_id": peer_id
    }
