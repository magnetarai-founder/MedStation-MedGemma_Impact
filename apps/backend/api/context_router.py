#!/usr/bin/env python3
"""
Context API Router - Phase 5: ANE Context Engine
Provides semantic search and RAG document retrieval for intelligent model routing
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from api.ane_context_engine import get_ane_engine
from api.auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/context", tags=["context"])


# MARK: - Request/Response Models

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


# MARK: - Endpoints

@router.post("/search", response_model=ContextSearchResponse)
async def search_context(
    request: ContextSearchRequest,
    current_user = Depends(get_current_user)
):
    """
    Semantic search across all workspace context
    Uses ANE-accelerated embeddings for fast, relevant results
    """
    try:
        engine = get_ane_engine()

        # Get query embedding
        from api.ane_context_engine import _embed_with_ane
        query_embedding = _embed_with_ane(request.query)

        # Search for similar contexts using ANE engine
        similar_results = engine.search_similar(
            query=request.query,
            top_k=request.limit,
            threshold=0.3  # Minimum similarity threshold (30%)
        )

        # Convert to response format
        results = []
        for item in similar_results:
            metadata = item.get('metadata', {})

            # Extract workspace type from metadata
            source = metadata.get('workspace', 'unknown')

            # Get content from metadata or use session_id as fallback
            content = metadata.get('content', f"Context from session {item['session_id']}")

            results.append(ContextSearchResult(
                source=source,
                content=content[:500],  # Limit content length
                relevance_score=float(item['similarity']),
                metadata={
                    'session_id': item['session_id'],
                    **metadata
                }
            ))

        return ContextSearchResponse(
            results=results,
            total_found=len(results),
            query_embedding_dims=len(query_embedding)
        )

    except Exception as e:
        logger.error(f"Context search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Context search failed: {str(e)}")


@router.post("/store")
async def store_context(
    request: StoreContextRequest,
    current_user = Depends(get_current_user)
):
    """
    Store context for future semantic search
    Automatically vectorized in background with ANE
    """
    try:
        engine = get_ane_engine()

        # Store context with metadata
        context_data = {
            "workspace": request.workspace_type,
            "content": request.content,
            **request.metadata
        }

        # Enqueue for background vectorization
        engine.enqueue_vectorization(
            session_id=request.session_id,
            context=context_data
        )

        return {"status": "queued", "session_id": request.session_id}

    except Exception as e:
        logger.error(f"Store context failed: {e}")
        raise HTTPException(status_code=500, detail=f"Store context failed: {str(e)}")


@router.get("/status")
async def get_context_status(current_user = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get ANE Context Engine status
    Returns available features, queue depth, vector count
    """
    try:
        engine = get_ane_engine()

        # Get engine statistics
        stats = engine.stats()

        return {
            "available": True,
            "backend": "ANE",  # ANE/Metal acceleration when available
            "vector_count": stats['sessions_stored'],
            "queue_depth": stats['queue_size'],
            "processed_count": stats['processed_count'],
            "error_count": stats['error_count'],
            "workers": stats['workers'],
            "retention_days": stats['retention_days'],
            "features": {
                "semantic_search": True,
                "ane_acceleration": True,
                "background_vectorization": True
            }
        }

    except Exception as e:
        logger.error(f"Get context status failed: {e}")
        return {
            "available": False,
            "error": str(e)
        }
