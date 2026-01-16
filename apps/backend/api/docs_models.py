"""Backward Compatibility Shim - use api.docs instead."""

from api.docs.models import (
    VALID_DOC_TYPES,
    VALID_SECURITY_LEVELS,
    DocumentCreate,
    DocumentUpdate,
    Document,
    SyncRequest,
    SyncResponse,
)

__all__ = [
    "VALID_DOC_TYPES",
    "VALID_SECURITY_LEVELS",
    "DocumentCreate",
    "DocumentUpdate",
    "Document",
    "SyncRequest",
    "SyncResponse",
]
