"""
Continue Extension Bridge

Abstract interface for Continue IDE extension integration.
Enables deep integration with Continue's autocomplete, context, and chat features.

Continue Architecture:
- Core: TypeScript extension running in VS Code/JetBrains
- SDK: Python SDK for custom context providers and tools
- Protocol: JSON-RPC over stdio or HTTP for communication

This bridge provides a Python-native interface that can:
1. Act as a Continue context provider (inject agent knowledge)
2. Handle Continue chat requests (route to MagnetarCode agents)
3. Provide autocomplete suggestions (using local models)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator


class MessageRole(Enum):
    """Roles in a Continue conversation"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ContextItemType(Enum):
    """Types of context items Continue can use"""

    FILE = "file"
    CODE = "code"
    TERMINAL = "terminal"
    DOCS = "docs"
    WEB = "web"
    DIFF = "diff"
    PROBLEM = "problem"  # Linter/compiler errors
    CUSTOM = "custom"


@dataclass
class ContextItem:
    """
    A piece of context for Continue prompts.

    Represents code, documentation, or other relevant information
    that helps the model understand the current task.
    """

    name: str
    content: str
    item_type: ContextItemType = ContextItemType.CODE
    description: str = ""

    # Source information
    uri: str | None = None  # file:// or https://
    line_start: int | None = None
    line_end: int | None = None

    # Metadata
    language: str | None = None
    relevance_score: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "content": self.content[:500] + "..." if len(self.content) > 500 else self.content,
            "type": self.item_type.value,
            "description": self.description,
            "uri": self.uri,
            "language": self.language,
            "relevance": self.relevance_score,
        }

    @property
    def token_estimate(self) -> int:
        """Rough token count estimate (4 chars per token)"""
        return len(self.content) // 4


@dataclass
class ChatMessage:
    """
    A message in a Continue chat conversation.

    Mirrors Continue's ChatMessage type.
    """

    role: MessageRole
    content: str

    # Tool use
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_id: str | None = None

    # Context attached to this message
    context_items: list[ContextItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "content": self.content,
            "toolCalls": self.tool_calls if self.tool_calls else None,
            "contextItems": [c.to_dict() for c in self.context_items],
        }


@dataclass
class AutocompleteRequest:
    """Request for autocomplete suggestions"""

    # Current file context
    file_path: str
    file_content: str
    cursor_line: int
    cursor_column: int

    # Surrounding context
    prefix: str  # Text before cursor
    suffix: str  # Text after cursor

    # Optional hints
    language: str | None = None
    trigger_kind: str = "automatic"  # "automatic" or "manual"

    # Workspace info
    workspace_root: str | None = None
    open_files: list[str] = field(default_factory=list)


@dataclass
class AutocompleteResult:
    """A single autocomplete suggestion"""

    text: str  # The completion text
    display_text: str | None = None  # How to display in UI

    # Range to replace
    range_start_line: int = 0
    range_start_col: int = 0
    range_end_line: int = 0
    range_end_col: int = 0

    # Metadata
    confidence: float = 0.8
    model: str = ""
    latency_ms: int = 0


@dataclass
class ChatRequest:
    """Request for chat completion"""

    messages: list[ChatMessage]
    context_items: list[ContextItem] = field(default_factory=list)

    # Model preferences
    model: str | None = None
    max_tokens: int = 2048
    temperature: float = 0.7

    # Streaming
    stream: bool = True

    # Workspace context
    workspace_root: str | None = None
    active_file: str | None = None


@dataclass
class ChatResponse:
    """Response from chat completion"""

    content: str
    role: MessageRole = MessageRole.ASSISTANT

    # Tool use
    tool_calls: list[dict[str, Any]] = field(default_factory=list)

    # Metadata
    model: str = ""
    tokens_used: int = 0
    latency_ms: int = 0

    # For streaming
    is_complete: bool = True


class ContextProvider(ABC):
    """
    Abstract context provider for Continue.

    Context providers inject relevant information into prompts.
    Examples: codebase search, documentation, git history.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider name (e.g., 'magnetar-codebase')"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description"""
        pass

    @abstractmethod
    async def get_context(
        self,
        query: str,
        full_input: str,
        workspace_root: str | None = None,
        selected_code: str | None = None,
    ) -> list[ContextItem]:
        """
        Get context items for a query.

        Args:
            query: The user's query/input
            full_input: Full conversation input
            workspace_root: Workspace directory
            selected_code: Currently selected code

        Returns:
            List of context items to inject
        """
        pass

    def get_config(self) -> dict[str, Any]:
        """Get provider configuration for Continue"""
        return {
            "name": self.name,
            "description": self.description,
        }


class SlashCommand(ABC):
    """
    Abstract slash command for Continue.

    Slash commands are custom actions like /edit, /comment, /test.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Command name without slash (e.g., 'edit')"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Command description"""
        pass

    @abstractmethod
    async def run(
        self,
        input_text: str,
        context_items: list[ContextItem],
        workspace_root: str | None = None,
    ) -> AsyncIterator[str]:
        """
        Execute the command.

        Args:
            input_text: User input after command
            context_items: Attached context
            workspace_root: Workspace directory

        Yields:
            Response chunks
        """
        pass

    def get_config(self) -> dict[str, Any]:
        """Get command configuration"""
        return {
            "name": self.name,
            "description": self.description,
        }


class ContinueBridge(ABC):
    """
    Abstract interface for Continue integration.

    Implementations can:
    - Connect to Continue's extension API
    - Serve as a Continue-compatible backend
    - Bridge between MagnetarCode agents and Continue UI
    """

    @abstractmethod
    async def handle_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatResponse]:
        """
        Handle a chat request from Continue.

        Args:
            request: Chat request with messages and context

        Yields:
            Response chunks (for streaming)
        """
        pass

    @abstractmethod
    async def handle_autocomplete(
        self,
        request: AutocompleteRequest,
    ) -> list[AutocompleteResult]:
        """
        Handle an autocomplete request.

        Args:
            request: Autocomplete request with file context

        Returns:
            List of completion suggestions
        """
        pass

    @abstractmethod
    def register_context_provider(
        self,
        provider: ContextProvider,
    ) -> None:
        """Register a context provider"""
        pass

    @abstractmethod
    def register_slash_command(
        self,
        command: SlashCommand,
    ) -> None:
        """Register a slash command"""
        pass

    @abstractmethod
    async def get_context(
        self,
        query: str,
        provider_names: list[str] | None = None,
        workspace_root: str | None = None,
    ) -> list[ContextItem]:
        """
        Get context from registered providers.

        Args:
            query: The query to get context for
            provider_names: Specific providers to use
            workspace_root: Workspace directory

        Returns:
            Aggregated context items
        """
        pass

    @abstractmethod
    def get_available_models(self) -> list[dict[str, Any]]:
        """Get list of available models"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to Continue extension"""
        pass


class ContinueServer(ABC):
    """
    Abstract server for Continue protocol.

    Can serve as a backend for Continue's IDE extension,
    handling JSON-RPC requests over stdio or HTTP.
    """

    @abstractmethod
    async def start(self, host: str = "localhost", port: int = 8080) -> None:
        """Start the server"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the server"""
        pass

    @abstractmethod
    def set_bridge(self, bridge: ContinueBridge) -> None:
        """Set the bridge implementation"""
        pass

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Check if server is running"""
        pass
