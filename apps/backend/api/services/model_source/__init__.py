"""
Model Source Abstraction Layer

Provides unified types for managing models from multiple sources:
- Ollama (local inference server)
- HuggingFace Hub (GGUF downloads for llama.cpp)
"""

from .types import (
    ModelSourceType,
    UnifiedModel,
    ModelCapability,
    HardwareRequirements,
)

__all__ = [
    "ModelSourceType",
    "UnifiedModel",
    "ModelCapability",
    "HardwareRequirements",
]
