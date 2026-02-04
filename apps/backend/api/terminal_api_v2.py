"""
Terminal API v2 for MagnetarCode

Advanced terminal integration with PTY, multiplexing, and native terminal support:
- PTY-based interactive sessions
- Terminal multiplexing (tmux-like)
- WebSocket streaming
- iTerm2/Warp integration
- Command history and suggestions
- Error detection and context capture
"""

import contextlib
import json

from fastapi import APIRouter, Body, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from .services.terminal import (
    PaneLayout,
    get_multiplexer,
    get_pty_manager,
    get_terminal_integration,
)

router = APIRouter(prefix="/api/v2/terminal", tags=["Terminal v2"])


# ===== Models =====


class CreateSessionRequest(BaseModel):
    """Request to create a PTY session"""

    working_dir: str = Field(..., description="Working directory")
    shell: str = Field("/bin/bash", description="Shell to use")
    env: dict[str, str] | None = Field(None, description="Environment variables")


class SendCommandRequest(BaseModel):
    """Request to send command to session"""

    session_id: str
    command: str


class CreateWorkspaceRequest(BaseModel):
    """Request to create terminal workspace"""

    name: str = Field(..., description="Workspace name")
    working_dir: str = Field(..., description="Working directory")


class CreateWindowRequest(BaseModel):
    """Request to create window in workspace"""

    workspace_id: str
    name: str
    layout: str = Field("single", description="Layout: single, horizontal, vertical, grid_2x2")


class SplitPaneRequest(BaseModel):
    """Request to split a pane"""

    window_id: str
    pane_id: str
    direction: str = Field("horizontal", description="horizontal or vertical")


class NativeTerminalRequest(BaseModel):
    """Request for native terminal operations"""

    action: str = Field(
        ..., description="Action: create_tab, create_window, send_command, split_pane"
    )
    command: str | None = None
    working_dir: str | None = None
    title: str | None = None
    direction: str | None = "horizontal"


# ===== PTY Session Endpoints =====


