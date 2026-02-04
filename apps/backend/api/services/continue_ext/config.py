"""
Continue Extension Configuration

Configuration management for Continue integration.
"""

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContinueConfig:
    """
    Master configuration for Continue integration.

    Consolidates all settings for the Continue extension bridge.
    """

    # Workspace
    workspace_root: str = ""

    # Model settings
    chat_model: str = "qwen2.5-coder:7b"
    autocomplete_model: str = "qwen2.5-coder:1.5b"
    api_base: str = "http://localhost:11434"

    # Feature toggles
    enable_autocomplete: bool = True
    enable_chat: bool = True
    enable_context_providers: bool = True

    # Autocomplete settings
    autocomplete_timeout_ms: int = 500
    autocomplete_max_tokens: int = 64

    # Chat settings
    chat_max_tokens: int = 2048
    chat_temperature: float = 0.7
    chat_include_codebase_context: bool = True

    # Context settings
    max_context_items: int = 10
    max_context_tokens: int = 4000

    # Server settings (if running as standalone server)
    server_host: str = "localhost"
    server_port: int = 8765

    # Logging
    log_requests: bool = False
    log_completions: bool = False

    @classmethod
    def from_env(cls) -> "ContinueConfig":
        """Create config from environment variables"""
        return cls(
            workspace_root=os.getenv("MAGNETAR_WORKSPACE", ""),
            chat_model=os.getenv("MAGNETAR_CHAT_MODEL", "qwen2.5-coder:7b"),
            autocomplete_model=os.getenv("MAGNETAR_AUTOCOMPLETE_MODEL", "qwen2.5-coder:1.5b"),
            api_base=os.getenv("OLLAMA_API_BASE", "http://localhost:11434"),
            enable_autocomplete=os.getenv("MAGNETAR_AUTOCOMPLETE", "true").lower() == "true",
            enable_chat=os.getenv("MAGNETAR_CHAT", "true").lower() == "true",
            autocomplete_timeout_ms=int(os.getenv("MAGNETAR_AUTOCOMPLETE_TIMEOUT", "500")),
            chat_max_tokens=int(os.getenv("MAGNETAR_CHAT_MAX_TOKENS", "2048")),
            server_port=int(os.getenv("MAGNETAR_CONTINUE_PORT", "8765")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "workspace_root": self.workspace_root,
            "chat_model": self.chat_model,
            "autocomplete_model": self.autocomplete_model,
            "api_base": self.api_base,
            "enable_autocomplete": self.enable_autocomplete,
            "enable_chat": self.enable_chat,
            "autocomplete_timeout_ms": self.autocomplete_timeout_ms,
            "chat_max_tokens": self.chat_max_tokens,
            "server_port": self.server_port,
        }


def get_continue_config() -> ContinueConfig:
    """Get Continue configuration from environment"""
    return ContinueConfig.from_env()
