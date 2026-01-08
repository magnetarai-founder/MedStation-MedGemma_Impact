"""
Vault Semantic Search Routes

AI-powered semantic search for vault files using ANE Context Engine.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel

from api.auth_middleware import get_current_user
from api.services.vault.core import VaultService
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
try:
    from api.utils import get_user_id
except ImportError:
    from api.utils import get_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/vault", tags=["vault-semantic-search"])


# MARK: - Request/Response Models

class SemanticSearchRequest(BaseModel):
    query: str
    vault_type: str  # "real" or "decoy"
    limit: int = 10
    min_similarity: float = 0.3  # Minimum similarity threshold (0.0-1.0)


class SemanticSearchResult(BaseModel):
    file_id: str
    filename: str
    folder_path: Optional[str]
    mime_type: str
    file_size: int
    created_at: str
    updated_at: str
    similarity_score: float
    snippet: Optional[str] = None  # Text snippet if available


class SemanticSearchResponse(BaseModel):
    results: List[SemanticSearchResult]
    query: str
    total_results: int


# MARK: - Semantic Search Endpoint

@router.post(
    "/semantic-search",
    response_model=SuccessResponse[SemanticSearchResponse],
    status_code=status.HTTP_200_OK,
    name="semantic_search_vault_files",
    summary="Semantic search for vault files",
    description="AI-powered semantic search for vault files using ANE Context Engine with on-device embeddings"
)
async def semantic_search_files(
    request: SemanticSearchRequest,
    user_claims: dict = Depends(get_current_user)
) -> SuccessResponse[SemanticSearchResponse]:
    """
    Semantic search for vault files using AI embeddings.
    Uses ANE Context Engine for fast, on-device semantic matching.
    """
    try:
        user_id = get_user_id(user_claims)
        logger.info(f"Semantic search: user={user_id}, query='{request.query[:50]}...'")

        # Get embedding for query
        query_embedding = await embed_query(request.query)

        if not query_embedding:
            # Fallback to text search
            logger.warning("Embeddings unavailable, falling back to text search")
            fallback_response = await fallback_text_search(user_id, request)
            return SuccessResponse(
                data=fallback_response,
                message=f"Found {fallback_response.total_results} file(s) (text search fallback)"
            )

        # Get vault service
        vault_service = VaultService()

        # Get all files for this vault
        files = vault_service.list_files(
            user_id=user_id,
            vault_type=request.vault_type
        )

        # Compute similarity for each file
        results = []
        for file in files:
            # Create searchable text from file metadata
            searchable_text = create_searchable_text(file)

            # Get file embedding
            file_embedding = await embed_query(searchable_text)

            if file_embedding:
                # Compute cosine similarity
                similarity = compute_cosine_similarity(query_embedding, file_embedding)

                if similarity >= request.min_similarity:
                    results.append(SemanticSearchResult(
                        file_id=file["id"],
                        filename=file["filename"],
                        folder_path=file.get("folder_path"),
                        mime_type=file.get("mime_type", "application/octet-stream"),
                        file_size=file["file_size"],
                        created_at=file["created_at"],
                        updated_at=file["updated_at"],
                        similarity_score=round(similarity, 4),
                        snippet=create_snippet(searchable_text, request.query)
                    ))

        # Sort by similarity score
        results.sort(key=lambda x: x.similarity_score, reverse=True)

        # Limit results
        results = results[:request.limit]

        logger.info(f"Found {len(results)} semantic matches")

        response_data = SemanticSearchResponse(
            results=results,
            query=request.query,
            total_results=len(results)
        )

        return SuccessResponse(
            data=response_data,
            message=f"Found {len(results)} semantic match{'es' if len(results) != 1 else ''}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Semantic search failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to perform semantic search"
            ).model_dump()
        )


# MARK: - Helper Functions

async def embed_query(text: str) -> Optional[List[float]]:
    """Generate embedding for query text using ANE Context Engine"""
    try:
        from api.ane_context_engine import ANEContextEngine

        engine = ANEContextEngine()
        # Use the engine's embedding function
        from api.ane_context_engine import _embed_with_ane
        embedding = _embed_with_ane(text)
        return embedding
    except Exception as e:
        logger.warning(f"⚠️ Embedding failed: {e}")
        return None


def create_searchable_text(file: dict) -> str:
    """Create searchable text from file metadata"""
    parts = [
        file["filename"],
        file.get("folder_path", ""),
        file.get("mime_type", ""),
    ]

    # Add tags if available
    tags = file.get("tags", [])
    if tags:
        parts.extend(tags)

    return " ".join(filter(None, parts))


def compute_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two vectors"""
    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


def create_snippet(text: str, query: str, max_length: int = 100) -> str:
    """Create a snippet of text around the query terms"""
    text_lower = text.lower()
    query_lower = query.lower()

    # Find first occurrence of any query word
    query_words = query_lower.split()
    best_pos = -1

    for word in query_words:
        pos = text_lower.find(word)
        if pos != -1 and (best_pos == -1 or pos < best_pos):
            best_pos = pos

    if best_pos == -1:
        # No match found, return start of text
        return text[:max_length] + "..." if len(text) > max_length else text

    # Extract snippet around match
    start = max(0, best_pos - max_length // 2)
    end = min(len(text), start + max_length)

    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    return snippet


async def fallback_text_search(user_id: str, request: SemanticSearchRequest) -> SemanticSearchResponse:
    """Fallback to text-based search when embeddings unavailable"""
    try:
        from api.services.vault.core import VaultService
        from api.services.vault.search import search_files

        vault_service = VaultService()

        # Use existing text search
        files = search_files(
            service=vault_service,
            user_id=user_id,
            vault_type=request.vault_type,
            query=request.query
        )

        # Convert to semantic search response format
        results = [
            SemanticSearchResult(
                file_id=file["id"],
                filename=file["filename"],
                folder_path=file.get("folder_path"),
                mime_type=file["mime_type"],
                file_size=file["file_size"],
                created_at=file["created_at"],
                updated_at=file["updated_at"],
                similarity_score=0.8,  # Default similarity for text match
                snippet=file["filename"]
            )
            for file in files[:request.limit]
        ]

        return SemanticSearchResponse(
            results=results,
            query=request.query,
            total_results=len(results)
        )
    except Exception as e:
        logger.error(f"❌ Fallback search failed: {e}")
        return SemanticSearchResponse(
            results=[],
            query=request.query,
            total_results=0
        )
