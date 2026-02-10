"""
Context Package

ANE Context Engine API for MedStation:
- Semantic search across workspaces
- Background vectorization
- RAG document retrieval
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