@router.post("/pty/create")
async def create_pty_session(request: CreateSessionRequest) -> dict[str, str | bool]:
    """
    Create a new PTY terminal session

    Returns a session ID that can be used to interact with the terminal.

    **Example:**
    ```bash
    curl -X POST http://localhost:8001/api/v2/terminal/pty/create \
      -H "Content-Type: application/json" \
      -d '{
        "working_dir": "/path/to/project",
        "shell": "/bin/bash"
      }'
    ```
    """
    pty_manager = get_pty_manager()

    try:
        session_id = pty_manager.create_session(
            working_dir=request.working_dir, shell=request.shell, env=request.env
        )

        return {
            "success": True,
            "session_id": session_id,
            "working_dir": request.working_dir,
            "shell": request.shell,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pty/command")
async def send_pty_command(request: SendCommandRequest) -> dict[str, str | bool]:
    """
    Send a command to a PTY session

    **Example:**
    ```bash
    curl -X POST http://localhost:8001/api/v2/terminal/pty/command \
      -H "Content-Type: application/json" \
      -d '{
        "session_id": "term_abc123",
        "command": "ls -la"
      }'
    ```
    """
    pty_manager = get_pty_manager()

    success = pty_manager.send_command(request.session_id, request.command)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found or inactive")

    return {"success": True, "session_id": request.session_id, "command": request.command}


@router.get("/pty/output/{session_id}")
async def get_pty_output(
    session_id: str, lines: int = Query(100, description="Number of lines to retrieve")
) -> dict[str, str | list[str] | bool | int]:
    """Get output from a PTY session"""
    pty_manager = get_pty_manager()

    output = pty_manager.get_output(session_id, lines=lines)

    return {"session_id": session_id, "output": output, "line_count": len(output)}


@router.get("/pty/history/{session_id}")
async def get_command_history(
    session_id: str, limit: int = Query(50, description="Number of commands")
) -> dict[str, str | list[dict] | int]:
    """Get command history for a session"""
    pty_manager = get_pty_manager()

    history = pty_manager.get_command_history(session_id, limit=limit)

    return {"session_id": session_id, "history": history, "count": len(history)}


@router.delete("/pty/{session_id}")
async def close_pty_session(session_id: str) -> dict[str, bool | str]:
    """Close a PTY session"""
    pty_manager = get_pty_manager()

    pty_manager.close_session(session_id)

    return {"success": True, "session_id": session_id}


@router.get("/pty/list")
async def list_pty_sessions() -> dict[str, list[dict] | int]:
    """List all active PTY sessions"""
    pty_manager = get_pty_manager()

    sessions = pty_manager.list_sessions()

    return {"sessions": sessions, "count": len(sessions)}


# ===== Multiplexer Endpoints =====


@router.post("/workspace/create")
async def create_workspace(request: CreateWorkspaceRequest) -> dict[str, str | bool]:
    """
    Create a new terminal workspace (like tmux session)

    **Example:**
    ```bash
    curl -X POST http://localhost:8001/api/v2/terminal/workspace/create \
      -H "Content-Type: application/json" \
      -d '{
        "name": "my-project",
        "working_dir": "/path/to/project"
      }'
    ```
    """
    multiplexer = get_multiplexer()

    try:
        workspace_id = multiplexer.create_workspace(
            name=request.name, working_dir=request.working_dir
        )

        return {"success": True, "workspace_id": workspace_id, "name": request.name}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/window/create")
async def create_window(request: CreateWindowRequest) -> dict[str, str | bool | dict]:
    """Create a new window in a workspace"""
    multiplexer = get_multiplexer()

    try:
        # Parse layout
        layout = PaneLayout(request.layout)

        window_id = multiplexer.create_window(
            workspace_id=request.workspace_id, name=request.name, layout=layout
        )

        return {"success": True, "window_id": window_id, "workspace_id": request.workspace_id}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pane/split")
async def split_pane(request: SplitPaneRequest) -> dict[str, str | bool | dict]:
    """
    Split a pane horizontally or vertically

    **Example:**
    ```bash
    curl -X POST http://localhost:8001/api/v2/terminal/pane/split \
      -H "Content-Type: application/json" \
      -d '{
        "window_id": "win_abc123",
        "pane_id": "pane_xyz789",
        "direction": "horizontal"
      }'
    ```
    """
    multiplexer = get_multiplexer()

    try:
        new_pane_id = multiplexer.split_pane(
            window_id=request.window_id, pane_id=request.pane_id, direction=request.direction
        )

        return {"success": True, "new_pane_id": new_pane_id, "window_id": request.window_id}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pane/command")
async def send_pane_command(
    pane_id: str = Body(...), command: str = Body(...)
) -> dict[str, str | bool]:
    """Send command to a specific pane"""
    multiplexer = get_multiplexer()

    success = multiplexer.send_command(pane_id, command)

    if not success:
        raise HTTPException(status_code=404, detail="Pane not found")

    return {"success": True, "pane_id": pane_id}


@router.get("/pane/output/{pane_id}")
async def get_pane_output(
    pane_id: str, lines: int = Query(100, description="Number of lines")
) -> dict[str, str | list[str] | bool | int]:
    """Get output from a specific pane"""
    multiplexer = get_multiplexer()

    output = multiplexer.get_pane_output(pane_id, lines=lines)

    return {"pane_id": pane_id, "output": output, "line_count": len(output)}


@router.get("/workspace/{workspace_id}")
async def get_workspace(workspace_id: str) -> dict[str, str | bool | dict]:
    """Get workspace details with all windows and panes"""
    multiplexer = get_multiplexer()

    workspace = multiplexer.get_workspace(workspace_id)

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    return workspace


@router.get("/workspace/list")
async def list_workspaces() -> dict[str, list[dict] | int]:
    """List all workspaces"""
    multiplexer = get_multiplexer()

    workspaces = multiplexer.list_workspaces()

    return {"workspaces": workspaces, "count": len(workspaces)}


@router.delete("/pane/{pane_id}")
async def close_pane(pane_id: str) -> dict[str, bool | str]:
    """Close a specific pane"""
    multiplexer = get_multiplexer()

    multiplexer.close_pane(pane_id)

    return {"success": True, "pane_id": pane_id}


@router.delete("/window/{window_id}")
async def close_window(window_id: str) -> dict[str, bool | str]:
    """Close a window and all its panes"""
    multiplexer = get_multiplexer()

    multiplexer.close_window(window_id)

    return {"success": True, "window_id": window_id}


# ===== Native Terminal Integration =====


@router.get("/native/detect")
async def detect_native_terminal() -> dict[str, str | bool | dict[str, str]]:
    """
    Detect which native terminal is running

    Returns information about iTerm2, Warp, or Terminal.app
    """
    integration = get_terminal_integration()

    result: dict[str, str | bool | dict[str, str]] = integration.get_terminal_info()
    return result


@router.post("/native/execute")
async def execute_native_action(request: NativeTerminalRequest) -> dict[str, bool | str]:
    """
    Execute action in native terminal (iTerm2/Warp)

    Actions:
    - create_tab: Create new tab
    - create_window: Create new window
    - send_command: Send command to current session
    - split_pane: Split current pane (iTerm2 only)

    **Example:**
    ```bash
    curl -X POST http://localhost:8001/api/v2/terminal/native/execute \
      -H "Content-Type: application/json" \
      -d '{
        "action": "create_tab",
        "working_dir": "/path/to/project",
        "command": "npm run dev",
        "title": "Dev Server"
      }'
    ```
    """
    integration = get_terminal_integration()

    success = False

    if request.action == "create_tab":
        success = integration.create_tab(
            command=request.command, working_dir=request.working_dir, title=request.title
        )

    elif request.action == "create_window":
        success = integration.create_window(
            command=request.command, working_dir=request.working_dir
        )

    elif request.action == "send_command":
        if not request.command:
            raise HTTPException(status_code=400, detail="command is required")
        success = integration.send_command(request.command)

    elif request.action == "split_pane":
        success = integration.split_pane(
            direction=request.direction or "horizontal", command=request.command
        )

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")

    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute {request.action}. Terminal may not support this action.",
        )

    return {"success": True, "action": request.action}


