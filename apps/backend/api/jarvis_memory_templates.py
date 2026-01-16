"""Backward Compatibility Shim - use api.jarvis instead."""

from api.jarvis.memory_templates import (
    MemoryType,
    MemoryTemplate,
    SemanticMemory,
    cosine_similarity,
    generate_hash_embedding,
    get_default_templates,
    get_template_by_id,
)

__all__ = [
    "MemoryType",
    "MemoryTemplate",
    "SemanticMemory",
    "cosine_similarity",
    "generate_hash_embedding",
    "get_default_templates",
    "get_template_by_id",
]
