#!/usr/bin/env python3
"""
PTY-based Terminal Session Manager

Provides interactive terminal sessions with PTY support:
- Real terminal emulation with PTY
- Session persistence and restoration
- Output capture and streaming
- Command execution tracking
- ANSI escape code handling

Uses DatabaseConnection for thread-safe database access (critical for
background reader threads that write output concurrently).
"""
# ruff: noqa: S608

import contextlib
import json
import os
import pty
import select
import sqlite3
import threading
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from api.services.db import BaseRepository, DatabaseConnection

# Security imports for command validation
from api.services.security import CommandValidationError, CommandValidator
from api.utils.structured_logging import get_logger

logger = get_logger(__name__)


@dataclass
class TerminalOutput:
    """Captured terminal output"""

    session_id: str
    output: str
    output_type: str  # stdout, stderr, error
    timestamp: str
    command: str | None = None


@dataclass
class TerminalSession:
    """Interactive terminal session with PTY"""

    session_id: str
    working_dir: str
    shell: str = "/bin/bash"
    env: dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # PTY file descriptors
    master_fd: int | None = None
    pid: int | None = None

    # State
    is_active: bool = False
    output_buffer: deque = field(default_factory=lambda: deque(maxlen=10000))
    command_history: list[str] = field(default_factory=list)

    # Callbacks
    output_callbacks: list[Callable[[str], None]] = field(default_factory=list)


@dataclass
class TerminalSessionRecord:
    """Database record for a terminal session."""

    session_id: str
    working_dir: str
    shell: str
    env: dict[str, str]
    created_at: str
    last_activity: str
    is_active: bool


@dataclass
class CommandHistoryRecord:
    """Database record for command history."""

    id: int | None
    session_id: str
    command: str
    exit_code: int | None
    duration_ms: int | None
    timestamp: str


# ============================================================================
# Repository Classes
# ============================================================================


class TerminalSessionRepository(BaseRepository[TerminalSessionRecord]):
    """Repository for terminal session records."""

    @property
    def table_name(self) -> str:
        return "terminal_sessions"

    def _create_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS terminal_sessions (
                session_id TEXT PRIMARY KEY,
                working_dir TEXT NOT NULL,
                shell TEXT NOT NULL,
                env TEXT,
                created_at TEXT NOT NULL,
                last_activity TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """

    def _row_to_entity(self, row: sqlite3.Row) -> TerminalSessionRecord:
        return TerminalSessionRecord(
            session_id=row["session_id"],
            working_dir=row["working_dir"],
            shell=row["shell"],
            env=json.loads(row["env"]) if row["env"] else {},
            created_at=row["created_at"],
            last_activity=row["last_activity"],
            is_active=bool(row["is_active"]),
        )

    def upsert(self, session: TerminalSession) -> None:
        """Insert or replace a session record."""
        self.db.execute(
            """
            INSERT OR REPLACE INTO terminal_sessions
            (session_id, working_dir, shell, env, created_at, last_activity, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.session_id,
                session.working_dir,
                session.shell,
                json.dumps(session.env),
                session.created_at,
                datetime.utcnow().isoformat(),
                1 if session.is_active else 0,
            ),
        )
        self.db.get().commit()

    def mark_inactive(self, session_id: str) -> None:
        """Mark a session as inactive."""
        self.update_where(
            {"is_active": 0, "last_activity": datetime.utcnow().isoformat()},
            "session_id = ?",
            (session_id,),
        )