# ===== WebSocket Streaming =====


@router.websocket("/ws/{session_id}")
async def websocket_terminal(websocket: WebSocket, session_id: str) -> None:
    """
    WebSocket endpoint for real-time terminal streaming

    **Usage:**
    ```javascript
    const ws = new WebSocket('ws://localhost:8001/api/v2/terminal/ws/term_abc123');

    ws.onmessage = (event) => {
        console.log('Terminal output:', event.data);
    };

    // Send commands
    ws.send(JSON.stringify({type: 'command', data: 'ls -la'}));
    ```
    """
    await websocket.accept()

    pty_manager = get_pty_manager()
    session = pty_manager.sessions.get(session_id)

    if not session:
        await websocket.send_json({"error": "Session not found"})
        await websocket.close()
        return

    # Register output callback
    async def output_callback(text: str):
        with contextlib.suppress(Exception):
            await websocket.send_json({"type": "output", "data": text})

    session.output_callbacks.append(output_callback)

    try:
        while True:
            # Receive commands from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)

                if message.get("type") == "command":
                    command = message.get("data")
                    if command:
                        pty_manager.send_command(session_id, command)

                elif message.get("type") == "resize":
                    # Terminal resize (future implementation)
                    pass

            except json.JSONDecodeError:
                # Treat as raw command
                pty_manager.send_command(session_id, data)

    except WebSocketDisconnect:
        # Remove callback
        if output_callback in session.output_callbacks:
            session.output_callbacks.remove(output_callback)


@router.get("/health")
async def terminal_health() -> dict[str, str | bool]:
    """Health check for terminal services"""
    integration = get_terminal_integration()

    return {
        "status": "healthy",
        "features": [
            "pty_sessions",
            "multiplexing",
            "native_integration",
            "websocket_streaming",
            "command_history",
        ],
        "native_terminal": integration.get_terminal_info(),
    }
