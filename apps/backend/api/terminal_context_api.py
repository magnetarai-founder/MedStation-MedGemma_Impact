"""
Terminal Context API for MagnetarCode

Simplified terminal output capture for context-aware chat.
Stores recent terminal output in circular buffers for AI context.

Endpoints:
  POST /api/v1/terminal-context/capture    - Capture terminal output
  GET  /api/v1/terminal-context/recent     - Get recent terminal output
  DELETE /api/v1/terminal-context/clear    - Clear terminal history
"""

from collections import deque
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/terminal-context", tags=["Terminal Context"])

# ===== Configuration =====

MAX_BUFFER_LINES = 500  # Keep last 500 lines per session
MAX_LINE_LENGTH = 2000  # Truncate lines longer than 2000 chars
MAX_SESSIONS = 10  # Maximum number of terminal sessions to track

# ===== In-Memory Storage =====

# session_id -> deque of output lines
_terminal_buffers: dict[str, deque] = {}

# session_id -> metadata
_session_metadata: dict[str, dict[str, Any]] = {}

# ===== Models =====


class TerminalCaptureRequest(BaseModel):
    """Request to capture terminal output"""

    session_id: str = Field(..., description="Terminal session ID (e.g., 'main', 'task-1')")
    output: str = Field(..., description="Terminal output to capture")
    command: str | None = Field(None, description="Command that generated this output")
    exit_code: int | None = Field(None, description="Command exit code")


class TerminalContextResponse(BaseModel):
    """Response with terminal context"""

    session_id: str
    lines: int
    output: str
    commands: list[str]
    last_updated: str


class TerminalSessionInfo(BaseModel):
    """Information about a terminal session"""

    session_id: str
    lines_buffered: int
    commands_run: int
    created_at: str
    last_updated: str


# ===== Helpers =====


def get_or_create_buffer(session_id: str) -> deque:
    """Get or create a circular buffer for a session"""
    if session_id not in _terminal_buffers:
        # Cleanup old sessions if we're at the limit
        if len(_terminal_buffers) >= MAX_SESSIONS:
            # Remove oldest session
            oldest_session = min(
                _session_metadata.keys(), key=lambda sid: _session_metadata[sid]["last_updated"]
            )
            del _terminal_buffers[oldest_session]
            del _session_metadata[oldest_session]

        _terminal_buffers[session_id] = deque(maxlen=MAX_BUFFER_LINES)
        _session_metadata[session_id] = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "commands": [],
        }

    return _terminal_buffers[session_id]


def update_metadata(session_id: str, command: str | None = None) -> None:
    """Update session metadata"""
    if session_id in _session_metadata:
        _session_metadata[session_id]["last_updated"] = datetime.now(timezone.utc).isoformat()
        if command and command not in _session_metadata[session_id]["commands"]:
            _session_metadata[session_id]["commands"].append(command)


# ===== Endpoints =====


@router.post("/capture")
async def capture_terminal_output(request: TerminalCaptureRequest) -> dict[str, bool | str | int]:
    """
    Capture terminal output for later use as context.

    Stores output in a circular buffer (last 500 lines per session).
    Can be called from terminal wrappers, IDE extensions, or scripts.

    **Example:**
    ```bash
    # Capture output from a command
    output=$(ls -la 2>&1)
    curl -X POST http://localhost:8001/api/v1/terminal-context/capture \
      -H "Content-Type: application/json" \
      -d "{
        \"session_id\": \"main\",
        \"command\": \"ls -la\",
        \"output\": \"$output\",
        \"exit_code\": $?
      }"
    ```

    **Shell Integration:**
    ```bash
    # Add to ~/.zshrc or ~/.bashrc
    function medstation_capture() {
        local cmd="$1"
        local output="$2"
        local exit_code=$?

        curl -s -X POST http://localhost:8001/api/v1/terminal-context/capture \
          -H "Content-Type: application/json" \
          -d "$(jq -n --arg cmd "$cmd" --arg out "$output" --argjson code $exit_code \
            '{session_id: "main", command: $cmd, output: $out, exit_code: $code}')"

        return $exit_code
    }

    # Use in prompt command
    precmd() {
        local last_cmd="$(history | tail -1 | sed 's/^[ ]*[0-9]*[ ]*//')"
        local last_output="$(fc -ln -1)"
        medstation_capture "$last_cmd" "$last_output"
    }
    ```
    """
    buffer = get_or_create_buffer(request.session_id)

    # Split output into lines
    lines = request.output.splitlines()

    # Add each line to buffer (with truncation)
    for line in lines:
        if len(line) > MAX_LINE_LENGTH:
            line = line[:MAX_LINE_LENGTH] + "... (truncated)"
        buffer.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "line": line,
                "command": request.command,
            }
        )

    # Update metadata
    update_metadata(request.session_id, request.command)

    return {
        "success": True,
        "session_id": request.session_id,
        "lines_captured": len(lines),
        "buffer_size": len(buffer),
    }


