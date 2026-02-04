"""
Aider Bridge Interface

Abstract interface for Aider integration.
Supports both subprocess-based and session-based execution.

Provides concrete implementations:
- SubprocessAiderBridge: Runs aider as subprocess per-request
- AiderSessionImpl: Maintains persistent aider session
"""

import asyncio
import logging
import os
import re
import shutil
import subprocess
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)


class EditType(Enum):
    """Types of edits Aider can make"""

    CREATE = "create"  # New file created
    MODIFY = "modify"  # Existing file modified
    DELETE = "delete"  # File deleted
    RENAME = "rename"  # File renamed


@dataclass
class AiderEdit:
    """
    A single edit made by Aider.

    Represents one file change with before/after content.
    """

    file_path: str
    edit_type: EditType
    description: str = ""

    # Content (for create/modify)
    old_content: str | None = None
    new_content: str | None = None

    # For renames
    old_path: str | None = None

    # Diff information
    lines_added: int = 0
    lines_removed: int = 0
    diff_hunks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "edit_type": self.edit_type.value,
            "description": self.description,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "has_content": self.new_content is not None,
        }

    @property
    def summary(self) -> str:
        """Brief summary of the edit"""
        return f"{self.edit_type.value}: {self.file_path} (+{self.lines_added}/-{self.lines_removed})"


@dataclass
class AiderMessage:
    """
    A message in the Aider conversation.

    Tracks the conversation history for context.
    """

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # For assistant messages, track any edits made
    edits: list[AiderEdit] = field(default_factory=list)


@dataclass
class AiderResponse:
    """
    Response from an Aider editing session.

    Contains all edits made and conversation context.
    """

    success: bool
    message: str  # Aider's response message

    # Edits made
    edits: list[AiderEdit] = field(default_factory=list)

    # Execution stats
    tokens_used: int = 0
    model: str = ""
    duration_ms: int = 0

    # Conversation context
    conversation: list[AiderMessage] = field(default_factory=list)

    # Error information
    error: str | None = None
    error_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message[:500],  # Truncate for logging
            "edits": [e.to_dict() for e in self.edits],
            "tokens_used": self.tokens_used,
            "model": self.model,
            "duration_ms": self.duration_ms,
            "edit_count": len(self.edits),
            "error": self.error,
        }

    @property
    def files_modified(self) -> list[str]:
        """Get list of all modified files"""
        return [e.file_path for e in self.edits]

    @property
    def total_lines_changed(self) -> int:
        """Total lines added + removed"""
        return sum(e.lines_added + e.lines_removed for e in self.edits)


