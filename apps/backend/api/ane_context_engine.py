"""Backward Compatibility Shim - use api.ml.ane instead."""

from api.ml.ane.context_engine import (
    ANEContextEngine,
    get_ane_engine,
    _embed_with_ane,
    _flatten_context,
    _cpu_embed_fallback,
)

__all__ = [
    "ANEContextEngine",
    "get_ane_engine",
    "_embed_with_ane",
    "_flatten_context",
    "_cpu_embed_fallback",
]
