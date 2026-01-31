"""
FAISS Search Service Package

Production-grade vector search using FAISS with sentence-transformers.
"""

from api.services.faiss.models import (
    RAGSourceType,
    DocumentMetadata,
    FAISSDocument,
    FAISSSearchRequest,
    FAISSSearchResult,
    FAISSSearchResponse,
    FAISSIndexRequest,
    FAISSIndexResult,
    FAISSBatchIndexRequest,
    FAISSBatchIndexResult,
    FAISSDeleteRequest,
    FAISSDeleteResult,
    FAISSIndexStatistics,
    FAISSHealthResponse,
    FAISSConfiguration,
    FAISSReindexRequest,
    FAISSReindexResult,
)

from api.services.faiss.search_service import (
    FAISSSearchService,
    get_faiss_service,
)

__all__ = [
    # Models
    "RAGSourceType",
    "DocumentMetadata",
    "FAISSDocument",
    "FAISSSearchRequest",
    "FAISSSearchResult",
    "FAISSSearchResponse",
    "FAISSIndexRequest",
    "FAISSIndexResult",
    "FAISSBatchIndexRequest",
    "FAISSBatchIndexResult",
    "FAISSDeleteRequest",
    "FAISSDeleteResult",
    "FAISSIndexStatistics",
    "FAISSHealthResponse",
    "FAISSConfiguration",
    "FAISSReindexRequest",
    "FAISSReindexResult",
    # Service
    "FAISSSearchService",
    "get_faiss_service",
]
