"""
Terminal API - WebSocket endpoints for terminal I/O

Provides real-time terminal access via WebSocket for the Code Tab.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from typing import Optional
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.terminal_bridge import terminal_bridge, TerminalSession

# Permission checking (TODO: integrate with full auth system)
try:
    from permissions import require_permission
except ImportError:
    # Fallback for testing
    def require_permission(perm: str):
        async def _get_user():
            return {"user_id": "default_user", "role": "admin"}
        return _get_user

# Audit logging
try:
    from audit_logger import log_action
except ImportError:
    # Fallback for testing
    async def log_action(user_id: str, action: str, details):
        print(f"[AUDIT] {user_id} - {action} - {details}")

router = APIRouter(prefix="/api/v1/terminal", tags=["terminal"])


@router.post("/spawn")
async def spawn_terminal(
    shell: Optional[str] = None,
    cwd: Optional[str] = None
):
    """
    Spawn a new terminal session

    Args:
        shell: Shell to use (defaults to /bin/zsh or /bin/bash)
        cwd: Working directory (defaults to user home)

    Returns:
        Terminal session info with ID and WebSocket URL
    """
    # For now, use default user until auth is fully wired
    user_id = "default_user"

    try:
        session = await terminal_bridge.spawn_terminal(
            user_id=user_id,
            shell=shell,
            cwd=cwd
        )

        await log_action(
            user_id,
            'terminal.spawn',
            {'terminal_id': session.id, 'shell': shell, 'cwd': cwd}
        )

        return {
            'terminal_id': session.id,
            'websocket_url': f'/api/v1/terminal/ws/{session.id}',
            'created_at': session.created_at.isoformat(),
            'pid': session.process.pid
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to spawn terminal: {str(e)}")


@router.get("/sessions")
async def list_terminal_sessions():
    """
    List all terminal sessions for current user

    Returns:
        List of active terminal sessions
    """
    user_id = "default_user"
    sessions = terminal_bridge.list_sessions(user_id=user_id)

    return {
        'sessions': sessions,
        'count': len(sessions)
    }


@router.get("/{terminal_id}")
async def get_terminal_session(terminal_id: str):
    """
    Get terminal session info

    Args:
        terminal_id: Terminal session ID

    Returns:
        Session info
    """
    session = terminal_bridge.get_session(terminal_id)

    if not session:
        raise HTTPException(status_code=404, detail="Terminal not found")

    # TODO: Check ownership when auth is implemented
    # if session.user_id != current_user['user_id']:
    #     raise HTTPException(status_code=403, detail="Access denied")

    return {
        'id': session.id,
        'user_id': session.user_id,
        'active': session.active,
        'created_at': session.created_at.isoformat(),
        'pid': session.process.pid
    }


@router.delete("/{terminal_id}")
async def close_terminal_session(terminal_id: str):
    """
    Close a terminal session

    Args:
        terminal_id: Terminal session ID

    Returns:
        Success message
    """
    user_id = "default_user"
    session = terminal_bridge.get_session(terminal_id)

    if not session:
        raise HTTPException(status_code=404, detail="Terminal not found")

    # TODO: Check ownership when auth is implemented
    # if session.user_id != user_id:
    #     raise HTTPException(status_code=403, detail="Access denied")

    await terminal_bridge.close_terminal(terminal_id)

    await log_action(
        user_id,
        'terminal.close',
        {'terminal_id': terminal_id}
    )

    return {
        'success': True,
        'message': f'Terminal {terminal_id} closed'
    }


@router.get("/{terminal_id}/context")
async def get_terminal_context(
    terminal_id: str,
    lines: int = Query(default=100, ge=1, le=1000)
):
    """
    Get terminal context (recent output) for AI/LLM

    Args:
        terminal_id: Terminal session ID
        lines: Number of recent lines to return (default 100, max 1000)

    Returns:
        Recent terminal output as context
    """
    session = terminal_bridge.get_session(terminal_id)

    if not session:
        raise HTTPException(status_code=404, detail="Terminal not found")

    # TODO: Check ownership when auth is implemented
    # if session.user_id != user_id:
    #     raise HTTPException(status_code=403, detail="Access denied")

    context = terminal_bridge.get_context(terminal_id, lines=lines)

    return {
        'terminal_id': terminal_id,
        'lines': lines,
        'context': context
    }


@router.websocket("/ws/{terminal_id}")
async def terminal_websocket(websocket: WebSocket, terminal_id: str):
    """
    WebSocket endpoint for real-time terminal I/O

    Args:
        websocket: WebSocket connection
        terminal_id: Terminal session ID

    Protocol:
        Client -> Server: {"type": "input", "data": "command\n"}
        Client -> Server: {"type": "resize", "rows": 24, "cols": 80}
        Server -> Client: {"type": "output", "data": "command output"}
        Server -> Client: {"type": "error", "message": "error message"}
    """
    await websocket.accept()

    session = terminal_bridge.get_session(terminal_id)

    if not session:
        await websocket.send_json({
            'type': 'error',
            'message': 'Terminal not found'
        })
        await websocket.close()
        return

    # TODO: Add user authentication check via WebSocket
    # For now, rely on session ownership validation

    # Register broadcast callback for this WebSocket
    async def send_output(data: str):
        """Callback to send terminal output to WebSocket"""
        try:
            await websocket.send_json({
                'type': 'output',
                'data': data
            })
        except Exception as e:
            print(f"Error sending to WebSocket: {e}")

    terminal_bridge.register_broadcast_callback(terminal_id, send_output)

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

            try:
                data = json.loads(message)
                msg_type = data.get('type')

                if msg_type == 'input':
                    # User input (commands, keystrokes)
                    input_data = data.get('data', '')
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
                await terminal_bridge.write_to_terminal(terminal_id, message)

            except Exception as e:
                await websocket.send_json({
                    'type': 'error',
                    'message': str(e)
                })

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for terminal {terminal_id}")

    except Exception as e:
        print(f"WebSocket error for terminal {terminal_id}: {e}")

    finally:
        # Cleanup
        terminal_bridge.unregister_broadcast_callback(terminal_id, send_output)

        # Optionally close terminal when WebSocket disconnects
        # For now, keep terminal alive for reconnection
        # await terminal_bridge.close_terminal(terminal_id)


@router.post("/{terminal_id}/resize")
async def resize_terminal(
    terminal_id: str,
    rows: int = Query(..., ge=1, le=1000),
    cols: int = Query(..., ge=1, le=1000)
):
    """
    Resize terminal window (HTTP endpoint as alternative to WebSocket)

    Args:
        terminal_id: Terminal session ID
        rows: Number of rows
        cols: Number of columns

    Returns:
        Success message
    """
    session = terminal_bridge.get_session(terminal_id)

    if not session:
        raise HTTPException(status_code=404, detail="Terminal not found")

    # TODO: Check ownership when auth is implemented
    # if session.user_id != user_id:
    #     raise HTTPException(status_code=403, detail="Access denied")

    await terminal_bridge.resize_terminal(terminal_id, rows, cols)

    return {
        'success': True,
        'rows': rows,
        'cols': cols
    }
