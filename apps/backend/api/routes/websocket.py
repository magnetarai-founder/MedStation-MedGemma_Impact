"""
WebSocket API endpoints.

Real-time WebSocket connections for query progress, streaming updates, and mesh networking.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, UTC
from typing import Dict, Callable, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.main import sessions
from api.core.state import update_progress_stream, delete_progress_stream

router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger(__name__)


# ===== Progress Streaming Helper =====

class QueryProgressStreamer:
    """
    Streams query execution progress over WebSocket.

    Phases:
    1. Parsing (0-10%)
    2. Validation (10-20%)
    3. Planning (20-30%)
    4. Execution (30-90%)
    5. Formatting (90-100%)
    """

    def __init__(self, websocket: WebSocket, task_id: str):
        self.websocket = websocket
        self.task_id = task_id
        self.start_time = time.time()
        self.current_phase = "initializing"
        self.current_progress = 0

    async def send_progress(self, phase: str, progress: int, message: str, details: Dict[str, Any] = None):
        """Send a progress update to the WebSocket client."""
        self.current_phase = phase
        self.current_progress = progress

        payload = {
            "type": "progress",
            "task_id": self.task_id,
            "phase": phase,
            "progress": progress,
            "message": message,
            "elapsed_ms": int((time.time() - self.start_time) * 1000)
        }

        if details:
            payload["details"] = details

        # Update central progress tracking
        update_progress_stream(
            self.task_id,
            status=phase,
            progress=progress,
            message=message,
            updated_at=datetime.now(UTC).isoformat()
        )

        await self.websocket.send_json(payload)

    async def parsing(self, sql: str):
        """Phase 1: SQL parsing"""
        await self.send_progress(
            "parsing", 5,
            "Parsing SQL query...",
            {"query_length": len(sql)}
        )

    async def validating(self, tables: list):
        """Phase 2: Security validation"""
        await self.send_progress(
            "validating", 15,
            f"Validating access to {len(tables)} table(s)...",
            {"tables": tables}
        )

    async def planning(self):
        """Phase 3: Query planning"""
        await self.send_progress(
            "planning", 25,
            "Planning query execution..."
        )

    async def executing(self, rows_processed: int = 0, total_rows: int = None):
        """Phase 4: Query execution with row count updates"""
        if total_rows and total_rows > 0:
            exec_progress = min(85, 30 + int((rows_processed / total_rows) * 55))
            message = f"Processing rows: {rows_processed:,} / {total_rows:,}"
        else:
            exec_progress = 60
            message = f"Executing query... ({rows_processed:,} rows processed)"

        await self.send_progress(
            "executing", exec_progress,
            message,
            {"rows_processed": rows_processed, "total_rows": total_rows}
        )

    async def formatting(self, row_count: int):
        """Phase 5: Formatting results"""
        await self.send_progress(
            "formatting", 95,
            f"Formatting {row_count:,} result rows...",
            {"row_count": row_count}
        )

    async def complete(self, row_count: int, execution_time_ms: float):
        """Send completion message"""
        await self.websocket.send_json({
            "type": "complete",
            "task_id": self.task_id,
            "row_count": row_count,
            "execution_time_ms": execution_time_ms,
            "total_elapsed_ms": int((time.time() - self.start_time) * 1000)
        })

        # Update and cleanup progress tracking
        update_progress_stream(
            self.task_id,
            status="complete",
            progress=100,
            message=f"Query complete: {row_count:,} rows",
            updated_at=datetime.now(UTC).isoformat()
        )

    async def error(self, message: str, phase: str = None):
        """Send error message"""
        await self.websocket.send_json({
            "type": "error",
            "task_id": self.task_id,
            "phase": phase or self.current_phase,
            "message": message,
            "elapsed_ms": int((time.time() - self.start_time) * 1000)
        })

        # Update progress tracking with error
        update_progress_stream(
            self.task_id,
            status="error",
            progress=self.current_progress,
            message=message,
            updated_at=datetime.now(UTC).isoformat()
        )

    def cleanup(self):
        """Clean up progress tracking"""
        delete_progress_stream(self.task_id)

# Track active mesh connections
_active_mesh_connections: Dict[str, WebSocket] = {}

# Local mesh message handlers (callback functions for different message types)
_mesh_message_handlers: Dict[str, list[Callable]] = {}


def register_mesh_handler(message_type: str, handler: Callable) -> None:
    """
    Register a handler for a specific mesh message type.

    Args:
        message_type: The type of message to handle (e.g., "chat", "file_transfer", "sync")
        handler: Async callable that receives (source_peer_id, payload) and returns response or None
    """
    if message_type not in _mesh_message_handlers:
        _mesh_message_handlers[message_type] = []
    _mesh_message_handlers[message_type].append(handler)
    logger.debug(f"Registered mesh handler for message type: {message_type}")


def unregister_mesh_handler(message_type: str, handler: Callable) -> bool:
    """
    Unregister a mesh message handler.

    Returns True if handler was found and removed.
    """
    if message_type in _mesh_message_handlers:
        try:
            _mesh_message_handlers[message_type].remove(handler)
            return True
        except ValueError:
            pass
    return False


async def dispatch_mesh_message(source_peer_id: str, message_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch a mesh message to all registered handlers.

    Args:
        source_peer_id: The peer that sent the message
        message_type: Type of message (from message payload)
        payload: The message payload

    Returns:
        Combined response from handlers, or acknowledgment
    """
    handlers = _mesh_message_handlers.get(message_type, [])

    if not handlers:
        logger.debug(f"No handlers registered for mesh message type: {message_type}")
        return {"status": "unhandled", "message_type": message_type}

    responses = []
    for handler in handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(source_peer_id, payload)
            else:
                result = handler(source_peer_id, payload)

            if result:
                responses.append(result)
        except (ValueError, TypeError) as e:
            logger.warning(f"Mesh handler validation error for {message_type}: {e}")
            responses.append({"error": f"validation: {e}"})
        except (asyncio.TimeoutError, TimeoutError) as e:
            logger.warning(f"Mesh handler timeout for {message_type}: {e}")
            responses.append({"error": "timeout"})
        except Exception as e:
            logger.error(f"Mesh handler unexpected error for {message_type}: {type(e).__name__}: {e}")
            responses.append({"error": str(e)})

    return {
        "status": "handled",
        "message_type": message_type,
        "handler_count": len(handlers),
        "responses": responses
    }


