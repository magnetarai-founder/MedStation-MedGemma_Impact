"""Backward Compatibility Shim - use api.jarvis instead."""

from api.jarvis.memory_db import (
    get_default_db_path,
    create_connection,
    setup_schema,
    generate_embedding,
    cosine_similarity,
    command_hash,
    error_hash,
    logger,
)

__all__ = [
    "get_default_db_path",
    "create_connection",
    "setup_schema",
    "generate_embedding",
    "cosine_similarity",
    "command_hash",
    "error_hash",
    "logger",
]
