"""
Terminal WebSocket Handler

Real-time terminal I/O via WebSocket.
"""

import asyncio
import json
import logging
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect, Query

from api.auth_middleware import extract_websocket_token
from api.terminal.constants import (
    MAX_WS_CONNECTIONS_PER_IP,
    MAX_WS_CONNECTIONS_TOTAL,
    MAX_SESSION_DURATION_SEC,
    MAX_INACTIVITY_SEC,
    MAX_INPUT_SIZE,
    MAX_OUTPUT_BURST,
    get_ws_connection_lock,
    get_ws_connections_by_ip,
    get_total_ws_connections,
    increment_ws_connections,
    decrement_ws_connections,
    get_session_metadata,
)
from api.terminal.security import redact_secrets

logger = logging.getLogger(__name__)

# Import terminal bridge
import sys
_backend_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_backend_root))

try:
    from services.terminal_bridge import terminal_bridge, TerminalSession
except ModuleNotFoundError:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "terminal_bridge",
        _backend_root / "services" / "terminal_bridge.py"
    )
    terminal_bridge_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(terminal_bridge_module)
    terminal_bridge = terminal_bridge_module.terminal_bridge
    TerminalSession = terminal_bridge_module.TerminalSession

# Audit logging
try:
    from api.audit_logger import log_action
except ImportError:
    async def log_action(user_id: str, action: str, details) -> None:
        logger.info(f"[AUDIT] {user_id} - {action} - {details}")


