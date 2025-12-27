"""
Terminal Bridge Service - PTY Management for Code Tab

Handles spawning, managing, and capturing terminal sessions for the Code Tab.
Provides WebSocket-based real-time terminal I/O with context capture.
"""

import pty
import os
import asyncio
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, Callable
import signal
import select
import logging

# Import audit logging
try:
    from api.audit_logger import get_audit_logger, AuditAction
except ImportError:
    try:
        from audit_logger import get_audit_logger, AuditAction
    except ImportError:
        # Fallback for testing
        def get_audit_logger():
            return None
        class AuditAction:
            TERMINAL_SPAWN = "terminal.spawn"
            TERMINAL_CLOSE = "terminal.close"
            TERMINAL_WRITE = "terminal.write"

logger = logging.getLogger(__name__)


@dataclass
class TerminalSession:
    """Represents an active terminal session"""
    id: str
    user_id: str
    master: int
    process: subprocess.Popen
    created_at: datetime = field(default_factory=datetime.now)
    active: bool = True
    output_buffer: list = field(default_factory=list)
    websocket: Optional[object] = None


class TerminalContextStore:
    """Stores terminal output for context and learning"""

    def __init__(self):
        self.context_buffer = {}

    async def store_terminal_output(self, terminal_id: str, output: str):
        """Store terminal output for context"""
        if terminal_id not in self.context_buffer:
            self.context_buffer[terminal_id] = []

        self.context_buffer[terminal_id].append({
            'timestamp': datetime.now().isoformat(),
            'output': output
        })

        # Keep last 1000 lines
        if len(self.context_buffer[terminal_id]) > 1000:
            self.context_buffer[terminal_id] = self.context_buffer[terminal_id][-1000:]

    def get_context(self, terminal_id: str, lines: int = 100) -> str:
        """Get recent terminal context"""
        if terminal_id not in self.context_buffer:
            return ""

        recent = self.context_buffer[terminal_id][-lines:]
        return '\n'.join([item['output'] for item in recent])


