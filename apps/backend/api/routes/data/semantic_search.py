"""
Database Query Semantic Search Routes

AI-powered semantic search for similar past queries using ANE Context Engine.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel

from api.auth_middleware import get_current_user
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from api.utils import get_user_id
from api.shared import embed_query, compute_cosine_similarity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/data", tags=["data-semantic-search"])


# MARK: - Request/Response Models

class QuerySemanticSearchRequest(BaseModel):
    query: str
    limit: int = 10
    min_similarity: float = 0.4  # Minimum similarity threshold


class QuerySearchResult(BaseModel):
    query_text: str
    executed_at: str
    similarity_score: float
    result_count: Optional[int] = None
    execution_time_ms: Optional[int] = None


class QuerySemanticSearchResponse(BaseModel):
    results: List[QuerySearchResult]
    query: str
    total_results: int


# MARK: - Semantic Search Endpoint

@router.post(
    "/semantic-search-queries",
    response_model=SuccessResponse[QuerySemanticSearchResponse],
    status_code=status.HTTP_200_OK,
    name="semantic_search_queries",
    summary="Semantic search for queries",
    description="AI-powered semantic search for similar past database queries using ANE Context Engine"
)
async def semantic_search_queries(
    request: QuerySemanticSearchRequest,
    user_claims: dict = Depends(get_current_user)
) -> SuccessResponse[QuerySemanticSearchResponse]:
    """
    Semantic search for similar past database queries.
    Helps users find relevant queries they've run before.
    """
    try:
        user_id = get_user_id(user_claims)
        logger.info(f"Query semantic search: user={user_id}, query='{request.query[:50]}...'")

        # Get embedding for query
        query_embedding = await embed_query(request.query)

        if not query_embedding:
            logger.warning("Embeddings unavailable")
            response_data = QuerySemanticSearchResponse(
                results=[],
                query=request.query,
                total_results=0
            )
            return SuccessResponse(
                data=response_data,
                message="No results found (embeddings unavailable)"
            )

        # Get query history from database service
        query_history = await get_query_history(user_id)

        # Compute similarity for each past query
        results = []
        for past_query in query_history:
            # Get query embedding
            past_query_embedding = await embed_query(past_query["query_text"])

            if past_query_embedding:
                # Compute cosine similarity
                similarity = compute_cosine_similarity(query_embedding, past_query_embedding)

                if similarity >= request.min_similarity:
                    results.append(QuerySearchResult(
                        query_text=past_query["query_text"],
                        executed_at=past_query["executed_at"],
                        similarity_score=round(similarity, 4),
                        result_count=past_query.get("result_count"),
                        execution_time_ms=past_query.get("execution_time_ms")
                    ))

        # Sort by similarity score
        results.sort(key=lambda x: x.similarity_score, reverse=True)

        # Limit results
        results = results[:request.limit]

        logger.info(f"Found {len(results)} similar queries")

        response_data = QuerySemanticSearchResponse(
            results=results,
            query=request.query,
            total_results=len(results)
        )

        return SuccessResponse(
            data=response_data,
            message=f"Found {len(results)} similar quer{'y' if len(results) == 1 else 'ies'}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Query semantic search failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to perform semantic search"
            ).model_dump()
        )


# MARK: - Helper Functions

async def get_query_history(user_id: str, limit: int = 100) -> List[dict]:
    """Get recent query history for user"""
    try:
        # Try to import database service
        from api.services.database.core import DatabaseService

        db_service = DatabaseService()

        # Get query history (if method exists)
        if hasattr(db_service, 'get_query_history'):
            return db_service.get_query_history(user_id=user_id, limit=limit)

        # Fallback: return empty for now
        logger.warning("⚠️ DatabaseService.get_query_history not implemented yet")
        return []

    except Exception as e:
        logger.warning(f"⚠️ Failed to get query history: {e}")
        return []