class AiderBridge(ABC):
    """
    Abstract interface for Aider integration.

    Implementations:
    - SubprocessAiderBridge: Runs aider as subprocess per-request
    - SessionAiderBridge: Maintains persistent aider session
    """

    @abstractmethod
    async def execute_edit(
        self,
        instruction: str,
        files: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> AiderResponse:
        """
        Execute an editing instruction.

        Args:
            instruction: What to do (e.g., "Add error handling to the login function")
            files: Specific files to edit (optional, aider can find them)
            context: Additional context (conversation history, workspace info)

        Returns:
            AiderResponse with edits made
        """
        pass

    @abstractmethod
    async def stream_edit(
        self,
        instruction: str,
        files: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream editing progress.

        Yields chunks of output as aider works.

        Args:
            instruction: What to do
            files: Specific files to edit
            context: Additional context

        Yields:
            Output chunks (text, diff hunks, etc.)
        """
        pass

    @abstractmethod
    async def analyze_code(
        self,
        question: str,
        files: list[str] | None = None,
    ) -> str:
        """
        Ask aider to analyze code without making changes.

        Args:
            question: What to analyze
            files: Files to analyze

        Returns:
            Aider's analysis
        """
        pass

    @abstractmethod
    async def get_diff_preview(
        self,
        instruction: str,
        files: list[str] | None = None,
    ) -> list[AiderEdit]:
        """
        Get a preview of changes without applying them.

        Args:
            instruction: What would be changed
            files: Files that would be affected

        Returns:
            List of proposed edits
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if Aider is available and configured"""
        pass


class AiderSession(ABC):
    """
    Abstract interface for persistent Aider sessions.

    Maintains conversation context across multiple interactions.
    """

    @property
    @abstractmethod
    def session_id(self) -> str:
        """Unique session identifier"""
        pass

    @property
    @abstractmethod
    def is_active(self) -> bool:
        """Check if session is still active"""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start the session"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the session"""
        pass

    @abstractmethod
    async def send(self, message: str) -> AiderResponse:
        """Send a message and get response"""
        pass

    @abstractmethod
    async def add_files(self, files: list[str]) -> None:
        """Add files to the session context"""
        pass

    @abstractmethod
    async def remove_files(self, files: list[str]) -> None:
        """Remove files from the session context"""
        pass

    @abstractmethod
    def get_conversation_history(self) -> list[AiderMessage]:
        """Get the conversation history"""
        pass

    @abstractmethod
    def clear_history(self) -> None:
        """Clear conversation history"""
        pass


# ==============================================================================
# Concrete Implementations
# ==============================================================================


class SubprocessAiderBridge(AiderBridge):
    """
    Subprocess-based Aider bridge.

    Runs aider as a subprocess for each request. Suitable for
    stateless operations where context doesn't need to persist.

    SECURITY NOTE: Uses asyncio.create_subprocess_exec which passes
    arguments as a list (not shell string), preventing command injection.
    """

    def __init__(
        self,
        workspace_path: str | Path | None = None,
        model: str = "gpt-4",
        aider_path: str | None = None,
    ):
        """
        Initialize subprocess bridge.

        Args:
            workspace_path: Working directory for aider operations
            model: LLM model to use (default: gpt-4)
            aider_path: Path to aider executable (auto-detected if None)
        """
        self.workspace_path = Path(workspace_path) if workspace_path else Path.cwd()
        self.model = model
        self._aider_path = aider_path
        self._available: bool | None = None

    @property
    def aider_path(self) -> str | None:
        """Get path to aider executable."""
        if self._aider_path:
            return self._aider_path
        return shutil.which("aider")

    def is_available(self) -> bool:
        """Check if Aider is available and configured."""
        if self._available is not None:
            return self._available

        aider = self.aider_path
        if not aider:
            logger.warning("Aider not found in PATH")
            self._available = False
            return False

        try:
            # SECURITY: Using run with list args, not shell=True
            result = subprocess.run(
                [aider, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                shell=False,  # Explicitly disable shell
            )
            self._available = result.returncode == 0
            if self._available:
                logger.info(f"Aider available: {result.stdout.strip()}")
            return self._available
        except Exception as e:
            logger.warning(f"Aider availability check failed: {e}")
            self._available = False
            return False

    async def execute_edit(
        self,
        instruction: str,
        files: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> AiderResponse:
        """Execute an editing instruction using aider subprocess."""
        start_time = time.monotonic()

        if not self.is_available():
            return AiderResponse(
                success=False,
                message="Aider is not available",
                error="Aider executable not found",
                error_type="NOT_AVAILABLE",
            )

        # Build command as list (safe from injection)
        cmd = [
            self.aider_path,
            "--model", self.model,
            "--no-auto-commits",
            "--yes",
            "--no-pretty",
            "--message", instruction,
        ]

        # Add files if specified
        if files:
            for f in files:
                cmd.extend(["--file", f])

        try:
            # SECURITY: create_subprocess_exec uses execvp, not shell
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace_path),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300,
            )

            duration_ms = int((time.monotonic() - start_time) * 1000)
            output = stdout.decode("utf-8", errors="replace")
            error_output = stderr.decode("utf-8", errors="replace")

            edits = self._parse_edits(output)

            if process.returncode == 0:
                return AiderResponse(
                    success=True,
                    message=output,
                    edits=edits,
                    model=self.model,
                    duration_ms=duration_ms,
                )
            else:
                return AiderResponse(
                    success=False,
                    message=output,
                    edits=edits,
                    model=self.model,
                    duration_ms=duration_ms,
                    error=error_output or "Aider returned non-zero exit code",
                    error_type="EXECUTION_ERROR",
                )

        except asyncio.TimeoutError:
            return AiderResponse(
                success=False,
                message="",
                error="Aider execution timed out after 5 minutes",
                error_type="TIMEOUT",
                duration_ms=300000,
            )
        except Exception as e:
            logger.error(f"Aider execution failed: {e}")
            return AiderResponse(
                success=False,
                message="",
                error=str(e),
                error_type="EXCEPTION",
            )

    async def stream_edit(
        self,
        instruction: str,
        files: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        """Stream editing progress."""
        if not self.is_available():
            yield "Error: Aider is not available"
            return

        cmd = [
            self.aider_path,
            "--model", self.model,
            "--no-auto-commits",
            "--yes",
            "--message", instruction,
        ]

        if files:
            for f in files:
                cmd.extend(["--file", f])

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(self.workspace_path),
            )

            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                yield line.decode("utf-8", errors="replace")

            await process.wait()

        except Exception as e:
            yield f"Error: {e}"

    async def analyze_code(
        self,
        question: str,
        files: list[str] | None = None,
    ) -> str:
        """Ask aider to analyze code without making changes."""
        instruction = f"[ANALYZE ONLY - DO NOT MODIFY] {question}"

        response = await self.execute_edit(
            instruction=instruction,
            files=files,
        )

        return response.message if response.success else f"Error: {response.error}"

    async def get_diff_preview(
        self,
        instruction: str,
        files: list[str] | None = None,
    ) -> list[AiderEdit]:
        """Get a preview of changes without applying them."""
        response = await self.execute_edit(
            instruction=f"[DRY RUN] {instruction}",
            files=files,
        )

        return response.edits

    def _parse_edits(self, output: str) -> list[AiderEdit]:
        """Parse aider output to extract edits."""
        edits = []

        file_pattern = re.compile(
            r"^(\S+\.(?:py|js|ts|go|rs|java|c|cpp|h|md|txt|json|yaml|yml))$",
            re.MULTILINE
        )
        diff_pattern = re.compile(r"^([+-])\s*(.*)$", re.MULTILINE)

        current_file = None
        lines_added = 0
        lines_removed = 0

        for line in output.split("\n"):
            file_match = file_pattern.match(line.strip())
            if file_match:
                if current_file:
                    edits.append(AiderEdit(
                        file_path=current_file,
                        edit_type=EditType.MODIFY,
                        lines_added=lines_added,
                        lines_removed=lines_removed,
                    ))
                current_file = file_match.group(1)
                lines_added = 0
                lines_removed = 0
            elif current_file:
                diff_match = diff_pattern.match(line)
                if diff_match:
                    if diff_match.group(1) == "+":
                        lines_added += 1
                    else:
                        lines_removed += 1

        if current_file:
            edits.append(AiderEdit(
                file_path=current_file,
                edit_type=EditType.MODIFY,
                lines_added=lines_added,
                lines_removed=lines_removed,
            ))

        return edits


class AiderSessionImpl(AiderSession):
    """
    Concrete implementation of persistent Aider session.

    Maintains a running aider process for interactive editing.

    SECURITY NOTE: Uses asyncio.create_subprocess_exec which passes
    arguments as a list (not shell string), preventing command injection.
    """

    def __init__(
        self,
        workspace_path: str | Path,
        model: str = "gpt-4",
        aider_path: str | None = None,
    ):
        """
        Initialize session.

        Args:
            workspace_path: Working directory for the session
            model: LLM model to use
            aider_path: Path to aider executable
        """
        self._session_id = str(uuid.uuid4())
        self.workspace_path = Path(workspace_path)
        self.model = model
        self._aider_path = aider_path or shutil.which("aider")
        self._process: asyncio.subprocess.Process | None = None
        self._is_active = False
        self._conversation: list[AiderMessage] = []
        self._files: set[str] = set()
        self._lock = asyncio.Lock()

    @property
    def session_id(self) -> str:
        """Unique session identifier."""
        return self._session_id

    @property
    def is_active(self) -> bool:
        """Check if session is still active."""
        return self._is_active and self._process is not None

    async def start(self) -> None:
        """Start the aider session."""
        if self._is_active:
            logger.warning(f"Session {self._session_id} already active")
            return

        if not self._aider_path:
            raise RuntimeError("Aider executable not found")

        cmd = [
            self._aider_path,
            "--model", self.model,
            "--no-auto-commits",
            "--no-pretty",
        ]

        try:
            # SECURITY: create_subprocess_exec uses execvp, not shell
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(self.workspace_path),
            )
            self._is_active = True
            logger.info(f"Started Aider session {self._session_id}")

            # Read initial output/prompt
            await self._read_until_prompt()

        except Exception as e:
            logger.error(f"Failed to start Aider session: {e}")
            raise

    async def stop(self) -> None:
        """Stop the session."""
        if not self._is_active:
            return

        try:
            if self._process:
                self._process.stdin.write(b"/exit\n")
                await self._process.stdin.drain()

                try:
                    await asyncio.wait_for(self._process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    self._process.terminate()
                    await self._process.wait()

        except Exception as e:
            logger.warning(f"Error stopping session {self._session_id}: {e}")
            if self._process:
                self._process.kill()

        finally:
            self._is_active = False
            self._process = None
            logger.info(f"Stopped Aider session {self._session_id}")

    async def send(self, message: str) -> AiderResponse:
        """Send a message and get response."""
        async with self._lock:
            if not self.is_active:
                return AiderResponse(
                    success=False,
                    message="",
                    error="Session not active",
                    error_type="SESSION_INACTIVE",
                )

            start_time = time.monotonic()

            try:
                self._conversation.append(AiderMessage(role="user", content=message))

                self._process.stdin.write(f"{message}\n".encode("utf-8"))
                await self._process.stdin.drain()

                response_text = await self._read_until_prompt()
                duration_ms = int((time.monotonic() - start_time) * 1000)

                edits = self._parse_response_edits(response_text)

                self._conversation.append(AiderMessage(
                    role="assistant",
                    content=response_text,
                    edits=edits,
                ))

                return AiderResponse(
                    success=True,
                    message=response_text,
                    edits=edits,
                    model=self.model,
                    duration_ms=duration_ms,
                    conversation=self._conversation.copy(),
                )

            except Exception as e:
                logger.error(f"Error in session {self._session_id}: {e}")
                return AiderResponse(
                    success=False,
                    message="",
                    error=str(e),
                    error_type="SEND_ERROR",
                )

    async def add_files(self, files: list[str]) -> None:
        """Add files to the session context."""
        async with self._lock:
            if not self.is_active:
                raise RuntimeError("Session not active")

            for file_path in files:
                if file_path not in self._files:
                    self._process.stdin.write(f"/add {file_path}\n".encode("utf-8"))
                    await self._process.stdin.drain()
                    await self._read_until_prompt()
                    self._files.add(file_path)

    async def remove_files(self, files: list[str]) -> None:
        """Remove files from the session context."""
        async with self._lock:
            if not self.is_active:
                raise RuntimeError("Session not active")

            for file_path in files:
                if file_path in self._files:
                    self._process.stdin.write(f"/drop {file_path}\n".encode("utf-8"))
                    await self._process.stdin.drain()
                    await self._read_until_prompt()
                    self._files.discard(file_path)

    def get_conversation_history(self) -> list[AiderMessage]:
        """Get the conversation history."""
        return self._conversation.copy()

    def clear_history(self) -> None:
        """Clear conversation history."""
        self._conversation.clear()

    async def _read_until_prompt(self, timeout: float = 60) -> str:
        """Read output until we see the aider prompt."""
        output = []

        try:
            while True:
                line = await asyncio.wait_for(
                    self._process.stdout.readline(),
                    timeout=timeout,
                )
                if not line:
                    break

                text = line.decode("utf-8", errors="replace")
                output.append(text)

                if text.strip().endswith(">") or "aider>" in text.lower():
                    break

        except asyncio.TimeoutError:
            logger.warning(f"Timeout reading from session {self._session_id}")

        return "".join(output)

    def _parse_response_edits(self, response: str) -> list[AiderEdit]:
        """Parse edits from session response."""
        edits = []

        file_pattern = re.compile(r"(Created|Modified|Wrote)\s+(\S+)")

        for match in file_pattern.finditer(response):
            action = match.group(1).lower()
            file_path = match.group(2)

            edit_type = EditType.CREATE if action == "created" else EditType.MODIFY

            edits.append(AiderEdit(
                file_path=file_path,
                edit_type=edit_type,
                description=f"{action} {file_path}",
            ))

        return edits


# ==============================================================================
# Factory Functions
# ==============================================================================


def get_aider_bridge(
    workspace_path: str | Path | None = None,
    model: str = "gpt-4",
    use_session: bool = False,
) -> AiderBridge | AiderSession:
    """
    Get an appropriate Aider bridge instance.

    Args:
        workspace_path: Working directory for operations
        model: LLM model to use
        use_session: If True, return a session-based bridge

    Returns:
        AiderBridge or AiderSession instance
    """
    if use_session:
        return AiderSessionImpl(
            workspace_path=workspace_path or Path.cwd(),
            model=model,
        )
    else:
        return SubprocessAiderBridge(
            workspace_path=workspace_path,
            model=model,
        )
