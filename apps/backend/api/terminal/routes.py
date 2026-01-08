"""
Terminal HTTP Routes

HTTP endpoints for terminal session management.
"""

import asyncio
import logging
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.routes.schemas.responses import SuccessResponse
from api.terminal.models import SpawnTerminalResponseData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/terminal", tags=["terminal"])


# ===== Imports with fallbacks =====

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

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user

try:
    from api.utils import get_user_id
except ImportError:
    from utils import get_user_id

try:
    from api.permission_engine import require_perm
except ImportError:
    from permission_engine import require_perm

# Audit logging
try:
    from api.audit_logger import log_action
except ImportError:
    async def log_action(user_id: str, action: str, details) -> None:
        logger.info(f"[AUDIT] {user_id} - {action} - {details}")


# ===== HTTP Routes =====

@router.post("/spawn", response_model=SuccessResponse[SpawnTerminalResponseData])
@require_perm("code.terminal")
async def spawn_terminal(
    shell: Optional[str] = None,
    cwd: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Spawn a new terminal session

    Args:
        shell: Shell to use (defaults to /bin/zsh or /bin/bash)
        cwd: Working directory (defaults to user home)

    Returns:
        Terminal session info with ID and WebSocket URL
    """
    user_id = get_user_id(current_user)

    # HIGH-09: Enforce server-side terminal session limit (max 3 per user)
    active_sessions = terminal_bridge.list_sessions(user_id=user_id)
    active_count = len([s for s in active_sessions if s.active])

    if active_count >= 3:
        raise HTTPException(
            status_code=429,
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


@router.post("/spawn-system", response_model=SuccessResponse[SpawnTerminalResponseData])
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
    user_id = get_user_id(current_user)

    try:
        # Check current session count (max 3) - use system terminal list
        active_sessions = terminal_bridge.list_system_terminals(user_id=user_id)
        active_count = len([s for s in active_sessions if s.get('active', False)])

        if active_count >= 3:
            raise HTTPException(
                status_code=400,
                detail="Maximum terminal limit reached (3/3). Please close a terminal before opening a new one."
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
        from api.config_paths import PATHS
        marker_file = PATHS.data_dir / "current_workspace.txt"
        workspace_root = home_dir  # default

        # Allowed workspace root directories (security whitelist)
        ALLOWED_WORKSPACE_ROOTS = [
            Path(home_dir),
            Path(home_dir) / "Documents",
            Path(home_dir) / "Projects",
            Path(home_dir) / "Developer",
            Path(home_dir) / "Code",
            Path("/tmp"),
        ]

        # Valid path character pattern (prevents command injection via special chars)
        VALID_PATH_PATTERN = re.compile(r'^[a-zA-Z0-9/_.\-\s]+$')

        if marker_file.exists():
            workspace_root_raw = marker_file.read_text().strip()

            # Step 1: Validate path characters BEFORE any Path operations
            if not VALID_PATH_PATTERN.match(workspace_root_raw):
                logger.warning(f"Invalid path characters in workspace: {workspace_root_raw!r}")
                workspace_root = home_dir
            elif not workspace_root_raw.startswith('/'):
                logger.warning(f"Workspace path must be absolute: {workspace_root_raw}")
                workspace_root = home_dir
            else:
                # Step 2: Now safe to create Path object
                workspace_path = Path(workspace_root_raw).resolve()

                # Step 3: Verify path is within allowed roots (prevent traversal)
                is_allowed = any(
                    workspace_path == allowed_root or
                    (allowed_root in workspace_path.parents)
                    for allowed_root in ALLOWED_WORKSPACE_ROOTS
                )

                if is_allowed and workspace_path.is_dir():
                    workspace_root = str(workspace_path)
                else:
                    logger.warning(f"Workspace path not in allowed directories: {workspace_path}")
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
                spawned = _open_with_app('Warp', bridge_script_path)
                if not spawned:
                    terminal_app = 'terminal'
            if terminal_app == 'iterm' and not spawned:
                spawned = _open_with_app('iTerm', bridge_script_path)
                if not spawned:
                    terminal_app = 'terminal'
            if terminal_app == 'terminal' and not spawned:
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

        return SuccessResponse(
            data=SpawnTerminalResponseData(
                terminal_id=terminal_id,
                terminal_app=terminal_app,
                workspace_root=workspace_root,
                active_count=active_count,
                message=f"Opened {terminal_app} in {workspace_root}"
            )
        )

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
) -> Dict[str, Any]:
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
    user_id = get_user_id(current_user)

    try:
        from api.config_paths import PATHS

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
async def list_terminal_sessions(current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    List all terminal sessions for current user

    Returns:
        List of active terminal sessions
    """
    user_id = get_user_id(current_user)
    sessions = terminal_bridge.list_sessions(user_id=user_id)

    return {
        'sessions': sessions,
        'count': len(sessions)
    }


@router.get("/{terminal_id}")
async def get_terminal_session(terminal_id: str, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get terminal session info

    Args:
        terminal_id: Terminal session ID

    Returns:
        Session info
    """
    user_id = get_user_id(current_user)
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
async def close_terminal_session(terminal_id: str, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Close a terminal session

    Args:
        terminal_id: Terminal session ID

    Returns:
        Success message
    """
    user_id = get_user_id(current_user)
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
) -> Dict[str, Any]:
    """
    Get terminal context (recent output) for AI/LLM

    Args:
        terminal_id: Terminal session ID
        lines: Number of recent lines to return (default 100, max 1000)

    Returns:
        Recent terminal output as context
    """
    user_id = get_user_id(current_user)
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


@router.post("/{terminal_id}/resize")
async def resize_terminal(
    terminal_id: str,
    rows: int = Query(..., ge=1, le=1000),
    cols: int = Query(..., ge=1, le=1000),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Resize terminal window (HTTP endpoint as alternative to WebSocket)

    Args:
        terminal_id: Terminal session ID
        rows: Number of rows
        cols: Number of columns

    Returns:
        Success message
    """
    user_id = get_user_id(current_user)
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
