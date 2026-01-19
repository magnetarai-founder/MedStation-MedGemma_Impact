"""
Vault WebSocket Routes

Real-time collaboration and notifications via WebSocket connections.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
import json
from datetime import datetime, UTC
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, status

from api.routes.schemas import SuccessResponse
from api.errors import http_500
from api.auth_middleware import get_current_user, extract_websocket_token

logger = logging.getLogger(__name__)

# Import WebSocket connection manager
try:
    from api.websocket_manager import manager
except ImportError:
    manager = None
    logger.warning("WebSocket manager not available for vault notifications")

router = APIRouter(
    prefix="/api/v1/vault",
    tags=["vault-ws"]
)


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    vault_type: str = "real",
    token: str = None  # Auth token from query param (deprecated)
):
    """
    WebSocket endpoint for real-time vault updates

    Supports:
    - Real-time file upload/delete/update notifications
    - User presence tracking
    - Activity broadcasting

    Authentication:
        - Preferred: Sec-WebSocket-Protocol header with "jwt-<token>" or "bearer.<token>"
        - Fallback: Query param ?token=xxx (deprecated)

    Security: Requires valid JWT token for authentication
    """
    # SECURITY: Extract token from header (preferred) or query param (deprecated fallback)
    auth_token = extract_websocket_token(websocket, token)

    # Verify authentication before accepting connection
    if not auth_token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return

    try:
        # Verify JWT token
        import jwt
        from api.auth_middleware import JWT_SECRET, JWT_ALGORITHM
        payload = jwt.decode(auth_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        authenticated_user_id = payload.get("user_id")

        # Verify user_id matches token
        if authenticated_user_id != user_id:
            await websocket.close(code=1008, reason="User ID mismatch")
            return
    except jwt.ExpiredSignatureError:
        await websocket.close(code=1008, reason="Token expired")
        return
    except jwt.InvalidTokenError:
        await websocket.close(code=1008, reason="Invalid token")
        return

    if manager:
        await manager.connect(websocket, user_id, vault_type)
    else:
        await websocket.accept()

    try:
        while True:
            # Receive messages for keepalive and client-initiated events
            data = await websocket.receive_text()

            # Parse incoming message
            try:
                message = json.loads(data)

                # Handle different message types
                if message.get("type") == "ping":
                    # Respond to keepalive ping
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now(UTC).isoformat()})

                elif message.get("type") == "activity_update":
                    # Update user's last activity timestamp
                    if manager and user_id in manager.user_presence:
                        manager.user_presence[user_id]["last_activity"] = datetime.now(UTC).isoformat()

                else:
                    # Echo unknown messages for debugging
                    await websocket.send_json({"type": "echo", "received": message})

            except json.JSONDecodeError:
                # If not JSON, treat as simple keepalive string
                await websocket.send_text(f"Message received: {data}")

    except WebSocketDisconnect:
        if manager:
            manager.disconnect(websocket, user_id, vault_type)
        logger.info(f"WebSocket disconnected: user={user_id}, vault={vault_type}")


@router.get(
    "/ws/online-users",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="get_online_users",
    summary="Get online users",
    description="Get list of currently online users in vault WebSocket connections"
)
async def get_online_users(
    vault_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """Get list of currently online users via WebSocket"""
    try:
        if not manager:
            data = {
                "online_users": [],
                "total_connections": 0,
                "vault_type": vault_type,
                "manager_available": False
            }
            message = "WebSocket manager not available"
        else:
            data = {
                "online_users": manager.get_online_users(vault_type),
                "total_connections": manager.get_connection_count(),
                "vault_type": vault_type,
                "manager_available": True
            }
            message = f"Retrieved {len(data['online_users'])} online user(s)"

        return SuccessResponse(
            data=data,
            message=message
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get online users", exc_info=True)
        raise http_500("Failed to retrieve online users")
