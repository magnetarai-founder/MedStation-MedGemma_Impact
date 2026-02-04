"""
Aider Subprocess Runner

Concrete implementation of AiderBridge using subprocess.
Runs Aider commands and parses output for edit information.

SECURITY NOTE:
This module uses asyncio.create_subprocess_exec() which accepts
command arguments as a Python list, NOT a shell string. This is
the SAFE subprocess pattern that prevents command injection:

    SAFE (this module):
        await asyncio.create_subprocess_exec("aider", "--model", model, ...)

    UNSAFE (NOT used):
        await asyncio.create_subprocess_shell(f"aider --model {model}")

All user-provided values (file paths, instructions) are passed as
discrete list elements, never interpolated into a shell string.
"""

import asyncio
import logging
import re
import time
from pathlib import Path
from typing import Any, AsyncIterator

from .bridge import AiderBridge, AiderEdit, AiderResponse, EditType
from .config import AiderConfig
from .context_sync import ContextSynchronizer

logger = logging.getLogger(__name__)


class SubprocessAiderBridge(AiderBridge):
    """
    Aider integration via subprocess.

    Features:
    - Per-request subprocess invocation
    - Output parsing for edits
    - Streaming support
    - Context synchronization
    """

    def __init__(
        self,
        config: AiderConfig,
        context_sync: ContextSynchronizer | None = None,
    ):
        """
        Initialize subprocess bridge.

        Args:
            config: Aider configuration
            context_sync: Optional context synchronizer
        """
        self._config = config
        self._context_sync = context_sync or ContextSynchronizer(
            config.workspace_root
        )

    def is_available(self) -> bool:
        """Check if Aider is available"""
        import shutil
        return shutil.which("aider") is not None

    async def execute_edit(
        self,
        instruction: str,
        files: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> AiderResponse:
        """
        Run an editing instruction.

        Args:
            instruction: What to do
            files: Specific files to edit
            context: Additional context

        Returns:
            AiderResponse with edits made
        """
        start_time = time.time()

        # Build command as list (safe pattern)
        cmd = self._build_command(instruction, files)

        try:
            # SAFE: create_subprocess_exec with list args
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._config.workspace_root,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self._config.timeout_seconds,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # Parse output
            output_text = stdout.decode("utf-8", errors="replace")
            error_text = stderr.decode("utf-8", errors="replace")

            if process.returncode != 0:
                return AiderResponse(
                    success=False,
                    message=output_text,
                    error=error_text or f"Exit code: {process.returncode}",
                    error_type="ProcessError",
                    duration_ms=duration_ms,
                    model=self._config.model,
                )

            # Parse edits from output
            edits = self._parse_edits(output_text, files or [])

            # Update context sync
            if edits and self._context_sync:
                modified_paths = [e.file_path for e in edits]
                self._context_sync.mark_in_aider_context(modified_paths, True)
                self._context_sync.sync_complete()

            return AiderResponse(
                success=True,
                message=output_text,
                edits=edits,
                duration_ms=duration_ms,
                model=self._config.model,
            )

        except asyncio.TimeoutError:
            return AiderResponse(
                success=False,
                message="",
                error=f"Timeout after {self._config.timeout_seconds}s",
                error_type="TimeoutError",
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except OSError as e:
            logger.error(f"Failed to run Aider: {e}")
            return AiderResponse(
                success=False,
                message="",
                error=str(e),
                error_type="OSError",
            )

    async def stream_edit(
        self,
        instruction: str,
        files: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream editing progress.

        Args:
            instruction: What to do
            files: Specific files to edit
            context: Additional context

        Yields:
            Output chunks
        """
        cmd = self._build_command(instruction, files)
        process = None

        try:
            # SAFE: create_subprocess_exec with list args
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=self._config.workspace_root,
            )

            if process.stdout:
                while True:
                    chunk = await process.stdout.read(256)
                    if not chunk:
                        break
                    yield chunk.decode("utf-8", errors="replace")

            await process.wait()

        except asyncio.CancelledError:
            if process:
                process.kill()
            raise
        except OSError as e:
            yield f"\nError: {e}\n"

    async def analyze_code(
        self,
        question: str,
        files: list[str] | None = None,
    ) -> str:
        """
        Ask Aider to analyze code without making changes.

        Args:
            question: What to analyze
            files: Files to analyze

        Returns:
            Aider's analysis
        """
        # Use /ask mode which doesn't make changes
        cmd = self._build_command(
            question, files, message_mode="ask"
        )

        try:
            # SAFE: create_subprocess_exec with list args
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._config.workspace_root,
            )

            stdout, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=self._config.timeout_seconds,
            )

            return stdout.decode("utf-8", errors="replace")

        except asyncio.TimeoutError:
            return f"Analysis timed out after {self._config.timeout_seconds}s"
        except OSError as e:
            return f"Error: {e}"

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
        # Use dry-run mode
        cmd = self._build_command(instruction, files)
        cmd.append("--dry-run")

        try:
            # SAFE: create_subprocess_exec with list args
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._config.workspace_root,
            )

            stdout, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=self._config.timeout_seconds,
            )

            output = stdout.decode("utf-8", errors="replace")
            return self._parse_edits(output, files or [])

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Diff preview failed: {e}")
            return []

    def _build_command(
        self,
        message: str,
        files: list[str] | None = None,
        message_mode: str = "message",
    ) -> list[str]:
        """
        Build Aider command as list of arguments.

        This returns a Python list for safe subprocess invocation.
        Each element is passed as a discrete argument, preventing
        any shell interpretation or injection.
        """
        cmd = ["aider"]

        # Model configuration
        cmd.extend(["--model", self._config.model])

        if self._config.ollama_url:
            cmd.extend(["--openai-api-base", self._config.ollama_url])

        # Edit format (EditFormat enum has .value)
        edit_fmt = self._config.edit_format
        if hasattr(edit_fmt, 'value'):
            edit_fmt = edit_fmt.value
        cmd.extend(["--edit-format", edit_fmt])

        # Behavior flags
        if not self._config.auto_commits:
            cmd.append("--no-auto-commit")

        if not self._config.git_enabled:
            cmd.append("--no-git")

        cmd.append("--no-pretty")
        cmd.append("--yes")  # Auto-confirm

        # Add files
        if files:
            for file_path in files:
                # Resolve to absolute path within workspace
                resolved = self._resolve_file_path(file_path)
                if resolved:
                    cmd.append(resolved)

        # Message mode
        if message_mode == "ask":
            cmd.extend(["--message", f"/ask {message}"])
        else:
            cmd.extend(["--message", message])

        return cmd

    def _resolve_file_path(self, file_path: str) -> str | None:
        """
        Resolve file path safely within workspace.

        Returns None if path is outside workspace.
        """
        try:
            workspace = Path(self._config.workspace_root).resolve()
            target = (workspace / file_path).resolve()

            # Security: ensure path is within workspace
            if not str(target).startswith(str(workspace)):
                logger.warning(f"Path outside workspace: {file_path}")
                return None

            if target.exists():
                return str(target)

            # Allow non-existent paths for new files
            return str(target)

        except (ValueError, OSError) as e:
            logger.warning(f"Invalid path {file_path}: {e}")
            return None

    def _parse_edits(
        self, output: str, files: list[str]
    ) -> list[AiderEdit]:
        """
        Parse Aider output to extract edits.

        Handles diff format output.
        """
        edits: list[AiderEdit] = []

        # Pattern for file changes in diff format
        # Look for: --- a/path/to/file.py
        #           +++ b/path/to/file.py
        diff_pattern = re.compile(
            r"^---\s+a/(.+?)$\n^\+\+\+\s+b/(.+?)$",
            re.MULTILINE
        )

        # Pattern for new files
        new_file_pattern = re.compile(
            r"^Creating\s+(.+?)$|^Wrote\s+(.+?)$",
            re.MULTILINE
        )

        # Find diff blocks
        for match in diff_pattern.finditer(output):
            old_path = match.group(1)
            new_path = match.group(2)

            # Determine edit type
            if old_path == "/dev/null":
                edit_type = EditType.CREATE
                file_path = new_path
            elif new_path == "/dev/null":
                edit_type = EditType.DELETE
                file_path = old_path
            elif old_path != new_path:
                edit_type = EditType.RENAME
                file_path = new_path
            else:
                edit_type = EditType.MODIFY
                file_path = new_path

            # Extract diff hunk
            hunk_start = match.end()
            hunk_end = output.find("\n---", hunk_start)
            if hunk_end == -1:
                hunk_end = len(output)

            hunk = output[hunk_start:hunk_end].strip()

            # Count lines
            lines_added = hunk.count("\n+") - hunk.count("\n+++")
            lines_removed = hunk.count("\n-") - hunk.count("\n---")

            edits.append(AiderEdit(
                file_path=file_path,
                edit_type=edit_type,
                description=f"{edit_type.value}: {file_path}",
                lines_added=max(0, lines_added),
                lines_removed=max(0, lines_removed),
                diff_hunks=[hunk] if hunk else [],
                old_path=old_path if edit_type == EditType.RENAME else None,
            ))

        # Check for new file creation messages
        for match in new_file_pattern.finditer(output):
            file_path = match.group(1) or match.group(2)
            if file_path:
                # Don't duplicate if already in edits
                if not any(e.file_path == file_path for e in edits):
                    edits.append(AiderEdit(
                        file_path=file_path,
                        edit_type=EditType.CREATE,
                        description=f"Created: {file_path}",
                    ))

        return edits


class SessionAiderBridge(AiderBridge):
    """
    Aider integration using persistent sessions.

    Wraps ManagedAiderSession for the AiderBridge interface.
    """

    def __init__(
        self,
        config: AiderConfig,
        session_manager=None,  # AiderSessionManager
    ):
        """
        Initialize session-based bridge.

        Args:
            config: Aider configuration
            session_manager: Optional session manager
        """
        self._config = config
        self._session_manager = session_manager
        self._current_session = None

    def is_available(self) -> bool:
        """Check if Aider is available"""
        import shutil
        return shutil.which("aider") is not None

    async def _get_session(self):
        """Get or create session"""
        if self._session_manager:
            from .session import SessionConfig
            config = SessionConfig(
                workspace_root=self._config.workspace_root,
                model=self._config.model,
                edit_format=self._config.edit_format,
                auto_commit=self._config.auto_commit,
            )
            return await self._session_manager.get_session(
                self._config.workspace_root, config
            )
        return None

    async def execute_edit(
        self,
        instruction: str,
        files: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> AiderResponse:
        """Run edit via session"""
        session = await self._get_session()
        if not session:
            return AiderResponse(
                success=False,
                message="",
                error="No session available",
                error_type="SessionError",
            )

        # Add files to context
        if files:
            await session.add_files(files)

        # Send instruction
        return await session.send(instruction)

    async def stream_edit(
        self,
        instruction: str,
        files: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        """Stream not supported in session mode, fallback"""
        response = await self.execute_edit(instruction, files, context)
        yield response.message

    async def analyze_code(
        self,
        question: str,
        files: list[str] | None = None,
    ) -> str:
        """Analyze code via session"""
        session = await self._get_session()
        if not session:
            return "No session available"

        if files:
            await session.add_files(files)

        response = await session.send(f"/ask {question}")
        return response.message

    async def get_diff_preview(
        self,
        instruction: str,
        files: list[str] | None = None,
    ) -> list[AiderEdit]:
        """Diff preview not supported in session mode"""
        return []


def create_aider_bridge(
    config: AiderConfig,
    use_sessions: bool = False,
    session_manager=None,
) -> AiderBridge:
    """
    Factory function to create appropriate Aider bridge.

    Args:
        config: Aider configuration
        use_sessions: Whether to use persistent sessions
        session_manager: Optional session manager

    Returns:
        Configured AiderBridge implementation
    """
    if use_sessions:
        return SessionAiderBridge(config, session_manager)
    else:
        return SubprocessAiderBridge(config)
