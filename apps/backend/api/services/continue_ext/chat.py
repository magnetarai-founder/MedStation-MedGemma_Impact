"""
Continue Chat Handler

Handles Continue chat requests and routes to MagnetarCode agents.
Bridges Continue's chat UI with the agent orchestration system.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator

from .bridge import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ContextItem,
    MessageRole,
    SlashCommand,
)
from .context import ContextProviderRegistry

logger = logging.getLogger(__name__)


@dataclass
class ChatConfig:
    """Configuration for chat service"""

    # Model settings
    model: str = "qwen2.5-coder:7b"
    api_base: str = "http://localhost:11434"

    # Generation settings
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9

    # Context settings
    max_context_tokens: int = 4000
    include_codebase_context: bool = True

    # Streaming
    stream: bool = True


class ChatHandler:
    """
    Handles Continue chat requests.

    Features:
    - Routes to appropriate agent or model
    - Manages conversation context
    - Supports slash commands
    - Integrates with context providers
    """

    def __init__(
        self,
        config: ChatConfig | None = None,
        context_registry: ContextProviderRegistry | None = None,
    ):
        """
        Initialize chat handler.

        Args:
            config: Chat configuration
            context_registry: Registry of context providers
        """
        self._config = config or ChatConfig()
        self._context_registry = context_registry
        self._slash_commands: dict[str, SlashCommand] = {}
        self._conversation_history: list[ChatMessage] = []

    def register_command(self, command: SlashCommand) -> None:
        """Register a slash command"""
        self._slash_commands[command.name] = command
        logger.info(f"Registered slash command: /{command.name}")

    async def handle_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatResponse]:
        """
        Handle a chat request.

        Routes to slash command handlers or general chat.

        Args:
            request: Chat request with messages and context

        Yields:
            Response chunks (for streaming)
        """
        if not request.messages:
            yield ChatResponse(
                content="No message provided",
                role=MessageRole.ASSISTANT,
            )
            return

        # Get the latest user message
        user_message = request.messages[-1]
        content = user_message.content.strip()

        # Check for slash command
        if content.startswith("/"):
            async for chunk in self._handle_slash_command(content, request):
                yield chunk
            return

        # Regular chat
        async for chunk in self._handle_regular_chat(request):
            yield chunk

    async def _handle_slash_command(
        self,
        content: str,
        request: ChatRequest,
    ) -> AsyncIterator[ChatResponse]:
        """Handle slash command"""
        # Parse command
        parts = content[1:].split(maxsplit=1)
        command_name = parts[0].lower()
        command_input = parts[1] if len(parts) > 1 else ""

        if command_name not in self._slash_commands:
            yield ChatResponse(
                content=f"Unknown command: /{command_name}\n\nAvailable commands:\n"
                + "\n".join(f"  /{name}" for name in self._slash_commands),
                role=MessageRole.ASSISTANT,
                is_complete=True,
            )
            return

        command = self._slash_commands[command_name]

        try:
            async for chunk in command.run(
                input_text=command_input,
                context_items=request.context_items,
                workspace_root=request.workspace_root,
            ):
                yield ChatResponse(
                    content=chunk,
                    role=MessageRole.ASSISTANT,
                    is_complete=False,
                )

            yield ChatResponse(
                content="",
                role=MessageRole.ASSISTANT,
                is_complete=True,
            )

        except Exception as e:
            logger.exception(f"Slash command error: {e}")
            yield ChatResponse(
                content=f"Error executing /{command_name}: {str(e)}",
                role=MessageRole.ASSISTANT,
                is_complete=True,
            )

    async def _handle_regular_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatResponse]:
        """Handle regular chat message"""
        start_time = time.time()

        try:
            # Build context
            context_items = list(request.context_items)

            # Add codebase context if enabled
            if self._config.include_codebase_context and self._context_registry:
                user_message = request.messages[-1].content
                codebase_context = await self._context_registry.get_context(
                    query=user_message,
                    workspace_root=request.workspace_root,
                )
                context_items.extend(codebase_context)

            # Build prompt
            prompt = self._build_prompt(request.messages, context_items)

            # Stream from model
            async for chunk in self._stream_model_response(prompt):
                yield ChatResponse(
                    content=chunk,
                    role=MessageRole.ASSISTANT,
                    model=self._config.model,
                    is_complete=False,
                )

            # Final response
            latency_ms = int((time.time() - start_time) * 1000)
            yield ChatResponse(
                content="",
                role=MessageRole.ASSISTANT,
                model=self._config.model,
                latency_ms=latency_ms,
                is_complete=True,
            )

        except Exception as e:
            logger.exception(f"Chat error: {e}")
            yield ChatResponse(
                content=f"Error: {str(e)}",
                role=MessageRole.ASSISTANT,
                is_complete=True,
            )

    def _build_prompt(
        self,
        messages: list[ChatMessage],
        context_items: list[ContextItem],
    ) -> str:
        """Build prompt with context"""
        parts: list[str] = []

        # System message with context
        system_parts = [
            "You are a helpful AI coding assistant. "
            "You help users write, debug, and understand code."
        ]

        if context_items:
            system_parts.append("\n\nRelevant context:")
            for item in context_items[:10]:  # Limit context items
                system_parts.append(f"\n--- {item.name} ---")
                # Truncate large content
                content = item.content
                if len(content) > 1000:
                    content = content[:1000] + "\n... [truncated]"
                system_parts.append(content)

        parts.append("".join(system_parts))

        # Conversation history
        for msg in messages:
            role_prefix = {
                MessageRole.USER: "User",
                MessageRole.ASSISTANT: "Assistant",
                MessageRole.SYSTEM: "System",
                MessageRole.TOOL: "Tool",
            }.get(msg.role, "User")

            parts.append(f"\n\n{role_prefix}: {msg.content}")

        parts.append("\n\nAssistant:")

        return "".join(parts)

    async def _stream_model_response(
        self,
        prompt: str,
    ) -> AsyncIterator[str]:
        """Stream response from Ollama"""
        import aiohttp

        url = f"{self._config.api_base}/api/generate"

        payload = {
            "model": self._config.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_predict": self._config.max_tokens,
                "temperature": self._config.temperature,
                "top_p": self._config.top_p,
            },
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        yield f"Model error: {response.status}"
                        return

                    async for line in response.content:
                        if not line:
                            continue

                        try:
                            import json
                            data = json.loads(line)
                            chunk = data.get("response", "")
                            if chunk:
                                yield chunk

                            if data.get("done", False):
                                break

                        except (json.JSONDecodeError, KeyError):
                            continue

        except aiohttp.ClientError as e:
            yield f"Connection error: {e}"

    def clear_history(self) -> None:
        """Clear conversation history"""
        self._conversation_history.clear()

    def get_commands(self) -> list[dict[str, str]]:
        """Get registered slash commands"""
        return [
            {"name": cmd.name, "description": cmd.description}
            for cmd in self._slash_commands.values()
        ]


# Built-in slash commands

class EditCommand(SlashCommand):
    """
    /edit - Edit code in the active file.

    Uses Aider for intelligent code editing.
    """

    def __init__(self, aider_bridge=None):
        self._aider_bridge = aider_bridge

    @property
    def name(self) -> str:
        return "edit"

    @property
    def description(self) -> str:
        return "Edit code using AI (e.g., /edit fix the bug in line 42)"

    async def run(
        self,
        input_text: str,
        context_items: list[ContextItem],
        workspace_root: str | None = None,
    ) -> AsyncIterator[str]:
        """Execute edit command"""
        if not input_text:
            yield "Please provide an edit instruction.\n"
            yield "Example: /edit add error handling to the login function"
            return

        # Get files from context
        files = [
            item.uri.replace("file://", "")
            for item in context_items
            if item.uri and item.uri.startswith("file://")
        ]

        if self._aider_bridge:
            try:
                async for chunk in self._aider_bridge.stream_edit(
                    instruction=input_text,
                    files=files,
                ):
                    yield chunk
            except Exception as e:
                yield f"Edit failed: {e}"
        else:
            yield "Edit functionality requires Aider integration.\n"
            yield f"Would edit: {input_text}\n"
            if files:
                yield f"Files: {', '.join(files)}"


class ExplainCommand(SlashCommand):
    """
    /explain - Explain selected code or concept.
    """

    @property
    def name(self) -> str:
        return "explain"

    @property
    def description(self) -> str:
        return "Explain code or a concept"

    async def run(
        self,
        input_text: str,
        context_items: list[ContextItem],
        workspace_root: str | None = None,
    ) -> AsyncIterator[str]:
        """Execute explain command"""
        # Get selected code
        selected_code = None
        for item in context_items:
            if item.name == "Selected Code":
                selected_code = item.content
                break

        if selected_code:
            yield f"Explaining the selected code:\n\n```\n{selected_code[:500]}\n```\n\n"
            yield "This code..."
            # Would stream explanation from model
        elif input_text:
            yield f"Explaining: {input_text}\n\n"
            # Would stream explanation from model
        else:
            yield "Please select code or provide a topic to explain."


class RefactorCommand(SlashCommand):
    """
    /refactor - Refactor selected code.
    """

    def __init__(self, aider_bridge=None):
        self._aider_bridge = aider_bridge

    @property
    def name(self) -> str:
        return "refactor"

    @property
    def description(self) -> str:
        return "Refactor selected code"

    async def run(
        self,
        input_text: str,
        context_items: list[ContextItem],
        workspace_root: str | None = None,
    ) -> AsyncIterator[str]:
        """Execute refactor command"""
        # Get selected code
        selected_code = None
        for item in context_items:
            if item.name == "Selected Code":
                selected_code = item.content
                break

        if not selected_code:
            yield "Please select code to refactor."
            return

        instruction = input_text or "Refactor this code to improve clarity and maintainability"

        yield f"Refactoring with instruction: {instruction}\n\n"

        if self._aider_bridge:
            files = [
                item.uri.replace("file://", "")
                for item in context_items
                if item.uri and item.uri.startswith("file://")
            ]

            try:
                async for chunk in self._aider_bridge.stream_edit(
                    instruction=f"Refactor: {instruction}\n\nCode:\n{selected_code}",
                    files=files,
                ):
                    yield chunk
            except Exception as e:
                yield f"Refactor failed: {e}"
        else:
            yield "Refactoring requires Aider integration."


class TestCommand(SlashCommand):
    """
    /test - Generate tests for selected code.
    """

    @property
    def name(self) -> str:
        return "test"

    @property
    def description(self) -> str:
        return "Generate tests for selected code"

    async def run(
        self,
        input_text: str,
        context_items: list[ContextItem],
        workspace_root: str | None = None,
    ) -> AsyncIterator[str]:
        """Execute test generation command"""
        selected_code = None
        for item in context_items:
            if item.name == "Selected Code":
                selected_code = item.content
                break

        if not selected_code:
            yield "Please select code to generate tests for."
            return

        yield "Generating tests for selected code...\n\n"
        yield "```python\n"
        yield "# Generated test cases\n"
        yield "import pytest\n\n"
        yield "# TODO: Generate actual tests using model\n"
        yield "```"


def create_chat_handler(
    config: ChatConfig | None = None,
    context_registry: ContextProviderRegistry | None = None,
    aider_bridge=None,
) -> ChatHandler:
    """
    Create configured chat handler with default commands.

    Args:
        config: Chat configuration
        context_registry: Context provider registry
        aider_bridge: Aider bridge for edit commands

    Returns:
        Configured chat handler
    """
    handler = ChatHandler(config, context_registry)

    # Register built-in commands
    handler.register_command(EditCommand(aider_bridge))
    handler.register_command(ExplainCommand())
    handler.register_command(RefactorCommand(aider_bridge))
    handler.register_command(TestCommand())

    return handler
