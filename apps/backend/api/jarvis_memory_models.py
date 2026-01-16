"""Backward Compatibility Shim - use api.jarvis instead."""

from api.jarvis.memory_models import (
    MemoryType,
    MemoryTemplate,
    SemanticMemory,
    get_default_templates,
)

__all__ = ["MemoryType", "MemoryTemplate", "SemanticMemory", "get_default_templates"]
