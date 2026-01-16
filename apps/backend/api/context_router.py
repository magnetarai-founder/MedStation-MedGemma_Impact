"""
Compatibility Shim for Context Router

The implementation now lives in the `api.context` package:
- api.context.types: Request/response models
- api.context.router: API endpoints

This shim maintains backward compatibility.
"""

from api.context.types import (
    ContextSearchRequest,
    ContextSearchResult,
    ContextSearchResponse,
    StoreContextRequest,
)
from api.context.router import router

__all__ = [
    # Types
    "ContextSearchRequest",
    "ContextSearchResult",
    "ContextSearchResponse",
    "StoreContextRequest",
    # Router
    "router",
]
