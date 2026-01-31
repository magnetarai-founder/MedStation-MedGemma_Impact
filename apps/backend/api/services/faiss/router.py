"""
FAISS Search Router - Phase 3: Backend RAG Integration

FastAPI router for FAISS vector search endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import logging

from api.auth_middleware import get_current_user
from api.errors import http_400, http_500

from api.services.faiss import (
    get_faiss_service,
    FAISSSearchRequest,
    FAISSSearchResponse,
    FAISSIndexRequest,
    FAISSIndexResult,
    FAISSBatchIndexRequest,
    FAISSBatchIndexResult,
    FAISSDeleteRequest,
    FAISSDeleteResult,
    FAISSIndexStatistics,
    FAISSHealthResponse,
    FAISSReindexRequest,
    FAISSReindexResult,
    RAGSourceType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/faiss", tags=["faiss", "rag"])


# MARK: - Search Endpoints

@router.post("/search", response_model=FAISSSearchResponse)
async def faiss_search(
    request: FAISSSearchRequest,
    current_user = Depends(get_current_user)
):
    """
    Perform semantic search using FAISS vector similarity.

    Features:
    - Sentence-transformer embeddings for high-quality semantic matching
    - Hybrid search combining semantic + keyword matching
    - Source filtering (chat, themes, files, etc.)
    - Conversation scoping
    """
    try:
        service = get_faiss_service()
        result = await service.search(request, user_id=str(current_user.id))
        return result

    except ValueError as e:
        logger.warning(f"FAISS search validation error: {e}")
        raise http_400(str(e))
    except Exception as e:
        logger.error(f"FAISS search failed: {e}", exc_info=True)
        raise http_500("Search failed")


@router.post("/search/conversation/{conversation_id}", response_model=FAISSSearchResponse)
async def faiss_search_conversation(
    conversation_id: str,
    query: str,
    limit: int = 10,
    min_similarity: float = 0.3,
    current_user = Depends(get_current_user)
):
    """
    Search within a specific conversation.
    Convenience endpoint for conversation-scoped search.
    """
    try:
        service = get_faiss_service()

        request = FAISSSearchRequest(
            query=query,
            limit=limit,
            min_similarity=min_similarity,
            conversation_id=conversation_id
        )

        result = await service.search(request, user_id=str(current_user.id))
        return result

    except Exception as e:
        logger.error(f"Conversation search failed: {e}", exc_info=True)
        raise http_500("Search failed")


# MARK: - Index Endpoints

@router.post("/index", response_model=FAISSIndexResult)
async def faiss_index(
    request: FAISSIndexRequest,
    current_user = Depends(get_current_user)
):
    """
    Index content for semantic search.

    Automatically:
    - Chunks large content
    - Generates embeddings
    - Stores in FAISS index
    """
    try:
        service = get_faiss_service()
        result = await service.index_document(request, user_id=str(current_user.id))
        return result

    except ValueError as e:
        logger.warning(f"FAISS index validation error: {e}")
        raise http_400(str(e))
    except Exception as e:
        logger.error(f"FAISS index failed: {e}", exc_info=True)
        raise http_500("Indexing failed")


@router.post("/index/batch", response_model=FAISSBatchIndexResult)
async def faiss_index_batch(
    request: FAISSBatchIndexRequest,
    current_user = Depends(get_current_user)
):
    """
    Batch index multiple items.
    More efficient than individual requests for bulk operations.
    """
    try:
        service = get_faiss_service()
        result = await service.index_batch(request.items, user_id=str(current_user.id))
        return result

    except Exception as e:
        logger.error(f"FAISS batch index failed: {e}", exc_info=True)
        raise http_500("Batch indexing failed")


@router.post("/index/message")
async def faiss_index_message(
    session_id: str,
    message_id: str,
    content: str,
    role: str = "user",
    current_user = Depends(get_current_user)
):
    """
    Index a chat message.
    Convenience endpoint for message indexing.
    """
    try:
        from api.services.faiss import FAISSIndexRequest, DocumentMetadata

        service = get_faiss_service()

        request = FAISSIndexRequest(
            content=content,
            source=RAGSourceType.CHAT_MESSAGE,
            metadata=DocumentMetadata(
                session_id=session_id,
                message_id=message_id,
            ),
            chunk_if_needed=False  # Messages are typically short
        )

        result = await service.index_document(request, user_id=str(current_user.id))

        return {
            "status": "indexed",
            "document_ids": result.document_ids
        }

    except Exception as e:
        logger.error(f"Message index failed: {e}", exc_info=True)
        raise http_500("Message indexing failed")


# MARK: - Delete Endpoints

@router.delete("/documents", response_model=FAISSDeleteResult)
async def faiss_delete(
    request: FAISSDeleteRequest,
    current_user = Depends(get_current_user)
):
    """
    Delete documents from the index.

    Can delete by:
    - Specific document IDs
    - Conversation ID (all documents in conversation)
    - Source type (all documents of a type)
    """
    try:
        service = get_faiss_service()
        result = await service.delete(
            document_ids=request.document_ids,
            conversation_id=request.conversation_id,
            source=request.source,
            user_id=str(current_user.id)
        )
        return result

    except Exception as e:
        logger.error(f"FAISS delete failed: {e}", exc_info=True)
        raise http_500("Delete failed")


@router.delete("/conversation/{conversation_id}", response_model=FAISSDeleteResult)
async def faiss_delete_conversation(
    conversation_id: str,
    current_user = Depends(get_current_user)
):
    """
    Delete all documents for a conversation.
    Convenience endpoint for conversation cleanup.
    """
    try:
        service = get_faiss_service()
        result = await service.delete(
            conversation_id=conversation_id,
            user_id=str(current_user.id)
        )
        return result

    except Exception as e:
        logger.error(f"Conversation delete failed: {e}", exc_info=True)
        raise http_500("Delete failed")


# MARK: - Admin Endpoints

@router.get("/statistics", response_model=FAISSIndexStatistics)
async def faiss_statistics(
    current_user = Depends(get_current_user)
):
    """
    Get FAISS index statistics.

    Returns:
    - Total documents and vectors
    - Distribution by source type
    - Index size and configuration
    """
    try:
        service = get_faiss_service()
        return service.get_statistics()

    except Exception as e:
        logger.error(f"FAISS statistics failed: {e}", exc_info=True)
        raise http_500("Failed to get statistics")


@router.get("/health", response_model=FAISSHealthResponse)
async def faiss_health():
    """
    Health check for FAISS service.
    Does not require authentication.
    """
    try:
        service = get_faiss_service()
        return service.health_check()

    except Exception as e:
        logger.error(f"FAISS health check failed: {e}")
        return FAISSHealthResponse(
            status="unhealthy",
            index_loaded=False,
            total_documents=0,
            sentence_transformer_loaded=False,
            embedding_model="unknown"
        )


@router.post("/rebuild")
async def faiss_rebuild(
    current_user = Depends(get_current_user)
):
    """
    Rebuild the FAISS index.

    This will:
    - Re-embed all documents
    - Create a fresh FAISS index
    - Reclaim space from deleted documents

    Note: This is a heavy operation, use sparingly.
    """
    # Check admin role
    if current_user.role not in ['founder', 'admin']:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        service = get_faiss_service()
        service.rebuild_index()

        return {
            "status": "rebuilt",
            "total_vectors": service._index.ntotal if service._index else 0
        }

    except Exception as e:
        logger.error(f"FAISS rebuild failed: {e}", exc_info=True)
        raise http_500("Rebuild failed")


@router.post("/save")
async def faiss_save(
    current_user = Depends(get_current_user)
):
    """
    Save FAISS index to disk.
    Normally auto-saved, but can be triggered manually.
    """
    if current_user.role not in ['founder', 'admin']:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        service = get_faiss_service()
        service.save_index()

        return {"status": "saved"}

    except Exception as e:
        logger.error(f"FAISS save failed: {e}", exc_info=True)
        raise http_500("Save failed")


# MARK: - Utility Endpoints

@router.post("/embed")
async def faiss_embed(
    text: str,
    current_user = Depends(get_current_user)
):
    """
    Generate embedding for text.
    Utility endpoint for testing or manual embedding.
    """
    try:
        service = get_faiss_service()
        embedding = service._embed([text])[0]

        return {
            "text": text[:100] + "..." if len(text) > 100 else text,
            "embedding_dimension": len(embedding),
            "embedding": embedding.tolist()
        }

    except Exception as e:
        logger.error(f"FAISS embed failed: {e}", exc_info=True)
        raise http_500("Embedding failed")


@router.get("/sources")
async def faiss_sources():
    """
    List available source types.
    """
    return {
        "sources": [
            {"value": s.value, "name": s.name}
            for s in RAGSourceType
        ]
    }
