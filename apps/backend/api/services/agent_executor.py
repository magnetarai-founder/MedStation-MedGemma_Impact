"""
Agent Executor Service

Executes coding tasks using AI agent engines (Aider, Continue, Codex).
Manages task queue, execution, and result storage.
"""

import asyncio
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from api.utils.structured_logging import get_logger

logger = get_logger(__name__)


class AgentEngine(str, Enum):
    """Available agent engines"""

    AIDER = "aider"
    CONTINUE = "continue"
    CODEX = "codex"
    AUTO = "auto"  # Automatically choose best engine


class TaskStatus(str, Enum):
    """Task execution status"""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentTask:
    """Represents a coding task for an agent"""

    id: str
    repo_path: str
    instructions: str
    file: str | None = None
    mode: str | None = None
    engine: AgentEngine = AgentEngine.AUTO
    status: TaskStatus = TaskStatus.QUEUED
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    output: list[str] = field(default_factory=list)


class AgentExecutor:
    """
    Manages execution of coding tasks using AI agent engines.

    Features:
    - Task queue with async execution
    - Multiple agent engine support (Aider, Continue, Codex)
    - Result caching and storage
    - Progress tracking
    """

    def __init__(
        self, ollama_url: str = "http://localhost:11434", default_model: str = "qwen2.5-coder:3b"
    ):
        self.ollama_url = ollama_url
        self.default_model = default_model
        self.tasks: dict[str, AgentTask] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.worker_running = False

    async def start_worker(self):
        """Start background worker to process tasks"""
        if self.worker_running:
            return

        self.worker_running = True
        self._worker_task = asyncio.create_task(self._process_queue())

    async def _process_queue(self):
        """Background worker that processes queued tasks"""
        while self.worker_running:
            try:
                task_id = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                task = self.tasks.get(task_id)

                if task and task.status == TaskStatus.QUEUED:
                    await self._execute_task(task)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Queue worker error: {e}")

    async def submit_task(
        self,
        repo_path: str,
        instructions: str,
        file: str | None = None,
        mode: str | None = None,
        engine: AgentEngine = AgentEngine.AUTO,
    ) -> str:
        """
        Submit a new coding task.

        Args:
            repo_path: Path to repository
            instructions: Task instructions for the agent
            file: Optional specific file to work on
            mode: Optional mode (code_review, test, doc, refactor)
            engine: Which agent engine to use

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())

        task = AgentTask(
            id=task_id,
            repo_path=repo_path,
            instructions=instructions,
            file=file,
            mode=mode,
            engine=engine,
        )

        self.tasks[task_id] = task
        await self.task_queue.put(task_id)

        # Ensure worker is running
        await self.start_worker()

        return task_id

    async def _execute_task(self, task: AgentTask):
        """
        Execute a task using the appropriate agent engine.

        Args:
            task: Task to execute
        """
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc).isoformat()

        try:
            # Choose engine
            engine = task.engine
            if engine == AgentEngine.AUTO:
                engine = self._choose_engine(task)

            # Execute based on engine
            if engine == AgentEngine.AIDER:
                result = await self._execute_aider(task)
            elif engine == AgentEngine.CONTINUE:
                result = await self._execute_continue(task)
            elif engine == AgentEngine.CODEX:
                result = await self._execute_codex(task)
            else:
                raise ValueError(f"Unknown engine: {engine}")

            task.status = TaskStatus.COMPLETED
            task.result = result

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)

        finally:
            task.completed_at = datetime.now(timezone.utc).isoformat()

    def _choose_engine(self, task: AgentTask) -> AgentEngine:
        """
        Automatically choose the best engine for a task.

        Args:
            task: Task to analyze

        Returns:
            Best engine for the task
        """
        mode = task.mode or ""
        instructions = task.instructions.lower()

        # Code review tasks → Continue (fast, focused)
        if mode == "code_review" or "review" in instructions:
            return AgentEngine.CONTINUE

        # Documentation tasks → Aider (good at docs)
        if mode == "doc" or "document" in instructions or "readme" in instructions:
            return AgentEngine.AIDER

        # Test generation → Codex (specialized)
        if mode == "test" or "test" in instructions:
            return AgentEngine.CODEX

        # Refactoring → Aider (best at multi-file)
        if mode == "refactor" or "refactor" in instructions:
            return AgentEngine.AIDER

        # Default to Aider (most versatile)
        return AgentEngine.AIDER

    async def _execute_aider(self, task: AgentTask) -> dict[str, Any]:
        """
        Execute task using Aider.

        Args:
            task: Task to execute

        Returns:
            Execution result
        """
        # Build Aider command
        cmd = [
            "python",
            "-m",
            "aider.main",
            "--model",
            self.default_model,
            "--yes",  # Auto-approve changes
            "--no-git",  # Don't auto-commit
            "--message",
            task.instructions,
        ]

        # Add file if specified
        if task.file:
            cmd.append(task.file)

        # SECURITY: Validate repo_path is within allowed workspace
        from pathlib import Path

        workspace_root = Path(os.getenv("WORKSPACE_ROOT") or Path.cwd()).resolve()
        repo_path = Path(task.repo_path).resolve()

        try:
            repo_path.relative_to(workspace_root)
        except ValueError:
            raise ValueError(
                f"Access denied: repo path '{task.repo_path}' is outside "
                f"allowed workspace root '{workspace_root}'"
            )

        # SECURITY: Validate Ollama URL
        from urllib.parse import urlparse

        parsed_url = urlparse(self.ollama_url)

        if parsed_url.scheme not in ["http", "https"]:
            raise ValueError(
                f"Invalid Ollama URL scheme: {parsed_url.scheme}. Must be http or https."
            )

        if not parsed_url.netloc:
            raise ValueError("Ollama URL must include a host")

        # Optional: Whitelist allowed hosts
        allowed_hosts = os.getenv("ALLOWED_OLLAMA_HOSTS", "localhost,127.0.0.1").split(",")
        if parsed_url.hostname not in allowed_hosts:
            raise ValueError(
                f"Ollama host {parsed_url.hostname} not in allowed list: {allowed_hosts}"
            )

        # Execute Aider
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(repo_path),  # Use validated path
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "OLLAMA_API_BASE": self.ollama_url},
        )

        # Capture output
        stdout, stderr = await process.communicate()

        # Parse output
        output_text = stdout.decode()
        error_text = stderr.decode()

        task.output.append(output_text)
        if error_text:
            task.output.append(f"STDERR: {error_text}")

        # Check exit code
        if process.returncode != 0:
            raise Exception(f"Aider failed with code {process.returncode}: {error_text}")

        # Parse result
        files_modified = self._parse_aider_output(output_text)

        return {
            "engine": "aider",
            "files_modified": files_modified,
            "summary": self._summarize_output(output_text),
            "exit_code": process.returncode,
        }

    async def _execute_continue(self, task: AgentTask) -> dict[str, Any]:
        """
        Execute task using Continue.

        Uses the deep Continue integration bridge for chat-based tasks.

        Args:
            task: Task to execute

        Returns:
            Execution result
        """
        from .continue_ext import (
            ChatMessage,
            ChatRequest,
            MessageRole,
            create_continue_bridge,
        )

        try:
            # Create Continue bridge
            bridge = create_continue_bridge(workspace_root=task.repo_path)

            # Build chat request
            chat_request = ChatRequest(
                messages=[
                    ChatMessage(
                        role=MessageRole.USER,
                        content=task.instructions,
                    )
                ],
                workspace_root=task.repo_path,
                active_file=task.file,
            )

            # Collect response
            response_chunks = []
            async for response in bridge.handle_chat(chat_request):
                if response.content:
                    response_chunks.append(response.content)
                    task.output.append(response.content)

            full_response = "".join(response_chunks)

            return {
                "engine": "continue",
                "files_modified": [],
                "summary": self._summarize_output(full_response),
                "response": full_response,
                "stats": bridge.get_stats(),
            }

        except ImportError as e:
            logger.warning(f"Continue module not available: {e}")
            return {
                "engine": "continue",
                "files_modified": [],
                "summary": f"Continue module not available: {e}",
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"Continue execution failed: {e}")
            raise

    async def _execute_codex(self, task: AgentTask) -> dict[str, Any]:
        """
        Execute task using Codex-like functionality.

        Since OpenAI Codex is cloud-only and deprecated, this routes to
        our local Aider bridge which provides similar code editing
        capabilities using local models (Ollama).

        Args:
            task: Task to execute

        Returns:
            Execution result
        """
        from .aider import AiderConfig, create_aider_bridge

        try:
            # Create Aider bridge as local Codex alternative
            config = AiderConfig(
                workspace_root=task.repo_path,
                model=self.default_model,
                auto_commit=False,
            )
            bridge = create_aider_bridge(config)

            # Build file list
            files = [task.file] if task.file else None

            # Execute via Aider (local Codex-like behavior)
            response = await bridge.execute_edit(
                instruction=task.instructions,
                files=files,
            )

            # Collect output
            task.output.append(response.message or "")

            return {
                "engine": "codex-local",
                "files_modified": response.files_modified,
                "summary": response.message or "Edit completed",
                "edits": [
                    {"file": e.file_path, "type": e.edit_type.value}
                    for e in response.edits
                ],
                "note": "Using local Aider bridge (Codex API is cloud-only)",
            }

        except ImportError as e:
            logger.warning(f"Aider module not available for Codex fallback: {e}")
            return {
                "engine": "codex",
                "files_modified": [],
                "summary": f"Codex fallback (Aider) not available: {e}",
                "error": str(e),
                "note": "OpenAI Codex requires cloud API. Install Aider for local alternative.",
            }
        except Exception as e:
            logger.error(f"Codex/Aider execution failed: {e}")
            raise

    def _parse_aider_output(self, output: str) -> list[str]:
        """
        Parse Aider output to extract modified files.

        Args:
            output: Aider stdout

        Returns:
            List of modified file paths
        """
        files = []
        for line in output.splitlines():
            # Aider typically shows "Applied edit to <file>"
            if "Applied edit to" in line or "Modified" in line:
                parts = line.split()
                if len(parts) > 3:
                    files.append(parts[-1])

        return files

    def _summarize_output(self, output: str, max_lines: int = 10) -> str:
        """
        Summarize agent output.

        Args:
            output: Full output text
            max_lines: Maximum lines to include

        Returns:
            Summarized output
        """
        lines = output.splitlines()
        if len(lines) <= max_lines:
            return output

        # Take first and last few lines
        half = max_lines // 2
        summary_lines = lines[:half] + ["...(truncated)..."] + lines[-half:]
        return "\n".join(summary_lines)

    def get_task(self, task_id: str) -> AgentTask | None:
        """
        Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task or None if not found
        """
        return self.tasks.get(task_id)

    def list_tasks(self, status: TaskStatus | None = None) -> list[AgentTask]:
        """
        List all tasks, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of tasks
        """
        tasks = list(self.tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        # Sort by created_at (newest first)
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        return tasks

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a queued or running task.

        Args:
            task_id: Task ID

        Returns:
            True if cancelled, False if not found or already completed
        """
        task = self.tasks.get(task_id)

        if not task:
            return False

        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False

        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now(timezone.utc).isoformat()
        task.error = "Task cancelled by user"

        return True


# Global agent executor instance
_executor: AgentExecutor | None = None


def get_agent_executor() -> AgentExecutor:
    """Get or create the global agent executor instance"""
    global _executor
    if _executor is None:
        _executor = AgentExecutor()
    return _executor
