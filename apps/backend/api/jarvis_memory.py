"""Backward Compatibility Shim - use api.jarvis instead."""

from api.jarvis.memory import JarvisMemory

# Re-export types that the original module re-exported
from api.jarvis.memory_models import (
    MemoryType,
    MemoryTemplate,
    SemanticMemory,
    get_default_templates,
)
from api.jarvis.memory_db import (
    get_default_db_path,
    create_connection,
    setup_schema,
    generate_embedding,
    cosine_similarity,
    command_hash,
    error_hash,
)

__all__ = [
    "JarvisMemory",
    "MemoryType",
    "MemoryTemplate",
    "SemanticMemory",
    "get_default_templates",
    "get_default_db_path",
    "create_connection",
    "setup_schema",
    "generate_embedding",
    "cosine_similarity",
    "command_hash",
    "error_hash",
]
