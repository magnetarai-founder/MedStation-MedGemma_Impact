#!/usr/bin/env python3
"""
Async Tool Executor

Provides async wrapper around synchronous tool execution for the agentic loop.
Supports:
- Parallel tool execution
- Streaming output for long-running tools
- Progress callbacks
- Retry with exponential backoff
- Tool result caching
"""

import asyncio
import hashlib
import json
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from api.utils.structured_logging import get_logger

from .custom_tools import CustomToolRegistry, get_custom_tool_registry
from .tools import Tool, ToolRegistry

logger = get_logger(__name__)


@dataclass
class ToolExecutionResult:
    """Result from tool execution."""

    tool_name: str
    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "cached": self.cached,
        }


@dataclass
class ToolExecutionContext:
    """Context for tool execution."""

    workspace_root: Path
    user_id: str | None = None
    session_id: str | None = None
    max_retries: int = 3
    timeout_seconds: float = 60.0
    enable_caching: bool = True


class AsyncToolExecutor:
    """
    Async wrapper for tool execution in the agentic loop.

    Features:
    - Async execution of sync tools via thread pool
    - Parallel multi-tool execution
    - Simple in-memory result caching
    - Retry with exponential backoff
    - Progress streaming for long-running tools
    """

    def __init__(
        self,
        workspace_root: str | Path | None = None,
        enable_custom_tools: bool = True,
    ):
        """
        Initialize async tool executor.

        Args:
            workspace_root: Root directory for file operations
            enable_custom_tools: Whether to include custom tools
        """
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()

        # Initialize tool registries
        self._tool_registry = ToolRegistry(str(self.workspace_root))
        self._custom_registry: CustomToolRegistry | None = None

        if enable_custom_tools:
            self._custom_registry = get_custom_tool_registry()

        # Simple in-memory cache (could be extended with Redis/disk)
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._cache_ttl_seconds = 300  # 5 minute cache

        # Progress callbacks
        self._progress_callbacks: list[Callable[[str, float, str], None]] = []

    def register_progress_callback(
        self, callback: Callable[[str, float, str], None]
    ) -> None:
        """
        Register a callback for progress updates.

        Callback receives: (tool_name, progress 0.0-1.0, message)
        """
        self._progress_callbacks.append(callback)

    async def _notify_progress(
        self, tool_name: str, progress: float, message: str
    ) -> None:
        """Notify all progress callbacks."""
        for callback in self._progress_callbacks:
            try:
                callback(tool_name, progress, message)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

    def get_tool(self, tool_name: str) -> Tool | None:
        """Get a tool by name (built-in or custom)."""
        # Check built-in tools first
        tool = self._tool_registry.get(tool_name)
        if tool:
            return tool

        # Check custom tools
        if self._custom_registry:
            custom = self._custom_registry.get_tool(tool_name)
            if custom:
                # Wrap custom tool as Tool
                return Tool(
                    name=custom.name,
                    description=custom.description,
                    parameters=custom.parameters,
                    function=lambda **kwargs: self._custom_registry.execute_tool(
                        custom.name, **kwargs
                    ),
                    category="custom",
                )

        return None

    def list_tools(self) -> list[dict[str, Any]]:
        """List all available tools with schemas."""
        tools = []

        # Built-in tools
        for tool in self._tool_registry.list_tools():
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "category": tool.category,
                "schema": tool.to_schema(),
                "type": "builtin",
            })

        # Custom tools
        if self._custom_registry:
            for custom in self._custom_registry.list_tools():
                tools.append({
                    "name": custom.name,
                    "description": custom.description,
                    "category": custom.category,
                    "schema": custom.to_dict(),
                    "type": "custom",
                })

        return tools

    def _cache_key(self, tool_name: str, params: dict[str, Any]) -> str:
        """Generate cache key for tool execution."""
        params_json = json.dumps(params, sort_keys=True)
        return hashlib.md5(f"{tool_name}:{params_json}".encode()).hexdigest()

    def _check_cache(self, cache_key: str) -> tuple[bool, Any]:
        """Check if result is cached and not expired."""
        if cache_key not in self._cache:
            return False, None

        result, cached_at = self._cache[cache_key]
        age = (datetime.utcnow() - cached_at).total_seconds()

        if age > self._cache_ttl_seconds:
            del self._cache[cache_key]
            return False, None

        return True, result

    def _set_cache(self, cache_key: str, result: Any) -> None:
        """Cache a result."""
        self._cache[cache_key] = (result, datetime.utcnow())

        # Simple cache cleanup - remove oldest if too large
        if len(self._cache) > 1000:
            # Remove oldest 10%
            sorted_keys = sorted(
                self._cache.keys(), key=lambda k: self._cache[k][1]
            )
            for key in sorted_keys[: len(sorted_keys) // 10]:
                del self._cache[key]

    async def execute(
        self,
        tool_name: str,
        params: dict[str, Any] | None = None,
        context: ToolExecutionContext | None = None,
    ) -> ToolExecutionResult:
        """
        Execute a tool asynchronously.

        Args:
            tool_name: Name of tool to execute
            params: Tool parameters
            context: Execution context (optional)

        Returns:
            ToolExecutionResult with output or error
        """
        params = params or {}
        context = context or ToolExecutionContext(workspace_root=self.workspace_root)
        start_time = datetime.utcnow()

        # Check cache for read-only tools
        cache_key = self._cache_key(tool_name, params)
        read_only_tools = {"read_file", "list_files", "grep_code", "git_status"}

        if context.enable_caching and tool_name in read_only_tools:
            cached, result = self._check_cache(cache_key)
            if cached:
                logger.debug(f"Cache hit for tool: {tool_name}")
                return ToolExecutionResult(
                    tool_name=tool_name,
                    success=True,
                    output=result,
                    cached=True,
                    duration_ms=0.0,
                )

        # Get the tool
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool not found: {tool_name}",
            )

        # Notify progress start
        await self._notify_progress(tool_name, 0.0, "Starting execution")

        # Execute with retry
        last_error = None
        for attempt in range(context.max_retries):
            try:
                # Run sync tool in thread pool
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: tool.function(**params)),
                    timeout=context.timeout_seconds,
                )

                # Notify progress complete
                await self._notify_progress(tool_name, 1.0, "Execution complete")

                # Calculate duration
                duration = (datetime.utcnow() - start_time).total_seconds() * 1000

                # Cache result for read-only tools
                if context.enable_caching and tool_name in read_only_tools:
                    self._set_cache(cache_key, result)

                return ToolExecutionResult(
                    tool_name=tool_name,
                    success=True,
                    output=result,
                    duration_ms=duration,
                    metadata={"attempt": attempt + 1},
                )

            except asyncio.TimeoutError:
                last_error = f"Tool execution timed out after {context.timeout_seconds}s"
                logger.warning(f"Tool {tool_name} timeout (attempt {attempt + 1})")

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Tool {tool_name} failed (attempt {attempt + 1}): {e}")

                # Exponential backoff
                if attempt < context.max_retries - 1:
                    await asyncio.sleep(2**attempt * 0.5)

        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        return ToolExecutionResult(
            tool_name=tool_name,
            success=False,
            error=last_error,
            duration_ms=duration,
            metadata={"attempts": context.max_retries},
        )

    async def execute_parallel(
        self,
        tool_calls: list[tuple[str, dict[str, Any]]],
        context: ToolExecutionContext | None = None,
    ) -> list[ToolExecutionResult]:
        """
        Execute multiple tools in parallel.

        Args:
            tool_calls: List of (tool_name, params) tuples
            context: Execution context

        Returns:
            List of results in same order as input
        """
        tasks = [
            self.execute(tool_name, params, context)
            for tool_name, params in tool_calls
        ]

        return await asyncio.gather(*tasks)

    async def execute_streaming(
        self,
        tool_name: str,
        params: dict[str, Any] | None = None,
        context: ToolExecutionContext | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Execute a tool with streaming output.

        Useful for long-running tools that produce incremental output.

        Args:
            tool_name: Name of tool to execute
            params: Tool parameters
            context: Execution context

        Yields:
            Progress events and final result
        """
        yield {"type": "start", "tool_name": tool_name, "params": params}

        result = await self.execute(tool_name, params, context)

        if result.success:
            yield {
                "type": "output",
                "tool_name": tool_name,
                "output": result.output,
                "duration_ms": result.duration_ms,
            }
        else:
            yield {
                "type": "error",
                "tool_name": tool_name,
                "error": result.error,
            }

        yield {"type": "complete", "tool_name": tool_name, "result": result.to_dict()}


class ToolPipeline:
    """
    Chain multiple tools together in a pipeline.

    Example:
        pipeline = ToolPipeline(executor)
        pipeline.add("read_file", {"file_path": "main.py"})
        pipeline.add("grep_code", {"pattern": "def", "file_pattern": "*.py"})
        results = await pipeline.run()
    """

    def __init__(self, executor: AsyncToolExecutor):
        """
        Initialize pipeline.

        Args:
            executor: Tool executor to use
        """
        self.executor = executor
        self.steps: list[tuple[str, dict[str, Any], Callable | None]] = []

    def add(
        self,
        tool_name: str,
        params: dict[str, Any] | None = None,
        transform: Callable[[Any], dict[str, Any]] | None = None,
    ) -> "ToolPipeline":
        """
        Add a step to the pipeline.

        Args:
            tool_name: Tool to execute
            params: Static parameters
            transform: Optional function to transform output for next step

        Returns:
            Self for chaining
        """
        self.steps.append((tool_name, params or {}, transform))
        return self

    async def run(
        self, initial_params: dict[str, Any] | None = None
    ) -> list[ToolExecutionResult]:
        """
        Run the pipeline.

        Args:
            initial_params: Initial parameters passed to first step

        Returns:
            List of results from each step
        """
        results = []
        current_params = initial_params or {}

        for tool_name, static_params, transform in self.steps:
            # Merge static params with dynamic params from previous step
            params = {**static_params, **current_params}

            result = await self.executor.execute(tool_name, params)
            results.append(result)

            if not result.success:
                # Stop pipeline on failure
                break

            # Transform output for next step
            if transform and result.output:
                current_params = transform(result.output)
            else:
                current_params = {}

        return results


# Global instance
_async_executor: AsyncToolExecutor | None = None


def get_async_tool_executor(
    workspace_root: str | Path | None = None,
) -> AsyncToolExecutor:
    """Get or create global async tool executor."""
    global _async_executor

    if _async_executor is None or (
        workspace_root and Path(workspace_root) != _async_executor.workspace_root
    ):
        _async_executor = AsyncToolExecutor(workspace_root)

    return _async_executor