@router.websocket("/api/sessions/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time query progress and logs"""
    if session_id not in sessions:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    logger.info(f"WebSocket connected for session {session_id}")

    try:
        while True:
            # Receive query request
            data = await websocket.receive_json()

            if data.get("type") == "query":
                # Generate task ID for tracking
                task_id = data.get("task_id") or str(uuid.uuid4())
                sql_query = data.get("sql", "")

                # Create progress streamer
                progress = QueryProgressStreamer(websocket, task_id)

                try:
                    # Phase 1: Parsing
                    await progress.parsing(sql_query)
                    await asyncio.sleep(0.05)  # Small delay for UI responsiveness

                    # Phase 2: Security validation
                    from neutron_utils.sql_utils import SQLProcessor as SQLUtil
                    referenced_tables = SQLUtil.extract_table_names(sql_query)
                    allowed_tables = {'excel_file'}

                    await progress.validating(list(referenced_tables))
                    await asyncio.sleep(0.05)

                    unauthorized_tables = set(referenced_tables) - allowed_tables
                    if unauthorized_tables:
                        await progress.error(
                            f"Query references unauthorized tables: {', '.join(unauthorized_tables)}",
                            phase="validating"
                        )
                        continue

                    # Phase 3: Planning
                    await progress.planning()
                    await asyncio.sleep(0.05)

                    # Phase 4: Execution with progress updates
                    await progress.executing(rows_processed=0)

                    engine = sessions[session_id]['engine']
                    exec_start = time.time()

                    # Execute the query
                    result = engine.execute_sql(sql_query)

                    exec_time_ms = (time.time() - exec_start) * 1000

                    if result.error:
                        await progress.error(result.error, phase="executing")
                        continue

                    # Phase 5: Formatting
                    await progress.formatting(result.row_count)
                    await asyncio.sleep(0.05)

                    # Complete
                    await progress.complete(
                        row_count=result.row_count,
                        execution_time_ms=exec_time_ms
                    )

                except (ValueError, TypeError) as e:
                    logger.warning(f"Query validation error: {e}")
                    await progress.error(f"Invalid query: {e}")
                except KeyError as e:
                    logger.warning(f"Query resource not found: {e}")
                    await progress.error(f"Resource not found: {e}")
                except (asyncio.TimeoutError, TimeoutError) as e:
                    logger.warning(f"Query timeout: {e}")
                    await progress.error("Query execution timed out")
                except Exception as e:
                    logger.error(f"Query execution error ({type(e).__name__}): {e}")
                    await progress.error(str(e))

                finally:
                    # Schedule cleanup after a delay (allow clients to read final state)
                    asyncio.get_event_loop().call_later(60, progress.cleanup)

            elif data.get("type") == "cancel":
                # Handle query cancellation
                task_id = data.get("task_id")
                if task_id:
                    delete_progress_stream(task_id)
                    await websocket.send_json({
                        "type": "cancelled",
                        "task_id": task_id,
                        "message": "Query cancelled"
                    })

            elif data.get("type") == "ping":
                # Health check
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except json.JSONDecodeError as e:
        logger.warning(f"WebSocket JSON error for session {session_id}: {e}")
        try:
            await websocket.send_json({"type": "error", "message": "Invalid JSON format"})
        except (WebSocketDisconnect, ConnectionError, RuntimeError):
            pass  # Connection already closed
    except (ConnectionError, OSError) as e:
        logger.warning(f"WebSocket connection error for session {session_id}: {e}")
    except Exception as e:
        logger.error(f"WebSocket unexpected error for session {session_id} ({type(e).__name__}): {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except (WebSocketDisconnect, ConnectionError, RuntimeError):
            pass  # Connection already closed


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
                    # Message was for us - dispatch to local handlers
                    logger.info(f"📨 Received mesh message from {mesh_msg.source_peer_id}")

                    # Extract message type and payload from the mesh message
                    inner_type = mesh_msg.payload.get("type", "unknown")
                    inner_payload = mesh_msg.payload

                    # Dispatch to registered handlers
                    dispatch_result = await dispatch_mesh_message(
                        source_peer_id=mesh_msg.source_peer_id,
                        message_type=inner_type,
                        payload=inner_payload
                    )

                    # Send acknowledgment back to sender if they requested it
                    if mesh_msg.payload.get("request_ack"):
                        await websocket.send_text(json.dumps({
                            "type": "mesh_ack",
                            "message_id": mesh_msg.message_id,
                            "source_peer_id": mesh_msg.source_peer_id,
                            "result": dispatch_result
                        }))

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
    except (ConnectionError, OSError) as e:
        logger.warning(f"Mesh connection error with {peer_id}: {e}")
    except Exception as e:
        logger.error(f"Mesh unexpected error with {peer_id} ({type(e).__name__}): {e}")
    finally:
        # Cleanup
        if peer_id:
            _active_mesh_connections.pop(peer_id, None)

            # Remove from relay
            try:
                from api.mesh_relay import get_mesh_relay
                relay = get_mesh_relay()
                relay.remove_direct_peer(peer_id)
            except (ImportError, AttributeError, KeyError):
                pass  # Relay not available or peer not registered


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
            except (WebSocketDisconnect, ConnectionError, RuntimeError) as e:
                logger.debug(f"Mesh peer {peer_id} disconnected during broadcast: {e}")
            except Exception as e:
                logger.warning(f"Failed to send to mesh peer {peer_id} ({type(e).__name__}): {e}")
