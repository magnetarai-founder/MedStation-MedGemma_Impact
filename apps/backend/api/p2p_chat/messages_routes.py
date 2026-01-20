"""
P2P Chat - Message Routes

Message sending and read receipt endpoints.
"""

from typing import Dict, Any
from datetime import datetime, UTC
from fastapi import APIRouter, Request, Depends
import logging

from api.errors import http_404, http_500, http_503
from api.p2p_chat.models import (
    Message,
    SendMessageRequest,
    MessageListResponse,
)
from api.auth_middleware import get_current_user

# NOTE: Import get_p2p_chat_service lazily inside functions to avoid circular import
from api.p2p_chat.state import get_read_receipts, get_all_read_receipts
from api.p2p_chat.websocket_routes import broadcast_event

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/channels/{channel_id}/messages", response_model=Message)
async def send_message(request: Request, channel_id: str, body: SendMessageRequest) -> Message:
    """Send a message to a channel"""
    from api.services.p2p_chat import get_p2p_chat_service

    service = get_p2p_chat_service()

    if not service or not service.is_running:
        raise http_503("P2P service not running", service="p2p_chat")

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
        raise http_500(str(e))


@router.get("/channels/{channel_id}/messages", response_model=MessageListResponse)
async def get_messages(channel_id: str, limit: int = 50) -> MessageListResponse:
    """Get messages for a channel"""
    from api.services.p2p_chat import get_p2p_chat_service

    service = get_p2p_chat_service()

    if not service:
        raise http_503("P2P service not initialized", service="p2p_chat")

    channel = await service.get_channel(channel_id)

    if not channel:
        raise http_404("Channel not found", resource="channel")

    messages = await service.get_messages(channel_id, limit=limit)

    return MessageListResponse(
        channel_id=channel_id,
        messages=messages,
        total=len(messages),
        has_more=len(messages) >= limit
    )


@router.post("/channels/{channel_id}/messages/{message_id}/read")
async def mark_message_as_read(
    request: Request,
    channel_id: str,
    message_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Mark a message as read"""
    from api.services.p2p_chat import get_p2p_chat_service

    service = get_p2p_chat_service()

    if not service or not service.is_running:
        raise http_503("P2P service not running", service="p2p_chat")

    user_id = current_user.get("user_id", "anonymous")

    # Get read receipts for this message
    receipts = get_read_receipts(message_id)

    # Check if already marked read by this user
    existing = next(
        (r for r in receipts if r["peer_id"] == user_id),
        None
    )

    if existing:
        logger.debug(f"Message {message_id} already marked read by {user_id}")
        return {
            "status": "already_read",
            "message_id": message_id,
            "read_at": existing["read_at"]
        }

    # Add new read receipt
    receipt = {
        "peer_id": user_id,
        "message_id": message_id,
        "channel_id": channel_id,
        "read_at": datetime.now(UTC).isoformat()
    }
    receipts.append(receipt)

    logger.info(f"User {user_id} marked message {message_id} as read")

    return {
        "status": "marked_read",
        "message_id": message_id,
        "read_at": receipt["read_at"]
    }


@router.get("/channels/{channel_id}/messages/{message_id}/receipts")
async def get_message_receipts(
    channel_id: str,
    message_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get read receipts for a message"""
    from api.services.p2p_chat import get_p2p_chat_service

    service = get_p2p_chat_service()

    if not service:
        raise http_503("P2P service not initialized", service="p2p_chat")

    receipts = get_read_receipts(message_id)

    return {
        "message_id": message_id,
        "channel_id": channel_id,
        "receipts": receipts,
        "total_reads": len(receipts),
        "read_by": [r["peer_id"] for r in receipts]
    }


@router.get("/channels/{channel_id}/receipts")
async def get_channel_receipts(
    channel_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get all read receipts for messages in a channel"""
    from api.services.p2p_chat import get_p2p_chat_service

    service = get_p2p_chat_service()

    if not service:
        raise http_503("P2P service not initialized", service="p2p_chat")

    # Filter receipts by channel
    all_receipts = get_all_read_receipts()
    channel_receipts = {}
    for message_id, receipts in all_receipts.items():
        # Filter receipts that belong to this channel
        channel_specific = [r for r in receipts if r.get("channel_id") == channel_id]
        if channel_specific:
            channel_receipts[message_id] = channel_specific

    return {
        "channel_id": channel_id,
        "receipts_by_message": channel_receipts,
        "total_messages": len(channel_receipts)
    }
