"""
Continue Extension Integration Module

Provides deep integration with Continue IDE extension.
Bridges MagnetarCode's agent system with Continue's UI.

Usage:
    from api.services.continue_ext import (
        ContinueConfig,
        MagnetarContinueBridge,
        create_continue_bridge,
    )

    # Create bridge with default config
    bridge = create_continue_bridge(workspace_root="/path/to/project")

    # Handle chat request
    async for response in bridge.handle_chat(chat_request):
        print(response.content)

    # Handle autocomplete
    completions = await bridge.handle_autocomplete(autocomplete_request)

Components:
    - Bridge: Abstract interface and concrete implementation
    - Context: Context providers for codebase, files, git, problems
    - Autocomplete: Fast FIM-based code completion
    - Chat: Chat handling with slash command support
    - Config: Configuration management
"""

import logging
from typing import Any, AsyncIterator

from .autocomplete import (
    AutocompleteConfig,
    AutocompleteService,
    SmartAutocompleteService,
    create_autocomplete_service,
)
from .bridge import (
    AutocompleteRequest,
    AutocompleteResult,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ContextItem,
    ContextItemType,
    ContextProvider,
    ContinueBridge,
    ContinueServer,
    MessageRole,
    SlashCommand,
)
from .chat import (
    ChatConfig,
    ChatHandler,
    EditCommand,
    ExplainCommand,
    RefactorCommand,
    TestCommand,
    create_chat_handler,
)
from .config import ContinueConfig, get_continue_config
from .context import (
    ActiveFileContextProvider,
    CodebaseContextProvider,
    ContextProviderRegistry,
    GitHistoryContextProvider,
    ProblemsContextProvider,
    create_default_providers,
)

logger = logging.getLogger(__name__)


class MagnetarContinueBridge(ContinueBridge):
    """
    Concrete implementation of ContinueBridge.

    Integrates all Continue components into a unified interface.
    """

    def __init__(
        self,
        config: ContinueConfig,
        aider_bridge=None,
    ):
        """
        Initialize Magnetar Continue bridge.

        Args:
            config: Continue configuration
            aider_bridge: Optional Aider bridge for edit commands
        """
        self._config = config
        self._aider_bridge = aider_bridge

        # Initialize components
        self._context_registry = create_default_providers(config.workspace_root)

        self._autocomplete_service = create_autocomplete_service(
            model=config.autocomplete_model,
            api_base=config.api_base,
            smart=True,
        )

        self._chat_handler = create_chat_handler(
            config=ChatConfig(
                model=config.chat_model,
                api_base=config.api_base,
                max_tokens=config.chat_max_tokens,
                temperature=config.chat_temperature,
                include_codebase_context=config.chat_include_codebase_context,
            ),
            context_registry=self._context_registry,
            aider_bridge=aider_bridge,
        )

        self._connected = True

    async def handle_chat(
        self,
        request: ChatRequest,
    ) -> AsyncIterator[ChatResponse]:
        """Handle chat request"""
        if not self._config.enable_chat:
            yield ChatResponse(
                content="Chat is disabled",
                role=MessageRole.ASSISTANT,
                is_complete=True,
            )
            return

        async for response in self._chat_handler.handle_chat(request):
            yield response

    async def handle_autocomplete(
        self,
        request: AutocompleteRequest,
    ) -> list[AutocompleteResult]:
        """Handle autocomplete request"""
        if not self._config.enable_autocomplete:
            return []

        return await self._autocomplete_service.get_completions(request)

    def register_context_provider(
        self,
        provider: ContextProvider,
    ) -> None:
        """Register a context provider"""
        self._context_registry.register(provider)

    def register_slash_command(
        self,
        command: SlashCommand,
    ) -> None:
        """Register a slash command"""
        self._chat_handler.register_command(command)

    async def get_context(
        self,
        query: str,
        provider_names: list[str] | None = None,
        workspace_root: str | None = None,
    ) -> list[ContextItem]:
        """Get context from providers"""
        return await self._context_registry.get_context(
            query=query,
            workspace_root=workspace_root or self._config.workspace_root,
            provider_names=provider_names,
        )

    def get_available_models(self) -> list[dict[str, Any]]:
        """Get available models"""
        return [
            {
                "name": self._config.chat_model,
                "provider": "ollama",
                "type": "chat",
            },
            {
                "name": self._config.autocomplete_model,
                "provider": "ollama",
                "type": "autocomplete",
            },
        ]

    def is_connected(self) -> bool:
        """Check if connected"""
        return self._connected

    def get_stats(self) -> dict[str, Any]:
        """Get bridge statistics"""
        return {
            "config": self._config.to_dict(),
            "autocomplete": self._autocomplete_service.get_stats(),
            "context_providers": self._context_registry.list_providers(),
            "slash_commands": self._chat_handler.get_commands(),
        }


def create_continue_bridge(
    workspace_root: str,
    config: ContinueConfig | None = None,
    aider_bridge=None,
) -> MagnetarContinueBridge:
    """
    Create configured Continue bridge.

    Args:
        workspace_root: Workspace directory
        config: Optional configuration (uses defaults if not provided)
        aider_bridge: Optional Aider bridge for edit commands

    Returns:
        Configured MagnetarContinueBridge
    """
    if config is None:
        config = get_continue_config()

    config.workspace_root = workspace_root

    return MagnetarContinueBridge(config, aider_bridge)


__all__ = [
    # Config
    "ContinueConfig",
    "get_continue_config",
    # Bridge interface
    "ContinueBridge",
    "ContinueServer",
    "MagnetarContinueBridge",
    "create_continue_bridge",
    # Types
    "AutocompleteRequest",
    "AutocompleteResult",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ContextItem",
    "ContextItemType",
    "MessageRole",
    # Context providers
    "ContextProvider",
    "ContextProviderRegistry",
    "CodebaseContextProvider",
    "ActiveFileContextProvider",
    "GitHistoryContextProvider",
    "ProblemsContextProvider",
    "create_default_providers",
    # Autocomplete
    "AutocompleteConfig",
    "AutocompleteService",
    "SmartAutocompleteService",
    "create_autocomplete_service",
    # Chat
    "ChatConfig",
    "ChatHandler",
    "SlashCommand",
    "EditCommand",
    "ExplainCommand",
    "RefactorCommand",
    "TestCommand",
    "create_chat_handler",
]
