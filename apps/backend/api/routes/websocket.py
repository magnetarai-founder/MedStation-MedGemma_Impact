"""
WebSocket API endpoints.

Real-time WebSocket connections for query progress, streaming updates, and mesh networking.
"""

import json
import logging
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.main import sessions

router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger(__name__)

# Track active mesh connections
_active_mesh_connections: Dict[str, WebSocket] = {}


@router.websocket("/api/sessions/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time query progress and logs"""
    if session_id not in sessions:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()

    try:
        while True:
            # Receive query request
            data = await websocket.receive_json()

            if data.get("type") == "query":
                # Execute query and stream progress
                await websocket.send_json({
                    "type": "progress",
                    "message": "Starting query execution..."
                })

                # Security: Validate table access (same as REST endpoint)
                sql_query = data.get("sql", "")
                from neutron_utils.sql_utils import SQLProcessor as SQLUtil
                referenced_tables = SQLUtil.extract_table_names(sql_query)
                allowed_tables = {'excel_file'}

                unauthorized_tables = set(referenced_tables) - allowed_tables
                if unauthorized_tables:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Query references unauthorized tables: {', '.join(unauthorized_tables)}"
                    })
                    continue

                # TODO: Implement actual progress streaming
                # For now, just execute and return result
                engine = sessions[session_id]['engine']
                result = engine.execute_sql(sql_query)

                if result.error:
                    await websocket.send_json({
                        "type": "error",
                        "message": result.error
                    })
                else:
                    await websocket.send_json({
                        "type": "complete",
                        "row_count": result.row_count,
                        "execution_time_ms": result.execution_time_ms
                    })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })


@router.websocket("/mesh")
async def mesh_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for mesh P2P networking.

    Handles peer connections for multi-hop message relay.
    """
    await websocket.accept()

    peer_id = None

    try:
        # Wait for handshake
        handshake_data = await websocket.receive_text()
        handshake = json.loads(handshake_data)

        if handshake.get("type") != "mesh_handshake":
            await websocket.close(code=4001, reason="Invalid handshake")
            return

        peer_id = handshake.get("peer_id")
        if not peer_id:
            await websocket.close(code=4002, reason="Missing peer_id")
            return

        # Register this connection
        _active_mesh_connections[peer_id] = websocket

        # Get our mesh relay and register the peer
        from api.mesh_relay import get_mesh_relay
        from api.offline_mesh_discovery import get_mesh_discovery

        relay = get_mesh_relay()
        discovery = get_mesh_discovery()

        # Register as direct peer with initial latency estimate
        relay.add_direct_peer(peer_id, latency_ms=50.0)

        logger.info(f"🔗 Mesh peer connected: {peer_id} ({handshake.get('display_name', 'Unknown')})")

        # Send our handshake response
        await websocket.send_text(json.dumps({
            "type": "mesh_handshake_ack",
            "peer_id": discovery.peer_id,
            "display_name": discovery.display_name,
            "capabilities": discovery.capabilities
        }))

        # Message loop
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            msg_type = message.get("type")

            if msg_type == "mesh_message":
                # Relay message through mesh
                from api.mesh_relay import MeshMessage
                mesh_msg = MeshMessage(**message.get("message", {}))
                is_for_us = await relay.receive_message(mesh_msg)

                if is_for_us:
                    # Message was for us - emit to local handlers
                    logger.info(f"📨 Received mesh message from {mesh_msg.source_peer_id}")
                    # TODO: Dispatch to local message handlers

            elif msg_type == "route_request":
                # Peer is asking for route to a destination
                dest_peer_id = message.get("dest_peer_id")
                route = relay.get_route_to(dest_peer_id)

                await websocket.send_text(json.dumps({
                    "type": "route_response",
                    "dest_peer_id": dest_peer_id,
                    "route": route,
                    "has_route": route is not None
                }))

            elif msg_type == "route_advertisement":
                # Peer is advertising reachable routes
                relay.update_route_from_advertisement(message)

            elif msg_type == "ping":
                # Health check
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        logger.info(f"👋 Mesh peer disconnected: {peer_id}")
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON from mesh peer {peer_id}: {e}")
    except Exception as e:
        logger.error(f"Mesh connection error with {peer_id}: {e}")
    finally:
        # Cleanup
        if peer_id:
            _active_mesh_connections.pop(peer_id, None)

            # Remove from relay
            try:
                from api.mesh_relay import get_mesh_relay
                relay = get_mesh_relay()
                relay.remove_direct_peer(peer_id)
            except Exception:
                pass


def get_active_mesh_peers() -> list:
    """Get list of currently connected mesh peers"""
    return list(_active_mesh_connections.keys())


async def broadcast_to_mesh_peers(message: dict, exclude_peer: str = None):
    """Broadcast a message to all connected mesh peers"""
    data = json.dumps(message)
    for peer_id, ws in _active_mesh_connections.items():
        if peer_id != exclude_peer:
            try:
                await ws.send_text(data)
            except Exception as e:
                logger.warning(f"Failed to send to mesh peer {peer_id}: {e}")
