"""Backward Compatibility Shim - use api.jarvis instead."""

from api.jarvis.rag_pipeline import (
    retrieve_context_for_command,
    ingest_paths,
    logger,
)

__all__ = ["retrieve_context_for_command", "ingest_paths", "logger"]
