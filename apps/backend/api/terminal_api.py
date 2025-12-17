"""
Terminal API - WebSocket endpoints for terminal I/O

Provides real-time terminal access via WebSocket for the Code Tab.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, Request
from typing import Optional
import json
import os
import subprocess

import sys
from pathlib import Path

# Import terminal bridge from parent services directory
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

# WebSocket rate limiting and security
# Track active connections per IP to prevent DoS
import time
import re
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta

MAX_WS_CONNECTIONS_PER_IP = 5
MAX_WS_CONNECTIONS_TOTAL = 100
MAX_SESSION_DURATION_SEC = 30 * 60  # 30 minutes
MAX_INACTIVITY_SEC = 5 * 60  # 5 minutes
MAX_INPUT_SIZE = 16 * 1024  # 16 KB
MAX_OUTPUT_BURST = 20  # Max messages per tick

_ws_connections_by_ip: defaultdict[str, int] = defaultdict(int)
_total_ws_connections: int = 0
_ws_connection_lock = None  # Will initialize as asyncio.Lock when needed
_session_metadata: dict = {}  # Track session start time and last activity

# Regex patterns for secret detection (basic)
SECRET_PATTERNS = [
    re.compile(r'(?i)(password|pwd|passwd)\s*[=:]\s*["\']?([^\s"\']+)', re.IGNORECASE),
    re.compile(r'(?i)(token|secret|key|api[_-]?key)\s*[=:]\s*["\']?([^\s"\']+)', re.IGNORECASE),
    re.compile(r'(?i)(aws_access_key|aws_secret)', re.IGNORECASE),
    re.compile(r'[A-Za-z0-9+/]{40,}={0,2}', re.IGNORECASE),  # Base64-ish strings
]

def redact_secrets(text: str) -> str:
    """Redact potential secrets from audit logs"""
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub('[REDACTED]', redacted)
    return redacted


@router.post("/spawn")
@require_perm("code.terminal")
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

    # HIGH-09: Enforce server-side terminal session limit (max 3 per user)
    active_sessions = terminal_bridge.list_sessions(user_id=user_id)
    active_count = len([s for s in active_sessions if s.active])

    if active_count >= 3:
        raise HTTPException(
            status_code=429,  # Too Many Requests
            detail="Maximum terminal limit reached (3/3). Please close a terminal before opening a new one."
        )

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
@require_perm("code.terminal")
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
        import shlex
        marker_file = PATHS.data_dir / "current_workspace.txt"
        workspace_root = home_dir  # default
        if marker_file.exists():
            workspace_root_raw = marker_file.read_text().strip()

            # Validate workspace path to prevent command injection
            workspace_path = Path(workspace_root_raw)
            if workspace_path.is_dir():
                # Normalize path and escape for shell
                workspace_root = str(workspace_path.resolve())
            else:
                logger.warning(f"Invalid workspace path: {workspace_root_raw}, using home directory")
                workspace_root = home_dir

        # Create bridge wrapper script
        # Use shlex.quote() to prevent shell injection via workspace path
        safe_workspace = shlex.quote(workspace_root)
        bridge_script_content = f"""#!/bin/bash
# ElohimOS Terminal Bridge
# This script transparently captures terminal I/O while maintaining normal shell behavior

# Source user's shell config
if [ -f "$HOME/.zshrc" ]; then
    source "$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    source "$HOME/.bashrc"
fi

# Change to workspace directory (path is shell-escaped for security)
cd {safe_workspace}

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

        # Spawn terminal with bridge script (robust fallbacks)
        def _run(cmd: list[str]) -> bool:
            try:
                p = subprocess.run(cmd, capture_output=True, text=True)
                return p.returncode == 0
            except Exception:
                return False

        def _open_with_app(app_name: str, path: str) -> bool:
            return _run(['open', '-a', app_name, path])

        spawned = False
        try:
            if terminal_app == 'warp':
                # Prefer direct open; fallback to Terminal
                spawned = _open_with_app('Warp', bridge_script_path)
                if not spawned:
                    terminal_app = 'terminal'
            if terminal_app == 'iterm' and not spawned:
                # SECURITY: Use subprocess list args instead of AppleScript string interpolation
                # to prevent command injection via bridge_script_path
                spawned = _open_with_app('iTerm', bridge_script_path)
                if not spawned:
                    terminal_app = 'terminal'
            if terminal_app == 'terminal' and not spawned:
                # SECURITY: Use open -a instead of AppleScript to avoid injection
                # AppleScript with f-string interpolation is a command injection vector
                spawned = _open_with_app('Terminal', bridge_script_path)
        except Exception:
            spawned = False

        if not spawned:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Failed to spawn system terminal. Ensure Terminal/iTerm/Warp are installed and that this app "
                    "has permission to control your computer (System Settings → Privacy & Security → Automation/Accessibility)."
                )
            )

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


