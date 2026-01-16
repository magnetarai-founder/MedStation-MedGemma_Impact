"""Backward Compatibility Shim - use api.docs instead."""

from api.docs.routes import router, logger

# Re-export models for backward compatibility
from api.docs.models import (
    Document,
    DocumentCreate,
    DocumentUpdate,
    SyncRequest,
    SyncResponse,
)

__all__ = [
    "router",
    "logger",
    "Document",
    "DocumentCreate",
    "DocumentUpdate",
    "SyncRequest",
    "SyncResponse",
]
