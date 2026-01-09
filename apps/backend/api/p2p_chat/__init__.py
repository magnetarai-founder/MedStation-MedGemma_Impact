"""
P2P Chat Package

FastAPI Router for P2P Team Chat.
Provides REST API endpoints for the frontend.

Components:
- state.py: Shared in-memory state (invitations, receipts, connections)
- status_routes.py: Service initialization and peer discovery
- channels_routes.py: Channel CRUD and invitations
- messages_routes.py: Message sending and read receipts
- websocket_routes.py: Real-time WebSocket updates
- e2e_routes.py: End-to-end encryption endpoints
"""

from fastapi import APIRouter, Depends

from api.auth_middleware import get_current_user

# Import sub-routers
from api.p2p_chat.status_routes import (
    router as status_router,
    initialize_p2p_service,
    get_p2p_status,
    list_peers,
    get_peer,
)
from api.p2p_chat.channels_routes import (
    router as channels_router,
    create_channel,
    create_direct_message,
    list_channels,
    get_channel,
    invite_to_channel,
    list_channel_invitations,
    accept_channel_invitation,
    decline_channel_invitation,
)
from api.p2p_chat.messages_routes import (
    router as messages_router,
    send_message,
    get_messages,
    mark_message_as_read,
    get_message_receipts,
    get_channel_receipts,
)
from api.p2p_chat.websocket_routes import (
    router as websocket_router,
    websocket_endpoint,
    broadcast_event,
)
from api.p2p_chat.e2e_routes import (
    router as e2e_router,
    initialize_e2e_keys,
    store_peer_public_key,
    verify_peer,
    get_safety_changes,
    acknowledge_safety_change,
    export_identity,
    import_identity,
)

# Import state for re-export
from api.p2p_chat.state import (
    active_connections,
    channel_invitations,
    read_receipts,
    get_channel_invitations,
    get_read_receipts,
    get_all_read_receipts,
)

# Create main router that includes all sub-routers
router = APIRouter(
    prefix="/api/v1/team",
    tags=["Team Chat"],
    dependencies=[Depends(get_current_user)]  # Require auth for all P2P chat endpoints
)
router.include_router(status_router)
router.include_router(channels_router)
router.include_router(messages_router)
router.include_router(websocket_router)
router.include_router(e2e_router)


__all__ = [
    # Main router
    "router",
    # State
    "active_connections",
    "channel_invitations",
    "read_receipts",
    "get_channel_invitations",
    "get_read_receipts",
    "get_all_read_receipts",
    # Broadcast
    "broadcast_event",
    # Status endpoints
    "initialize_p2p_service",
    "get_p2p_status",
    "list_peers",
    "get_peer",
    # Channel endpoints
    "create_channel",
    "create_direct_message",
    "list_channels",
    "get_channel",
    "invite_to_channel",
    "list_channel_invitations",
    "accept_channel_invitation",
    "decline_channel_invitation",
    # Message endpoints
    "send_message",
    "get_messages",
    "mark_message_as_read",
    "get_message_receipts",
    "get_channel_receipts",
    # WebSocket endpoint
    "websocket_endpoint",
    # E2E endpoints
    "initialize_e2e_keys",
    "store_peer_public_key",
    "verify_peer",
    "get_safety_changes",
    "acknowledge_safety_change",
    "export_identity",
    "import_identity",
]