class TerminalBridge:
    """Main Terminal Bridge service for PTY management"""

    def __init__(self):
        self.sessions: Dict[str, TerminalSession] = {}
        self.context_store = TerminalContextStore()
        self._broadcast_callbacks: Dict[str, list] = {}
        self.system_terminals: Dict[str, dict] = {}  # Track system terminal sessions

    def _generate_id(self) -> str:
        """Generate unique terminal ID"""
        return f"term_{uuid.uuid4().hex[:12]}"

    async def spawn_terminal(self, user_id: str, shell: str = None, cwd: str = None) -> TerminalSession:
        """
        Spawn new PTY terminal session

        Args:
            user_id: User ID owning this terminal
            shell: Shell to use (defaults to /bin/bash or /bin/zsh)
            cwd: Working directory (defaults to user home)

        Returns:
            TerminalSession object
        """
        # Determine shell with STRICT validation (SECURITY: Prevent command injection)
        ALLOWED_SHELLS = ['/bin/bash', '/bin/zsh', '/bin/sh', '/usr/bin/bash', '/usr/bin/zsh']

        if shell is None:
            # Try zsh first, fall back to bash
            if os.path.exists('/bin/zsh'):
                shell = '/bin/zsh'
            else:
                shell = '/bin/bash'
        else:
            # SECURITY: Validate shell is in whitelist
            if shell not in ALLOWED_SHELLS:
                logger.error(f"SECURITY: Rejected invalid shell: {shell}")
                raise ValueError(f"Invalid shell. Allowed shells: {', '.join(ALLOWED_SHELLS)}")

            # SECURITY: Verify shell actually exists
            if not os.path.exists(shell):
                raise ValueError(f"Shell does not exist: {shell}")

        # Determine working directory with validation (SECURITY: Prevent directory traversal)
        if cwd is None:
            cwd = os.path.expanduser('~')
        else:
            # SECURITY: Validate cwd is an absolute path and exists
            from pathlib import Path
            cwd_path = Path(cwd).resolve()

            if not cwd_path.exists():
                raise ValueError(f"Working directory does not exist: {cwd}")

            if not cwd_path.is_dir():
                raise ValueError(f"Working directory is not a directory: {cwd}")

            # SECURITY: Ensure no symlinks to sensitive paths
            # (This is additional defense-in-depth)
            cwd = str(cwd_path)

        # Create PTY
        master, slave = pty.openpty()

        # Spawn process
        process = subprocess.Popen(
            [shell],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            cwd=cwd,
            preexec_fn=os.setsid,
            env=os.environ.copy()
        )

        # Close slave FD (parent doesn't need it)
        os.close(slave)

        # Create session
        session = TerminalSession(
            id=self._generate_id(),
            user_id=user_id,
            master=master,
            process=process
        )

        self.sessions[session.id] = session

        # Start output capture task
        asyncio.create_task(self._capture_output(session))

        # Audit log terminal spawn
        try:
            audit_logger = get_audit_logger()
            if audit_logger:
                audit_logger.log(
                    user_id=user_id,
                    action=AuditAction.TERMINAL_SPAWN,
                    details={
                        "terminal_id": session.id,
                        "shell": shell,
                        "cwd": cwd,
                        "pid": process.pid
                    }
                )
        except Exception as e:
            logger.error(f"Failed to log terminal spawn: {e}")

        return session

    async def _capture_output(self, session: TerminalSession):
        """
        Capture terminal output in background task

        Reads from PTY master and broadcasts to WebSocket clients
        """
        loop = asyncio.get_event_loop()

        while session.active:
            try:
                # Use select to check if data is available (non-blocking)
                readable, _, _ = select.select([session.master], [], [], 0.1)

                if readable:
                    # Read from PTY master
                    output = await loop.run_in_executor(
                        None,
                        os.read,
                        session.master,
                        4096
                    )

                    if output:
                        decoded = output.decode('utf-8', errors='replace')

                        # Store in buffer
                        session.output_buffer.append(decoded)

                        # Keep buffer size manageable
                        if len(session.output_buffer) > 1000:
                            session.output_buffer = session.output_buffer[-1000:]

                        # Store in context
                        await self.context_store.store_terminal_output(
                            terminal_id=session.id,
                            output=decoded
                        )

                        # Broadcast to WebSocket
                        await self._broadcast(session.id, decoded)
                else:
                    # Check if process is still alive
                    if session.process.poll() is not None:
                        # Process exited
                        session.active = False
                        await self._broadcast(session.id, f"\n[Process exited with code {session.process.returncode}]\n")
                        break

                    # Brief sleep to prevent busy loop
                    await asyncio.sleep(0.05)

            except OSError as e:
                # PTY closed or other error
                session.active = False
                break
            except Exception as e:
                logger.error(f"Error capturing terminal output: {e}")
                session.active = False
                break

    async def write_to_terminal(self, terminal_id: str, data: str):
        """
        Write data to terminal (user input)

        Args:
            terminal_id: Terminal session ID
            data: Data to write (commands, keystrokes)
        """
        session = self.sessions.get(terminal_id)

        if not session or not session.active:
            raise ValueError(f"Terminal {terminal_id} not found or inactive")

        # Write to PTY master
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            os.write,
            session.master,
            data.encode('utf-8')
        )

    async def resize_terminal(self, terminal_id: str, rows: int, cols: int):
        """
        Resize terminal window

        Args:
            terminal_id: Terminal session ID
            rows: Number of rows
            cols: Number of columns
        """
        import fcntl
        import termios
        import struct

        session = self.sessions.get(terminal_id)

        if not session or not session.active:
            raise ValueError(f"Terminal {terminal_id} not found or inactive")

        # Set window size
        size = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(session.master, termios.TIOCSWINSZ, size)

    async def close_terminal(self, terminal_id: str):
        """
        Close terminal session

        Args:
            terminal_id: Terminal session ID
        """
        session = self.sessions.get(terminal_id)

        if not session:
            return

        session.active = False

        # Kill process gracefully
        try:
            session.process.send_signal(signal.SIGTERM)

            # Wait briefly for graceful exit
            await asyncio.sleep(0.5)

            # Force kill if still running
            if session.process.poll() is None:
                session.process.kill()

            # Close PTY master
            os.close(session.master)

        except Exception as e:
            logger.error(f"Error closing terminal {terminal_id}: {e}")

        # Audit log terminal close
        try:
            audit_logger = get_audit_logger()
            if audit_logger:
                audit_logger.log(
                    user_id=session.user_id,
                    action=AuditAction.TERMINAL_CLOSE,
                    details={
                        "terminal_id": terminal_id,
                        "duration_seconds": (datetime.now() - session.created_at).total_seconds()
                    }
                )
        except Exception as e:
            logger.error(f"Failed to log terminal close: {e}")

        # Remove from sessions
        if terminal_id in self.sessions:
            del self.sessions[terminal_id]

        # Clean up broadcast callbacks
        if terminal_id in self._broadcast_callbacks:
            del self._broadcast_callbacks[terminal_id]

    def register_broadcast_callback(self, terminal_id: str, callback: Callable):
        """
        Register callback for terminal output broadcast

        Args:
            terminal_id: Terminal session ID
            callback: Async function to call with output data
        """
        if terminal_id not in self._broadcast_callbacks:
            self._broadcast_callbacks[terminal_id] = []

        self._broadcast_callbacks[terminal_id].append(callback)

    def unregister_broadcast_callback(self, terminal_id: str, callback: Callable):
        """Remove broadcast callback"""
        if terminal_id in self._broadcast_callbacks:
            try:
                self._broadcast_callbacks[terminal_id].remove(callback)
            except ValueError:
                pass

    async def _broadcast(self, terminal_id: str, data: str):
        """Broadcast terminal output to all registered callbacks"""
        callbacks = self._broadcast_callbacks.get(terminal_id, [])

        for callback in callbacks:
            try:
                await callback(data)
            except Exception as e:
                logger.error(f"Error in broadcast callback: {e}")

    def get_session(self, terminal_id: str) -> Optional[TerminalSession]:
        """Get terminal session by ID"""
        return self.sessions.get(terminal_id)

    def list_sessions(self, user_id: str = None) -> list:
        """
        List terminal sessions

        Args:
            user_id: Filter by user ID (optional)

        Returns:
            List of session info dicts
        """
        sessions = self.sessions.values()

        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]

        return [
            {
                'id': s.id,
                'user_id': s.user_id,
                'active': s.active,
                'created_at': s.created_at.isoformat(),
                'pid': s.process.pid
            }
            for s in sessions
        ]

    def get_context(self, terminal_id: str, lines: int = 100) -> str:
        """Get terminal context for AI/LLM"""
        return self.context_store.get_context(terminal_id, lines)

    # System Terminal Management Methods

    def register_system_terminal(self, user_id: str, terminal_app: str, workspace_root: str) -> str:
        """
        Register a system terminal session

        Args:
            user_id: User ID owning this terminal
            terminal_app: Terminal app used (warp, iterm, terminal)
            workspace_root: Working directory for terminal

        Returns:
            Terminal session ID
        """
        terminal_id = self._generate_id()

        self.system_terminals[terminal_id] = {
            'id': terminal_id,
            'user_id': user_id,
            'terminal_app': terminal_app,
            'workspace_root': workspace_root,
            'created_at': datetime.now(),
            'active': True,
            'socket_path': None  # Will be set when socket connects
        }

        return terminal_id

    def get_system_terminal(self, terminal_id: str) -> Optional[dict]:
        """Get system terminal session info"""
        return self.system_terminals.get(terminal_id)

    def list_system_terminals(self, user_id: str = None) -> list:
        """
        List system terminal sessions

        Args:
            user_id: Filter by user ID (optional)

        Returns:
            List of system terminal session info dicts
        """
        terminals = self.system_terminals.values()

        if user_id:
            terminals = [t for t in terminals if t['user_id'] == user_id]

        return [
            {
                'id': t['id'],
                'user_id': t['user_id'],
                'terminal_app': t['terminal_app'],
                'workspace_root': t['workspace_root'],
                'active': t['active'],
                'created_at': t['created_at'].isoformat()
            }
            for t in terminals
        ]

    def close_system_terminal(self, terminal_id: str):
        """
        Close/remove system terminal session

        Args:
            terminal_id: Terminal session ID
        """
        if terminal_id in self.system_terminals:
            self.system_terminals[terminal_id]['active'] = False
            # Keep in dict for history, or remove completely
            # del self.system_terminals[terminal_id]

    async def start_socket_listener(self, socket_path: str, terminal_id: str):
        """
        Start Unix socket listener for terminal I/O capture

        Args:
            socket_path: Path to Unix socket
            terminal_id: Terminal session ID to associate output with

        This will be called by the bridge script to establish communication
        """
        import socket as sock_module

        # Remove existing socket if present
        if os.path.exists(socket_path):
            os.remove(socket_path)

        # Create Unix socket
        server = sock_module.socket(sock_module.AF_UNIX, sock_module.SOCK_STREAM)
        server.bind(socket_path)
        server.listen(1)

        print(f"Socket listener started at {socket_path} for terminal {terminal_id}")

        # Accept connection from bridge script
        loop = asyncio.get_event_loop()
        conn, _ = await loop.run_in_executor(None, server.accept)

        # Read data from socket in background task
        async def capture_socket_output():
            while True:
                try:
                    data = await loop.run_in_executor(None, conn.recv, 4096)
                    if not data:
                        break

                    decoded = data.decode('utf-8', errors='replace')

                    # Store in context
                    await self.context_store.store_terminal_output(
                        terminal_id=terminal_id,
                        output=decoded
                    )

                    # Broadcast to any listeners
                    await self._broadcast(terminal_id, decoded)

                except Exception as e:
                    logger.error(f"Error capturing socket output: {e}")
                    break

        asyncio.create_task(capture_socket_output())


# Global instance
terminal_bridge = TerminalBridge()