@router.get("/recent", response_model=TerminalContextResponse)
async def get_recent_output(
    session_id: str = Query(default="main", description="Terminal session ID"),
    lines: int = Query(default=100, ge=1, le=500, description="Number of recent lines to return"),
) -> TerminalContextResponse:
    """
    Get recent terminal output for use as AI context.

    Returns the last N lines from the terminal buffer, formatted for LLM consumption.

    **Example:**
    ```bash
    # Get last 100 lines
    curl "http://localhost:8001/api/v1/terminal-context/recent?session_id=main&lines=100"
    ```
    """
    if session_id not in _terminal_buffers:
        return TerminalContextResponse(
            session_id=session_id,
            lines=0,
            output="",
            commands=[],
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

    buffer = _terminal_buffers[session_id]
    metadata = _session_metadata[session_id]

    # Get last N lines
    recent_items = list(buffer)[-lines:]

    # Format output
    output_lines = []
    for item in recent_items:
        line = item["line"]
        if item.get("command"):
            output_lines.append(f"$ {item['command']}")
        output_lines.append(line)

    output = "\n".join(output_lines)

    return TerminalContextResponse(
        session_id=session_id,
        lines=len(recent_items),
        output=output,
        commands=metadata.get("commands", []),
        last_updated=metadata["last_updated"],
    )


@router.get("/sessions", response_model=list[TerminalSessionInfo])
async def list_sessions() -> list[TerminalSessionInfo]:
    """
    List all active terminal sessions.

    Returns metadata about each session (lines buffered, commands run, etc.).
    """
    sessions = []
    for session_id, metadata in _session_metadata.items():
        buffer = _terminal_buffers.get(session_id, deque())
        sessions.append(
            TerminalSessionInfo(
                session_id=session_id,
                lines_buffered=len(buffer),
                commands_run=len(metadata.get("commands", [])),
                created_at=metadata["created_at"],
                last_updated=metadata["last_updated"],
            )
        )

    # Sort by last updated (most recent first)
    sessions.sort(key=lambda s: s.last_updated, reverse=True)

    return sessions


@router.delete("/clear")
async def clear_terminal_context(
    session_id: str | None = Query(None, description="Session ID to clear (all if not specified)"),
) -> dict[str, bool | str]:
    """
    Clear terminal context.

    Clears the output buffer for a specific session or all sessions.

    **Example:**
    ```bash
    # Clear specific session
    curl -X DELETE "http://localhost:8001/api/v1/terminal-context/clear?session_id=main"

    # Clear all sessions
    curl -X DELETE "http://localhost:8001/api/v1/terminal-context/clear"
    ```
    """
    if session_id:
        if session_id in _terminal_buffers:
            del _terminal_buffers[session_id]
            del _session_metadata[session_id]
            return {"success": True, "message": f"Cleared session: {session_id}"}
        else:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    else:
        # Clear all sessions
        count = len(_terminal_buffers)
        _terminal_buffers.clear()
        _session_metadata.clear()
        return {"success": True, "message": f"Cleared {count} sessions"}


@router.get("/health")
async def terminal_context_health() -> dict[str, str | int]:
    """Health check for terminal context service"""
    return {
        "status": "healthy",
        "active_sessions": len(_terminal_buffers),
        "max_sessions": MAX_SESSIONS,
        "max_buffer_lines": MAX_BUFFER_LINES,
        "total_lines_buffered": sum(len(buf) for buf in _terminal_buffers.values()),
    }