class TerminalOutputRepository(BaseRepository[TerminalOutput]):
    """Repository for terminal output records."""

    @property
    def table_name(self) -> str:
        return "terminal_output"

    def _create_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS terminal_output (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                output TEXT NOT NULL,
                output_type TEXT NOT NULL,
                command TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES terminal_sessions(session_id)
            )
        """

    def _row_to_entity(self, row: sqlite3.Row) -> TerminalOutput:
        return TerminalOutput(
            session_id=row["session_id"],
            output=row["output"],
            output_type=row["output_type"],
            command=row["command"],
            timestamp=row["timestamp"],
        )

    def _run_migrations(self) -> None:
        """Create indexes for performance."""
        self._create_index(["session_id"], name="idx_output_session")

    def record_output(self, session_id: str, output: str, output_type: str) -> None:
        """Record terminal output."""
        self.insert(
            {
                "session_id": session_id,
                "output": output,
                "output_type": output_type,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


class CommandHistoryRepository(BaseRepository[CommandHistoryRecord]):
    """Repository for command history records."""

    @property
    def table_name(self) -> str:
        return "command_history"

    def _create_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS command_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                command TEXT NOT NULL,
                exit_code INTEGER,
                duration_ms INTEGER,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES terminal_sessions(session_id)
            )
        """

    def _row_to_entity(self, row: sqlite3.Row) -> CommandHistoryRecord:
        return CommandHistoryRecord(
            id=row["id"],
            session_id=row["session_id"],
            command=row["command"],
            exit_code=row["exit_code"],
            duration_ms=row["duration_ms"],
            timestamp=row["timestamp"],
        )

    def _run_migrations(self) -> None:
        """Create indexes for performance."""
        self._create_index(["session_id"], name="idx_command_session")

    def record_command(self, session_id: str, command: str) -> None:
        """Record a command execution."""
        self.insert(
            {
                "session_id": session_id,
                "command": command,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def get_session_history(self, session_id: str, limit: int = 50) -> list[str]:
        """Get command history for a session."""
        records = self.find_where(
            "session_id = ?",
            (session_id,),
            order_by="timestamp DESC",
            limit=limit,
        )
        # Reverse to get chronological order
        return [r.command for r in reversed(records)]


class PTYSessionManager:
    """
    Manages interactive PTY-based terminal sessions.

    Features:
    - Multiple concurrent sessions
    - Output capture and streaming
    - Command history tracking
    - Session persistence

    Uses DatabaseConnection for thread-safe database access, which is
    critical because background reader threads write output concurrently.
    """

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            data_dir = Path("~/.magnetarcode/data").expanduser()
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "terminal_sessions.db"

        self.sessions: dict[str, TerminalSession] = {}
        self.reader_threads: dict[str, threading.Thread] = {}

        # Initialize database connection and repositories
        self._db = DatabaseConnection(db_path)
        self._session_repo = TerminalSessionRepository(self._db)
        self._output_repo = TerminalOutputRepository(self._db)
        self._command_repo = CommandHistoryRepository(self._db)

    def create_session(
        self, working_dir: str, shell: str = "/bin/bash", env: dict[str, str] | None = None
    ) -> str:
        """
        Create a new PTY terminal session

        Args:
            working_dir: Initial working directory
            shell: Shell to use (default: /bin/bash)
            env: Additional environment variables

        Returns:
            Session ID

        Raises:
            ValueError: If working_dir is outside allowed workspace paths
        """
        session_id = f"term_{uuid.uuid4().hex[:12]}"

        # SECURITY: Validate working directory is within allowed workspace
        # This includes symlink detection to prevent TOCTOU attacks
        from pathlib import Path

        workspace_root = Path(os.getenv("WORKSPACE_ROOT") or Path.cwd()).resolve()
        working_path = Path(working_dir).resolve()

        # SECURITY: Check for symlinks in the path that could escape workspace
        # Walk from working_path up to workspace_root checking for symlinks
        def contains_symlink_escape(path: Path, root: Path) -> bool:
            """Check if path contains symlinks that resolve outside root."""
            current = path
            visited = set()

            while current != root and current != current.parent:
                if current in visited:
                    # Circular symlink detected
                    return True
                visited.add(current)

                # Check if this component is a symlink
                if current.is_symlink():
                    # Resolve the symlink and check if it's still within root
                    try:
                        resolved = current.resolve()
                        resolved.relative_to(root)
                    except ValueError:
                        # Symlink points outside workspace
                        return True

                current = current.parent

            return False

        # First check: path must be within workspace
        try:
            working_path.relative_to(workspace_root)
        except ValueError:
            raise ValueError(
                f"Access denied: working directory '{working_dir}' is outside "
                f"allowed workspace root '{workspace_root}'"
            )

        # Second check: no symlinks escaping workspace
        if contains_symlink_escape(working_path, workspace_root):
            raise ValueError(
                f"Access denied: path '{working_dir}' contains symlinks that "
                f"resolve outside workspace root '{workspace_root}'"
            )

        # Third check: verify the path exists and is a directory
        if not working_path.exists():
            raise ValueError(f"Working directory does not exist: {working_dir}")
        if not working_path.is_dir():
            raise ValueError(f"Path is not a directory: {working_dir}")

        # Prepare environment
        session_env = os.environ.copy()
        if env:
            session_env.update(env)

        # Add custom PS1 for command detection
        session_env["PS1"] = (
            "\\[\\033[0;32m\\]magnetar\\[\\033[0m\\]:\\[\\033[0;34m\\]\\w\\[\\033[0m\\]$ "
        )

        try:
            # Create PTY
            pid, master_fd = pty.fork()

            if pid == 0:  # Child process
                # Change to working directory (already validated)
                os.chdir(str(working_path))

                # Execute shell
                os.execvpe(shell, [shell], session_env)

            else:  # Parent process
                # Create session object
                session = TerminalSession(
                    session_id=session_id,
                    working_dir=working_dir,
                    shell=shell,
                    env=env or {},
                    master_fd=master_fd,
                    pid=pid,
                    is_active=True,
                )

                self.sessions[session_id] = session

                # Start output reader thread
                reader_thread = threading.Thread(
                    target=self._read_output, args=(session_id,), daemon=True
                )
                reader_thread.start()
                self.reader_threads[session_id] = reader_thread

                # Store in database using repository
                self._session_repo.upsert(session)

                return session_id

        except Exception as e:
            raise RuntimeError(f"Failed to create PTY session: {e}")

    def _read_output(self, session_id: str):
        """Background thread to read PTY output"""
        session = self.sessions.get(session_id)
        if not session or session.master_fd is None:
            return

        buffer = b""

        while session.is_active:
            try:
                # Check if data is available
                ready, _, _ = select.select([session.master_fd], [], [], 0.1)

                if ready:
                    # Read available data
                    try:
                        chunk = os.read(session.master_fd, 4096)
                        if not chunk:
                            # EOF - process ended
                            session.is_active = False
                            break

                        buffer += chunk

                        # Try to decode
                        try:
                            text = buffer.decode("utf-8")
                            buffer = b""

                            # Add to buffer
                            session.output_buffer.append(text)

                            # Call callbacks
                            for callback in session.output_callbacks:
                                try:
                                    callback(text)
                                except Exception as e:
                                    logger.error(f"Output callback error: {e}")

                            # Store in database using repository
                            self._output_repo.record_output(session_id, text, "stdout")

                        except UnicodeDecodeError:
                            # Incomplete UTF-8 sequence, keep in buffer
                            pass

                    except OSError:
                        session.is_active = False
                        break

            except Exception as e:
                logger.error(f"Error reading PTY output: {e}")
                session.is_active = False
                break

        # Clean up
        with contextlib.suppress(Exception):
            os.close(session.master_fd)

    def send_command(self, session_id: str, command: str) -> bool:
        """
        Send a command to the terminal session

        Args:
            session_id: Session ID
            command: Command to execute

        Returns:
            True if command was sent successfully
        """
        session = self.sessions.get(session_id)
        if not session or not session.is_active or session.master_fd is None:
            return False

        # SECURITY FIX: Validate command before execution
        validator = CommandValidator(
            workspace_root=Path(session.working_dir),
            strict_mode=True,
        )
        try:
            validator.validate(command)
        except CommandValidationError as e:
            logger.warning(
                "Command blocked by security validator",
                session_id=session_id,
                command=command[:100],  # Truncate for logging
                reason=str(e),
            )
            return False

        try:
            # Add to command history
            session.command_history.append(command)

            # Send command + newline
            os.write(session.master_fd, f"{command}\n".encode())

            # Store in database using repository
            self._command_repo.record_command(session_id, command)

            return True

        except Exception as e:
            logger.error(f"Error sending command: {e}", session_id=session_id)
            return False

    def get_output(self, session_id: str, lines: int = 100) -> list[str]:
        """
        Get recent output from session

        Args:
            session_id: Session ID
            lines: Number of lines to retrieve

        Returns:
            List of output lines
        """
        session = self.sessions.get(session_id)
        if not session:
            return []

        # Get from buffer
        output_list = list(session.output_buffer)
        return output_list[-lines:] if lines else output_list

    def get_command_history(self, session_id: str, limit: int = 50) -> list[str]:
        """Get command history for session."""
        session = self.sessions.get(session_id)
        if session:
            return session.command_history[-limit:]

        # Fallback to database using repository
        return self._command_repo.get_session_history(session_id, limit)

    def close_session(self, session_id: str) -> None:
        """Close a terminal session."""
        session = self.sessions.get(session_id)
        if not session:
            return

        session.is_active = False

        # Close PTY
        if session.master_fd is not None:
            with contextlib.suppress(Exception):
                os.close(session.master_fd)

        # Kill process
        if session.pid:
            with contextlib.suppress(Exception):
                os.kill(session.pid, 9)

        # Update database using repository
        self._session_repo.mark_inactive(session_id)

        # Remove from active sessions
        del self.sessions[session_id]

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all active sessions"""
        return [
            {
                "session_id": session.session_id,
                "working_dir": session.working_dir,
                "shell": session.shell,
                "is_active": session.is_active,
                "created_at": session.created_at,
                "command_count": len(session.command_history),
            }
            for session in self.sessions.values()
        ]


# Global instance
_pty_manager: PTYSessionManager | None = None


def get_pty_manager() -> PTYSessionManager:
    """Get or create global PTY session manager"""
    global _pty_manager
    if _pty_manager is None:
        _pty_manager = PTYSessionManager()
    return _pty_manager
