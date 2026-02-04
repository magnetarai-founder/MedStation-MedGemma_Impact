"""
Aider Session Manager

Manages persistent Aider sessions with conversation context.
Enables multi-turn interactions for complex editing tasks.

Security Note: This module uses asyncio.create_subprocess_exec which
passes arguments as a list (not shell string), preventing injection.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .bridge import AiderMessage, AiderResponse, AiderSession

logger = logging.getLogger(__name__)


@dataclass
class SessionConfig:
    """Configuration for an Aider session"""

    workspace_root: str
    model: str = "ollama/deepseek-coder:33b"
    edit_format: str = "diff"

    # Session limits
    max_idle_seconds: int = 300  # 5 minutes
    max_conversation_turns: int = 50
    max_context_tokens: int = 8000

    # Behavior
    auto_commit: bool = False
    verbose: bool = False
    stream_output: bool = True


@dataclass
class SessionState:
    """Runtime state of a session"""

    session_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)

    # Conversation
    messages: list[AiderMessage] = field(default_factory=list)
    files_in_context: set[str] = field(default_factory=set)

    # Stats
    total_edits: int = 0
    total_tokens: int = 0
    error_count: int = 0

    # Process
    process_pid: int | None = None
    is_active: bool = False

    def touch(self) -> None:
        """Update last activity time"""
        self.last_activity = datetime.utcnow()

    def is_expired(self, max_idle_seconds: int) -> bool:
        """Check if session has expired due to inactivity"""
        elapsed = (datetime.utcnow() - self.last_activity).total_seconds()
        return elapsed > max_idle_seconds

    def add_message(self, role: str, content: str) -> AiderMessage:
        """Add a message to conversation history"""
        msg = AiderMessage(role=role, content=content)
        self.messages.append(msg)
        self.touch()
        return msg


class ManagedAiderSession(AiderSession):
    """
    Concrete implementation of AiderSession.

    Manages a single persistent Aider session with:
    - Conversation history tracking
    - File context management
    - Idle timeout handling
    - Resource cleanup
    """

    def __init__(self, config: SessionConfig):
        """
        Initialize managed session.

        Args:
            config: Session configuration
        """
        self._config = config
        self._state = SessionState(session_id=str(uuid.uuid4()))
        self._lock = asyncio.Lock()
        self._process: asyncio.subprocess.Process | None = None

    @property
    def session_id(self) -> str:
        return self._state.session_id

    @property
    def is_active(self) -> bool:
        return self._state.is_active and not self._state.is_expired(
            self._config.max_idle_seconds
        )

    async def start(self) -> None:
        """Start the Aider session"""
        async with self._lock:
            if self._state.is_active:
                logger.warning(f"Session {self.session_id} already active")
                return

            logger.info(f"Starting Aider session {self.session_id}")

            # Build command as list (safe - no shell interpolation)
            cmd = self._build_command()

            try:
                # SECURITY: Using create_subprocess_exec with list args
                # This passes arguments directly to the executable without
                # shell interpretation, preventing command injection.
                self._process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self._config.workspace_root,
                )

                self._state.is_active = True
                self._state.process_pid = self._process.pid
                self._state.touch()

                logger.info(
                    f"Aider session started with PID {self._process.pid}"
                )

            except FileNotFoundError:
                logger.error("Aider not found in PATH")
                raise RuntimeError("Aider is not installed or not in PATH")
            except OSError as e:
                logger.error(f"Failed to start Aider session: {e}")
                raise

    async def stop(self) -> None:
        """Stop the Aider session"""
        async with self._lock:
            if not self._state.is_active:
                return

            logger.info(f"Stopping Aider session {self.session_id}")

            if self._process:
                try:
                    # Send quit command
                    if self._process.stdin:
                        self._process.stdin.write(b"/quit\n")
                        await self._process.stdin.drain()

                    # Wait for graceful shutdown
                    try:
                        await asyncio.wait_for(
                            self._process.wait(), timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        # Force kill
                        self._process.kill()
                        await self._process.wait()

                except OSError as e:
                    logger.warning(f"Error stopping Aider process: {e}")
                    if self._process:
                        self._process.kill()

            self._state.is_active = False
            self._process = None

    async def send(self, message: str) -> AiderResponse:
        """
        Send a message to Aider and get response.

        Args:
            message: The instruction or question

        Returns:
            AiderResponse with results
        """
        if not self.is_active:
            return AiderResponse(
                success=False,
                message="Session is not active",
                error="Session inactive or expired",
                error_type="SessionError",
            )

        async with self._lock:
            start_time = time.time()

            try:
                # Add user message to history
                self._state.add_message("user", message)

                # Send to process
                if self._process and self._process.stdin:
                    self._process.stdin.write(f"{message}\n".encode())
                    await self._process.stdin.drain()

                # Read response
                response_text = await self._read_response()

                # Add assistant message
                self._state.add_message("assistant", response_text)

                duration_ms = int((time.time() - start_time) * 1000)

                return AiderResponse(
                    success=True,
                    message=response_text,
                    model=self._config.model,
                    duration_ms=duration_ms,
                    conversation=list(self._state.messages),
                )

            except OSError as e:
                self._state.error_count += 1
                logger.error(f"Error sending to Aider: {e}")

                return AiderResponse(
                    success=False,
                    message="",
                    error=str(e),
                    error_type=type(e).__name__,
                )

    async def add_files(self, files: list[str]) -> None:
        """Add files to session context"""
        if not self.is_active:
            raise RuntimeError("Session not active")

        async with self._lock:
            for file_path in files:
                if file_path not in self._state.files_in_context:
                    # Send /add command
                    if self._process and self._process.stdin:
                        self._process.stdin.write(f"/add {file_path}\n".encode())
                        await self._process.stdin.drain()

                    self._state.files_in_context.add(file_path)

            self._state.touch()

    async def remove_files(self, files: list[str]) -> None:
        """Remove files from session context"""
        if not self.is_active:
            raise RuntimeError("Session not active")

        async with self._lock:
            for file_path in files:
                if file_path in self._state.files_in_context:
                    # Send /drop command
                    if self._process and self._process.stdin:
                        self._process.stdin.write(f"/drop {file_path}\n".encode())
                        await self._process.stdin.drain()

                    self._state.files_in_context.discard(file_path)

            self._state.touch()

    def get_conversation_history(self) -> list[AiderMessage]:
        """Get conversation history"""
        return list(self._state.messages)

    def clear_history(self) -> None:
        """Clear conversation history"""
        self._state.messages.clear()

    def _build_command(self) -> list[str]:
        """
        Build the aider command as a list.

        Returns a list of arguments, not a shell string,
        ensuring safe subprocess invocation.
        """
        cmd = [
            "aider",
            "--model", self._config.model,
            "--edit-format", self._config.edit_format,
        ]

        if not self._config.auto_commit:
            cmd.append("--no-auto-commit")

        if not self._config.verbose:
            cmd.append("--no-pretty")

        # No git integration for now
        cmd.append("--no-git")

        return cmd

    async def _read_response(self, timeout: float = 60.0) -> str:
        """
        Read response from Aider process.

        Reads until we see the prompt indicator.
        """
        if not self._process or not self._process.stdout:
            return ""

        chunks: list[bytes] = []
        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                break

            try:
                chunk = await asyncio.wait_for(
                    self._process.stdout.read(1024),
                    timeout=1.0
                )

                if not chunk:
                    break

                chunks.append(chunk)

                # Check for prompt (aider shows ">" when ready for input)
                combined = b"".join(chunks)
                if combined.endswith(b"> ") or combined.endswith(b">\n"):
                    break

            except asyncio.TimeoutError:
                # Check if we have enough response
                if chunks:
                    break
                continue

        return b"".join(chunks).decode("utf-8", errors="replace")


class AiderSessionManager:
    """
    Manages multiple Aider sessions.

    Features:
    - Session pooling and reuse
    - Automatic cleanup of idle sessions
    - Resource limits
    """

    # Maximum concurrent sessions
    MAX_SESSIONS = 5

    def __init__(self, default_config: SessionConfig | None = None):
        """
        Initialize session manager.

        Args:
            default_config: Default configuration for new sessions
        """
        self._default_config = default_config
        self._sessions: dict[str, ManagedAiderSession] = {}
        self._workspace_sessions: dict[str, str] = {}  # workspace -> session_id
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None

    async def get_session(
        self,
        workspace_root: str,
        config: SessionConfig | None = None,
    ) -> ManagedAiderSession:
        """
        Get or create a session for workspace.

        Args:
            workspace_root: Workspace directory
            config: Optional session config

        Returns:
            Active session for the workspace
        """
        async with self._lock:
            # Check for existing session
            if workspace_root in self._workspace_sessions:
                session_id = self._workspace_sessions[workspace_root]
                session = self._sessions.get(session_id)

                if session and session.is_active:
                    return session

                # Clean up expired session
                if session:
                    await session.stop()
                    del self._sessions[session_id]
                del self._workspace_sessions[workspace_root]

            # Check session limit
            if len(self._sessions) >= self.MAX_SESSIONS:
                await self._cleanup_oldest_session()

            # Create new session
            session_config = config or self._default_config
            if not session_config:
                session_config = SessionConfig(workspace_root=workspace_root)
            else:
                # Ensure workspace is set
                session_config.workspace_root = workspace_root

            session = ManagedAiderSession(session_config)
            await session.start()

            self._sessions[session.session_id] = session
            self._workspace_sessions[workspace_root] = session.session_id

            return session

    async def close_session(self, session_id: str) -> None:
        """Close a specific session"""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                await session.stop()
                del self._sessions[session_id]

                # Remove workspace mapping
                for workspace, sid in list(self._workspace_sessions.items()):
                    if sid == session_id:
                        del self._workspace_sessions[workspace]
                        break

    async def close_all(self) -> None:
        """Close all sessions"""
        async with self._lock:
            for session in self._sessions.values():
                await session.stop()

            self._sessions.clear()
            self._workspace_sessions.clear()

            if self._cleanup_task:
                self._cleanup_task.cancel()

    async def _cleanup_oldest_session(self) -> None:
        """Clean up the oldest session to make room"""
        if not self._sessions:
            return

        # Find oldest by last activity
        oldest_id = min(
            self._sessions.keys(),
            key=lambda sid: self._sessions[sid]._state.last_activity
        )

        await self.close_session(oldest_id)

    async def start_cleanup_task(self, interval: int = 60) -> None:
        """Start background cleanup task"""
        async def cleanup_loop() -> None:
            while True:
                await asyncio.sleep(interval)
                await self._cleanup_expired_sessions()

        self._cleanup_task = asyncio.create_task(cleanup_loop())

    async def _cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions"""
        async with self._lock:
            expired = [
                sid for sid, session in self._sessions.items()
                if not session.is_active
            ]

            for sid in expired:
                await self.close_session(sid)

    def get_stats(self) -> dict[str, Any]:
        """Get session manager statistics"""
        return {
            "active_sessions": len(self._sessions),
            "max_sessions": self.MAX_SESSIONS,
            "sessions": {
                sid: {
                    "workspace": next(
                        (w for w, s in self._workspace_sessions.items() if s == sid),
                        None
                    ),
                    "is_active": session.is_active,
                    "messages": len(session._state.messages),
                    "files": len(session._state.files_in_context),
                    "total_edits": session._state.total_edits,
                }
                for sid, session in self._sessions.items()
            },
        }