@router.post("/socket/start")
@require_perm("code.terminal")
async def start_terminal_socket(
    request: Request,
    terminal_app: Optional[str] = None,
    workspace_root: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Start a Unix socket listener for external terminal output capture

    Creates a socket that external terminal processes can write to.
    The TerminalBridge will broadcast captured output to subscribers.

    Args:
        terminal_app: Name of terminal application (e.g., 'iTerm2', 'Warp')
        workspace_root: Working directory for the terminal session

    Returns:
        terminal_id: Session ID
        socket_path: Path to Unix socket for external process to connect
    """
    user_id = current_user["user_id"]

    try:
        # Import PATHS
        try:
            from config_paths import PATHS
        except ImportError:
            from .config_paths import PATHS

        # Register system terminal session
        terminal_id = terminal_bridge.register_system_terminal(
            user_id=user_id,
            terminal_app=terminal_app or "unknown",
            workspace_root=workspace_root or str(Path.home())
        )

        # Compute socket path under data_dir
        socket_path = PATHS.data_dir / f"term_{terminal_id}.sock"

        # Validate socket path is inside data_dir (security check)
        if not str(socket_path).startswith(str(PATHS.data_dir)):
            raise HTTPException(status_code=400, detail="Invalid socket path")

        # Start socket listener in background (non-blocking)
        asyncio.create_task(terminal_bridge.start_socket_listener(str(socket_path), terminal_id))

        # Log the operation
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Terminal socket started: user={user_id}, terminal_id={terminal_id}, socket_path={socket_path}")

        return {
            "terminal_id": terminal_id,
            "socket_path": str(socket_path)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start socket listener: {str(e)}")


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
    global _total_ws_connections, _ws_connection_lock

    # Initialize lock on first use
    if _ws_connection_lock is None:
        import asyncio
        _ws_connection_lock = asyncio.Lock()

    # Rate limiting check
    client_ip = websocket.client.host if websocket.client else "unknown"

    async with _ws_connection_lock:
        # Check global limit
        if _total_ws_connections >= MAX_WS_CONNECTIONS_TOTAL:
            await websocket.close(code=1008, reason="Server at capacity")
            return

        # Check per-IP limit
        if _ws_connections_by_ip[client_ip] >= MAX_WS_CONNECTIONS_PER_IP:
            await websocket.close(code=1008, reason="Too many connections from your IP")
            return

        # Increment counters
        _ws_connections_by_ip[client_ip] += 1
        _total_ws_connections += 1

    # Authenticate before accepting connection
    if not token:
        # Decrement counters on early exit
        async with _ws_connection_lock:
            _ws_connections_by_ip[client_ip] -= 1
            _total_ws_connections -= 1
        await websocket.close(code=1008, reason="Missing authentication token")
        return

    try:
        from auth_middleware import auth_service
    except ImportError:
        from .auth_middleware import auth_service

    user_payload = auth_service.verify_token(token)
    if not user_payload:
        # Decrement counters on auth failure
        async with _ws_connection_lock:
            _ws_connections_by_ip[client_ip] -= 1
            _total_ws_connections -= 1
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    user_id = user_payload["user_id"]

    await websocket.accept()

    session = terminal_bridge.get_session(terminal_id)

    if not session:
        # Decrement counters on session not found
        async with _ws_connection_lock:
            _ws_connections_by_ip[client_ip] -= 1
            _total_ws_connections -= 1
        await websocket.send_json({
            'type': 'error',
            'message': 'Terminal not found'
        })
        await websocket.close()
        return

    # Check ownership
    if session.user_id != user_id:
        # Decrement counters on access denied
        async with _ws_connection_lock:
            _ws_connections_by_ip[client_ip] -= 1
            _total_ws_connections -= 1
        await websocket.send_json({
            'type': 'error',
            'message': 'Access denied'
        })
        await websocket.close()
        return

    # Initialize session metadata for TTL and inactivity tracking
    session_start = datetime.utcnow()
    last_activity = datetime.utcnow()
    _session_metadata[terminal_id] = {
        'start': session_start,
        'last_activity': last_activity
    }

    # Output throttling state
    output_queue = []

    # Register broadcast callback for this WebSocket with throttling
    async def send_output(data: str):
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
            print(f"Error sending to WebSocket: {e}")

    terminal_bridge.register_broadcast_callback(terminal_id, send_output)

    # Background task to check TTL and inactivity
    async def check_timeouts():
        """Check session TTL and inactivity, close if exceeded"""
        while session.active:
            await asyncio.sleep(60)  # Check every minute

            now = datetime.utcnow()
            metadata = _session_metadata.get(terminal_id)
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
            _session_metadata[terminal_id]['last_activity'] = datetime.utcnow()

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
        print(f"WebSocket disconnected for terminal {terminal_id}")

    except Exception as e:
        print(f"WebSocket error for terminal {terminal_id}: {e}")

    finally:
        # Cancel timeout task
        timeout_task.cancel()

        # Cleanup
        terminal_bridge.unregister_broadcast_callback(terminal_id, send_output)

        # Clean up session metadata
        if terminal_id in _session_metadata:
            del _session_metadata[terminal_id]

        # Decrement WebSocket connection counters
        async with _ws_connection_lock:
            _ws_connections_by_ip[client_ip] -= 1
            _total_ws_connections -= 1
            # Clean up empty IP entries
            if _ws_connections_by_ip[client_ip] == 0:
                del _ws_connections_by_ip[client_ip]

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
        try:
            from .workspace_session import get_workspace_session_manager

            context_mgr = get_unified_context()
            ws_mgr = get_workspace_session_manager()

            # Ensure session_id is a workspace session
            # If passed session_id looks like a terminal/chat ID, create/get workspace session
            workspace_session_id = body.session_id
            if not workspace_session_id.startswith('ws_'):
                # Try to get workspace session, creating if needed
                workspace_session_id = ws_mgr.get_or_create_for_workspace(
                    user_id=user_id,
                    workspace_root=body.cwd or str(Path.home())
                )

            context_mgr.add_entry(
                user_id=user_id,
                session_id=workspace_session_id,
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
        except Exception as e:
            logger.warning(f"Failed to add to unified context: {e}")

    return BashAssistResponse(
        input_type=classification['type'],
        confidence=classification['confidence'],
        suggested_command=suggested_cmd,
        is_safe=is_safe,
        safety_warning=safety_warning,
        improvements=improvements
    )
