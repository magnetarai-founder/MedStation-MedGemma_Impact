"""
Terminal API - WebSocket endpoints for terminal I/O

Provides real-time terminal access via WebSocket for the Code Tab.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from typing import Optional
import json
import os
import subprocess

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.terminal_bridge import terminal_bridge, TerminalSession

# Import auth middleware
try:
    from auth_middleware import get_current_user
except ImportError:
    from .auth_middleware import get_current_user

try:
    from permission_engine import require_perm
except ImportError:
    from .permission_engine import require_perm

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
    cwd: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Spawn a new terminal session

    Args:
        shell: Shell to use (defaults to /bin/zsh or /bin/bash)
        cwd: Working directory (defaults to user home)

    Returns:
        Terminal session info with ID and WebSocket URL
    """
    user_id = current_user["user_id"]

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


@router.post("/spawn-system")
async def spawn_system_terminal(current_user: dict = Depends(get_current_user)):
    """
    Spawn a system terminal (Warp, iTerm2, Terminal.app) with bridge script

    This endpoint:
    1. Detects user's preferred terminal application
    2. Creates wrapper script (.elohim_bridge.sh) for I/O capture
    3. Spawns system terminal with bridge
    4. Tracks active terminal count (max 3)

    Returns:
        Active terminal count and session info
    """
    user_id = current_user["user_id"]

    try:
        # Check current session count (max 3) - use system terminal list
        active_sessions = terminal_bridge.list_system_terminals(user_id=user_id)
        active_count = len([s for s in active_sessions if s.get('active', False)])

        if active_count >= 3:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum terminal limit reached (3/3). Please close a terminal before opening a new one."
            )

        # Detect terminal application (Warp > iTerm2 > Terminal.app)
        terminal_app = None
        if os.path.exists('/Applications/Warp.app'):
            terminal_app = 'warp'
        elif os.path.exists('/Applications/iTerm.app'):
            terminal_app = 'iterm'
        else:
            terminal_app = 'terminal'  # Default macOS Terminal

        # Create bridge script in user's home directory
        home_dir = os.path.expanduser('~')
        bridge_script_path = os.path.join(home_dir, '.elohim_bridge.sh')

        # Get workspace root from marker file if exists
        from config_paths import PATHS
        marker_file = PATHS.data_dir / "current_workspace.txt"
        workspace_root = home_dir  # default
        if marker_file.exists():
            workspace_root = marker_file.read_text().strip()

        # Create bridge wrapper script
        bridge_script_content = f"""#!/bin/bash
# ElohimOS Terminal Bridge
# This script transparently captures terminal I/O while maintaining normal shell behavior

# Source user's shell config
if [ -f "$HOME/.zshrc" ]; then
    source "$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    source "$HOME/.bashrc"
fi

# Change to workspace directory
cd "{workspace_root}"

# TODO: Set up socket connection to ElohimOS backend
# For now, just spawn shell normally
exec $SHELL
"""

        # Write bridge script
        with open(bridge_script_path, 'w') as f:
            f.write(bridge_script_content)

        # Make executable
        os.chmod(bridge_script_path, 0o755)

        # Register system terminal session
        terminal_id = terminal_bridge.register_system_terminal(
            user_id=user_id,
            terminal_app=terminal_app,
            workspace_root=workspace_root
        )

        # Spawn terminal with bridge script
        if terminal_app == 'warp':
            # Warp CLI: warp-cli open <path>
            subprocess.Popen([
                'open', '-a', 'Warp',
                bridge_script_path
            ])
        elif terminal_app == 'iterm':
            # iTerm2 via AppleScript
            applescript = f'''
            tell application "iTerm"
                activate
                create window with default profile
                tell current session of current window
                    write text "{bridge_script_path}"
                end tell
            end tell
            '''
            subprocess.Popen(['osascript', '-e', applescript])
        else:
            # Terminal.app via AppleScript
            applescript = f'''
            tell application "Terminal"
                activate
                do script "{bridge_script_path}"
            end tell
            '''
            subprocess.Popen(['osascript', '-e', applescript])

        # Update active count
        active_count += 1

        await log_action(
            user_id,
            'terminal.spawn_system',
            {
                'terminal_app': terminal_app,
                'workspace_root': workspace_root,
                'active_terminals': active_count
            }
        )

        return {
            'success': True,
            'terminal_id': terminal_id,
            'terminal_app': terminal_app,
            'active_terminals': active_count,
            'max_terminals': 3,
            'bridge_script': bridge_script_path
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to spawn system terminal: {str(e)}")


@router.get("/sessions")
async def list_terminal_sessions(current_user: dict = Depends(get_current_user)):
    """
    List all terminal sessions for current user

    Returns:
        List of active terminal sessions
    """
    user_id = current_user["user_id"]
    sessions = terminal_bridge.list_sessions(user_id=user_id)

    return {
        'sessions': sessions,
        'count': len(sessions)
    }


@router.get("/{terminal_id}")
async def get_terminal_session(terminal_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get terminal session info

    Args:
        terminal_id: Terminal session ID

    Returns:
        Session info
    """
    user_id = current_user["user_id"]
    session = terminal_bridge.get_session(terminal_id)

    if not session:
        raise HTTPException(status_code=404, detail="Terminal not found")

    # Check ownership
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        'id': session.id,
        'user_id': session.user_id,
        'active': session.active,
        'created_at': session.created_at.isoformat(),
        'pid': session.process.pid
    }


@router.delete("/{terminal_id}")
async def close_terminal_session(terminal_id: str, current_user: dict = Depends(get_current_user)):
    """
    Close a terminal session

    Args:
        terminal_id: Terminal session ID

    Returns:
        Success message
    """
    user_id = current_user["user_id"]
    session = terminal_bridge.get_session(terminal_id)

    if not session:
        raise HTTPException(status_code=404, detail="Terminal not found")

    # Check ownership
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

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
    lines: int = Query(default=100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user)
):
    """
    Get terminal context (recent output) for AI/LLM

    Args:
        terminal_id: Terminal session ID
        lines: Number of recent lines to return (default 100, max 1000)

    Returns:
        Recent terminal output as context
    """
    user_id = current_user["user_id"]
    session = terminal_bridge.get_session(terminal_id)

    if not session:
        raise HTTPException(status_code=404, detail="Terminal not found")

    # Check ownership
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    context = terminal_bridge.get_context(terminal_id, lines=lines)

    return {
        'terminal_id': terminal_id,
        'lines': lines,
        'context': context
    }


@router.websocket("/ws/{terminal_id}")
async def terminal_websocket(websocket: WebSocket, terminal_id: str, token: Optional[str] = Query(None)):
    """
    WebSocket endpoint for real-time terminal I/O

    Args:
        websocket: WebSocket connection
        terminal_id: Terminal session ID
        token: JWT token for authentication (query param)

    Protocol:
        Client -> Server: {"type": "input", "data": "command\n"}
        Client -> Server: {"type": "resize", "rows": 24, "cols": 80}
        Server -> Client: {"type": "output", "data": "command output"}
        Server -> Client: {"type": "error", "message": "error message"}
    """
    # Authenticate before accepting connection
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return

    try:
        from auth_middleware import auth_service
    except ImportError:
        from .auth_middleware import auth_service

    user_payload = auth_service.verify_token(token)
    if not user_payload:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    user_id = user_payload["user_id"]

    await websocket.accept()

    session = terminal_bridge.get_session(terminal_id)

    if not session:
        await websocket.send_json({
            'type': 'error',
            'message': 'Terminal not found'
        })
        await websocket.close()
        return

    # Check ownership
    if session.user_id != user_id:
        await websocket.send_json({
            'type': 'error',
            'message': 'Access denied'
        })
        await websocket.close()
        return

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
    cols: int = Query(..., ge=1, le=1000),
    current_user: dict = Depends(get_current_user)
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
    user_id = current_user["user_id"]
    session = terminal_bridge.get_session(terminal_id)

    if not session:
        raise HTTPException(status_code=404, detail="Terminal not found")

    # Check ownership
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    await terminal_bridge.resize_terminal(terminal_id, rows, cols)

    return {
        'success': True,
        'rows': rows,
        'cols': cols
    }


# ==================== Bash Assist Mode ====================

try:
    from .bash_intelligence import get_bash_intelligence
    from .unified_context import get_unified_context
except ImportError:
    from bash_intelligence import get_bash_intelligence
    from unified_context import get_unified_context

from pydantic import BaseModel


class BashAssistRequest(BaseModel):
    """Request for bash assist"""
    input: str
    session_id: Optional[str] = None
    cwd: Optional[str] = None


class BashAssistResponse(BaseModel):
    """Response from bash assist"""
    input_type: str  # 'nl', 'bash', 'ambiguous'
    confidence: float
    suggested_command: Optional[str]
    is_safe: bool
    safety_warning: Optional[str]
    improvements: list[str]


@router.post("/assist", response_model=BashAssistResponse)
async def bash_assist(
    request: Request,
    body: BashAssistRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Intelligent bash assist - translate NL to bash, check safety

    Features:
    - Natural language → bash translation
    - Command safety checking
    - Context-aware suggestions
    - Integrated with unified context

    Rate limited: 30/min per user
    """
    user_id = current_user["user_id"]

    # Rate limiting
    try:
        from .rate_limiter import rate_limiter
    except ImportError:
        from rate_limiter import rate_limiter

    if not rate_limiter.check_rate_limit(
        f"terminal:assist:{user_id}",
        max_requests=30,
        window_seconds=60
    ):
        raise HTTPException(status_code=429, detail="Too many assist requests. Please try again later.")

    # Get bash intelligence
    bash_intel = get_bash_intelligence()

    # Classify input
    classification = bash_intel.classify_input(body.input)

    # Get suggested command
    suggested_cmd = classification.get('suggestion')
    if not suggested_cmd and classification['type'] == 'bash':
        suggested_cmd = body.input

    # Check safety
    is_safe = True
    safety_warning = None
    if suggested_cmd:
        is_safe, safety_warning = bash_intel.check_safety(suggested_cmd)

    # Get improvements
    improvements = []
    if suggested_cmd:
        improvements = bash_intel.suggest_improvements(suggested_cmd)

    # Add to unified context
    if body.session_id:
        context_mgr = get_unified_context()
        context_mgr.add_entry(
            user_id=user_id,
            session_id=body.session_id,
            source='terminal',
            entry_type='command',
            content=suggested_cmd or body.input,
            metadata={
                'original_input': body.input,
                'input_type': classification['type'],
                'is_safe': is_safe,
                'cwd': body.cwd
            }
        )

    return BashAssistResponse(
        input_type=classification['type'],
        confidence=classification['confidence'],
        suggested_command=suggested_cmd,
        is_safe=is_safe,
        safety_warning=safety_warning,
        improvements=improvements
    )