async def terminal_websocket(websocket: WebSocket, terminal_id: str, token: Optional[str] = Query(None)) -> None:
    """
    WebSocket endpoint for real-time terminal I/O

    Args:
        websocket: WebSocket connection
        terminal_id: Terminal session ID
        token: JWT token for authentication (query param or Sec-WebSocket-Protocol header)

    Authentication:
        - Preferred: Sec-WebSocket-Protocol header with "jwt-<token>" or "bearer.<token>"
        - Fallback: Query param ?token=xxx (deprecated)

    Protocol:
        Client -> Server: {"type": "input", "data": "command\n"}
        Client -> Server: {"type": "resize", "rows": 24, "cols": 80}
        Server -> Client: {"type": "output", "data": "command output"}
        Server -> Client: {"type": "error", "message": "error message"}
    """
    ws_lock = get_ws_connection_lock()
    ws_connections_by_ip = get_ws_connections_by_ip()
    session_metadata = get_session_metadata()

    # Rate limiting check
    client_ip = websocket.client.host if websocket.client else "unknown"

    async with ws_lock:
        # Check global limit
        if get_total_ws_connections() >= MAX_WS_CONNECTIONS_TOTAL:
            await websocket.close(code=1008, reason="Server at capacity")
            return

        # Check per-IP limit
        if ws_connections_by_ip[client_ip] >= MAX_WS_CONNECTIONS_PER_IP:
            await websocket.close(code=1008, reason="Too many connections from your IP")
            return

        # Increment counters
        increment_ws_connections(client_ip)

    # SECURITY: Extract token from header (preferred) or query param (deprecated fallback)
    auth_token = extract_websocket_token(websocket, token)

    # Authenticate before accepting connection
    if not auth_token:
        # Decrement counters on early exit
        async with ws_lock:
            decrement_ws_connections(client_ip)
        await websocket.close(code=1008, reason="Missing authentication token")
        return

    try:
        from api.auth_middleware import auth_service
    except ImportError:
        from auth_middleware import auth_service

    user_payload = auth_service.verify_token(auth_token)
    if not user_payload:
        # Decrement counters on auth failure
        async with ws_lock:
            decrement_ws_connections(client_ip)
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    user_id = user_payload["user_id"]

    await websocket.accept()

    session = terminal_bridge.get_session(terminal_id)

    if not session:
        # Decrement counters on session not found
        async with ws_lock:
            decrement_ws_connections(client_ip)
        await websocket.send_json({
            'type': 'error',
            'message': 'Terminal not found'
        })
        await websocket.close()
        return

    # Check ownership
    if session.user_id != user_id:
        # Decrement counters on access denied
        async with ws_lock:
            decrement_ws_connections(client_ip)
        await websocket.send_json({
            'type': 'error',
            'message': 'Access denied'
        })
        await websocket.close()
        return

    # Initialize session metadata for TTL and inactivity tracking
    session_start = datetime.now(UTC)
    last_activity = datetime.now(UTC)
    session_metadata[terminal_id] = {
        'start': session_start,
        'last_activity': last_activity
    }

    # Output throttling state
    output_queue = []

    # Register broadcast callback for this WebSocket with throttling
    async def send_output(data: str) -> None:
        """Callback to send terminal output to WebSocket with burst control"""
        try:
            output_queue.append(data)
            # Coalesce and send up to MAX_OUTPUT_BURST messages per tick
            if len(output_queue) >= MAX_OUTPUT_BURST:
                coalesced = ''.join(output_queue[:MAX_OUTPUT_BURST])
                output_queue.clear()
                await websocket.send_json({
                    'type': 'output',
                    'data': coalesced
                })
        except Exception as e:
            logger.warning(f"Error sending to WebSocket: {e}")

    terminal_bridge.register_broadcast_callback(terminal_id, send_output)

    # Background task to check TTL and inactivity
    async def check_timeouts() -> None:
        """Check session TTL and inactivity, close if exceeded"""
        while session.active:
            await asyncio.sleep(60)  # Check every minute

            now = datetime.now(UTC)
            metadata = session_metadata.get(terminal_id)
            if not metadata:
                break

            # Check session duration TTL
            if (now - metadata['start']).total_seconds() > MAX_SESSION_DURATION_SEC:
                await websocket.send_json({
                    'type': 'error',
                    'message': f'Session timeout after {MAX_SESSION_DURATION_SEC // 60} minutes'
                })
                await websocket.close(code=1000, reason='Session TTL exceeded')
                break

            # Check inactivity timeout
            if (now - metadata['last_activity']).total_seconds() > MAX_INACTIVITY_SEC:
                await websocket.send_json({
                    'type': 'error',
                    'message': f'Inactivity timeout after {MAX_INACTIVITY_SEC // 60} minutes'
                })
                await websocket.close(code=1000, reason='Inactivity timeout')
                break

    timeout_task = asyncio.create_task(check_timeouts())

    try:
        # Send initial buffered output
        if session.output_buffer:
            initial_output = ''.join(session.output_buffer[-100:])
            await websocket.send_json({
                'type': 'output',
                'data': initial_output
            })

        # Main WebSocket loop
        while session.active:
            # Receive message from client
            message = await websocket.receive_text()

            # Check input size limit
            if len(message) > MAX_INPUT_SIZE:
                await websocket.send_json({
                    'type': 'error',
                    'message': f'Input exceeds {MAX_INPUT_SIZE} byte limit'
                })
                await websocket.close(code=1009, reason='Message too large')
                break

            # Update last activity timestamp
            session_metadata[terminal_id]['last_activity'] = datetime.now(UTC)

            try:
                data = json.loads(message)
                msg_type = data.get('type')

                if msg_type == 'input':
                    # User input (commands, keystrokes)
                    input_data = data.get('data', '')

                    # Audit log with redaction
                    redacted_input = redact_secrets(input_data)
                    await log_action(
                        user_id,
                        'terminal.input',
                        {'terminal_id': terminal_id, 'input': redacted_input}
                    )

                    await terminal_bridge.write_to_terminal(terminal_id, input_data)

                elif msg_type == 'resize':
                    # Terminal resize
                    rows = data.get('rows', 24)
                    cols = data.get('cols', 80)
                    await terminal_bridge.resize_terminal(terminal_id, rows, cols)

                else:
                    await websocket.send_json({
                        'type': 'error',
                        'message': f'Unknown message type: {msg_type}'
                    })

            except json.JSONDecodeError:
                # Treat as raw input if not valid JSON
                redacted_message = redact_secrets(message)
                await log_action(
                    user_id,
                    'terminal.input',
                    {'terminal_id': terminal_id, 'input': redacted_message}
                )
                await terminal_bridge.write_to_terminal(terminal_id, message)

            except Exception as e:
                await websocket.send_json({
                    'type': 'error',
                    'message': str(e)
                })

    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected for terminal {terminal_id}")

    except Exception as e:
        logger.error(f"WebSocket error for terminal {terminal_id}: {e}")

    finally:
        # Cancel timeout task
        timeout_task.cancel()

        # Cleanup
        terminal_bridge.unregister_broadcast_callback(terminal_id, send_output)

        # Clean up session metadata
        if terminal_id in session_metadata:
            del session_metadata[terminal_id]

        # Decrement WebSocket connection counters
        async with ws_lock:
            decrement_ws_connections(client_ip)
