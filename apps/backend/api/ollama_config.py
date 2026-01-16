"""
Compatibility Shim for Ollama Configuration

The implementation now lives in the `api.llm` package:
- api.llm.ollama: OllamaConfig, OllamaConfigManager

This shim maintains backward compatibility.
"""

from api.llm.ollama import (
    OllamaConfig,
    OllamaConfigManager,
    get_ollama_config,
)

__all__ = [
    "OllamaConfig",
    "OllamaConfigManager",
    "get_ollama_config",
]
