"""
Aider Configuration

Provides a typed configuration class for Aider integration.
Replaces hardcoded CLI args with a configurable, validatable structure.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class EditFormat(Enum):
    """
    Aider edit formats.

    DIFF: Git-style unified diff (default, most reliable)
    WHOLE: Send entire file content (simpler but uses more tokens)
    UDIFF: Unified diff with context (alternative to DIFF)
    """

    DIFF = "diff"
    WHOLE = "whole"
    UDIFF = "udiff"


class AiderModel(Enum):
    """
    Common Ollama models for Aider.

    These are models known to work well with Aider's editing workflow.
    """

    QWEN_CODER_3B = "qwen2.5-coder:3b"
    QWEN_CODER_7B = "qwen2.5-coder:7b"
    QWEN_CODER_14B = "qwen2.5-coder:14b"
    CODELLAMA_7B = "codellama:7b"
    CODELLAMA_13B = "codellama:13b"
    DEEPSEEK_CODER = "deepseek-coder:6.7b"
    STARCODER2 = "starcoder2:7b"


@dataclass
class AiderConfig:
    """
    Configuration for Aider execution.

    Encapsulates all Aider CLI options in a type-safe structure.
    Supports environment variable overrides.
    """

    # Model configuration
    model: str = "qwen2.5-coder:3b"
    ollama_url: str = "http://localhost:11434"

    # Git behavior
    auto_commits: bool = False  # Don't auto-commit changes
    git_enabled: bool = False  # Don't use git at all (--no-git)

    # Edit behavior
    edit_format: EditFormat = EditFormat.DIFF
    yes_always: bool = True  # Auto-approve changes (--yes)

    # Context options
    map_tokens: int = 1024  # Tokens for repository map
    max_chat_history_tokens: int = 2048  # Context window for chat

    # File handling
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(
        default_factory=lambda: [
            "*.pyc",
            "__pycache__",
            "node_modules",
            ".git",
            "*.lock",
            "dist",
            "build",
        ]
    )

    # Safety options
    allowed_commands: list[str] = field(
        default_factory=lambda: [
            "python",
            "pytest",
            "npm",
            "npx",
            "node",
            "go",
            "cargo",
        ]
    )

    # Workspace restrictions
    workspace_root: Path | None = None
    allowed_ollama_hosts: list[str] = field(
        default_factory=lambda: ["localhost", "127.0.0.1"]
    )

    def __post_init__(self):
        """Validate configuration after initialization"""
        self._validate_ollama_url()
        if self.workspace_root:
            self.workspace_root = Path(self.workspace_root).resolve()

    def _validate_ollama_url(self) -> None:
        """Validate Ollama URL format and host"""
        parsed = urlparse(self.ollama_url)

        if parsed.scheme not in ["http", "https"]:
            raise ValueError(
                f"Invalid Ollama URL scheme: {parsed.scheme}. Must be http or https."
            )

        if not parsed.netloc:
            raise ValueError("Ollama URL must include a host")

        if parsed.hostname not in self.allowed_ollama_hosts:
            raise ValueError(
                f"Ollama host {parsed.hostname} not in allowed list: "
                f"{self.allowed_ollama_hosts}"
            )

    def validate_repo_path(self, repo_path: str | Path) -> Path:
        """
        Validate that a repository path is within allowed workspace.

        Args:
            repo_path: Path to validate

        Returns:
            Resolved, validated Path

        Raises:
            ValueError: If path is outside workspace root
        """
        if self.workspace_root is None:
            # If no workspace root set, use CWD
            workspace = Path.cwd().resolve()
        else:
            workspace = self.workspace_root

        resolved_path = Path(repo_path).resolve()

        try:
            resolved_path.relative_to(workspace)
        except ValueError:
            raise ValueError(
                f"Access denied: repo path '{repo_path}' is outside "
                f"allowed workspace root '{workspace}'"
            )

        return resolved_path

    def to_cli_args(self) -> list[str]:
        """
        Convert configuration to Aider CLI arguments.

        Returns:
            List of CLI arguments for subprocess execution
        """
        args = []

        # Model
        args.extend(["--model", self.model])

        # Git options
        if not self.git_enabled:
            args.append("--no-git")
        if not self.auto_commits:
            args.append("--no-auto-commits")

        # Edit format
        args.extend(["--edit-format", self.edit_format.value])

        # Auto-approve
        if self.yes_always:
            args.append("--yes")

        # Context options
        args.extend(["--map-tokens", str(self.map_tokens)])
        args.extend(["--max-chat-history-tokens", str(self.max_chat_history_tokens)])

        return args

    def to_env_dict(self) -> dict[str, str]:
        """
        Get environment variables for Aider execution.

        Returns:
            Dict of environment variable overrides
        """
        return {
            "OLLAMA_API_BASE": self.ollama_url,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize configuration for logging/debugging"""
        return {
            "model": self.model,
            "ollama_url": self.ollama_url,
            "auto_commits": self.auto_commits,
            "git_enabled": self.git_enabled,
            "edit_format": self.edit_format.value,
            "yes_always": self.yes_always,
            "map_tokens": self.map_tokens,
            "workspace_root": str(self.workspace_root) if self.workspace_root else None,
        }

    @classmethod
    def from_env(cls) -> "AiderConfig":
        """
        Create configuration from environment variables.

        Environment variables:
            - DEFAULT_MODEL: Ollama model name
            - OLLAMA_BASE_URL: Ollama API URL
            - WORKSPACE_ROOT: Root directory for workspace
            - ALLOWED_OLLAMA_HOSTS: Comma-separated list of allowed hosts
            - AIDER_AUTO_COMMITS: Set to "true" to enable auto-commits
            - AIDER_GIT_ENABLED: Set to "true" to enable git integration
            - AIDER_EDIT_FORMAT: Edit format (diff, whole, udiff)
        """
        allowed_hosts = os.getenv("ALLOWED_OLLAMA_HOSTS", "localhost,127.0.0.1")
        workspace = os.getenv("WORKSPACE_ROOT") or os.getenv("WORKSPACE_PATH")

        return cls(
            model=os.getenv("DEFAULT_MODEL", "qwen2.5-coder:3b"),
            ollama_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            workspace_root=Path(workspace) if workspace else None,
            allowed_ollama_hosts=allowed_hosts.split(","),
            auto_commits=os.getenv("AIDER_AUTO_COMMITS", "false").lower() == "true",
            git_enabled=os.getenv("AIDER_GIT_ENABLED", "false").lower() == "true",
            edit_format=EditFormat(os.getenv("AIDER_EDIT_FORMAT", "diff")),
        )


# Singleton instance
_default_config: AiderConfig | None = None


def get_aider_config() -> AiderConfig:
    """
    Get the default Aider configuration.

    Creates a singleton instance from environment variables.

    Returns:
        AiderConfig instance
    """
    global _default_config
    if _default_config is None:
        _default_config = AiderConfig.from_env()
    return _default_config


def reset_aider_config() -> None:
    """Reset the singleton configuration (useful for testing)"""
    global _default_config
    _default_config = None
