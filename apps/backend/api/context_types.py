"""
Context Types - Request/response models for ANE context engine

Extracted from context_router.py during P2 decomposition.
Contains:
- ContextSearchRequest (search query)
- ContextSearchResult (single result)
- ContextSearchResponse (search results)
- StoreContextRequest (store context)
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class ContextSearchRequest(BaseModel):
    """Search for relevant context across all workspaces"""
    query: str
    session_id: Optional[str] = None
    workspace_types: Optional[List[str]] = None  # ["vault", "data", "chat", etc.]
    limit: int = 10


class ContextSearchResult(BaseModel):
    """Single context search result"""
    source: str  # "vault", "chat", "data", "kanban", etc.
    content: str
    relevance_score: float
    metadata: Dict[str, Any]


class ContextSearchResponse(BaseModel):
    """Response from context search"""
    results: List[ContextSearchResult]
    total_found: int
    query_embedding_dims: int


class StoreContextRequest(BaseModel):
    """Store context for future retrieval"""
    session_id: str
    workspace_type: str  # "chat", "vault", "data", etc.
    content: str
    metadata: Dict[str, Any]


__all__ = [
    "ContextSearchRequest",
    "ContextSearchResult",
    "ContextSearchResponse",
    "StoreContextRequest",
]
