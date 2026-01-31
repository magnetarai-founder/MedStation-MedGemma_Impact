"""
FAISS Search Models - Phase 3: Backend RAG Integration

Pydantic models for FAISS vector search service.
Provides type-safe request/response handling for semantic search.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


# MARK: - Enums

class RAGSourceType(str, Enum):
    """Source types for RAG documents"""
    CHAT_MESSAGE = "chat_message"
    THEME = "theme"
    SEMANTIC_NODE = "semantic_node"
    FILE = "file"
    VAULT_FILE = "vault_file"
    WORKFLOW = "workflow"
    KANBAN_TASK = "kanban_task"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    CODE_FILE = "code_file"
    DATASET_COLUMN = "dataset_column"
    TEAM_MESSAGE = "team_message"


# MARK: - Document Models

class DocumentMetadata(BaseModel):
    """Metadata for an indexed document"""
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    message_id: Optional[str] = None
    file_id: Optional[str] = None
    workflow_id: Optional[str] = None
    task_id: Optional[str] = None
    document_id: Optional[str] = None
    team_id: Optional[str] = None
    title: Optional[str] = None
    content_type: Optional[str] = None
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None
    tags: Optional[List[str]] = None
    is_vault_protected: bool = False
    extra: Optional[Dict[str, Any]] = None


class FAISSDocument(BaseModel):
    """A document stored in the FAISS index"""
    id: str
    content: str
    embedding: List[float]
    source: RAGSourceType
    metadata: DocumentMetadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# MARK: - Search Models

class FAISSSearchRequest(BaseModel):
    """Request for FAISS semantic search"""
    query: str = Field(..., min_length=1, max_length=10000)
    limit: int = Field(default=10, ge=1, le=100)
    min_similarity: float = Field(default=0.3, ge=0.0, le=1.0)
    sources: Optional[List[RAGSourceType]] = None
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    include_embeddings: bool = Field(default=False)
    use_hybrid_search: bool = Field(default=True)

    class Config:
        json_schema_extra = {
            "example": {
                "query": "How do I implement authentication?",
                "limit": 10,
                "min_similarity": 0.3,
                "sources": ["chat_message", "theme"],
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class FAISSSearchResult(BaseModel):
    """A single search result"""
    id: str
    content: str
    source: RAGSourceType
    similarity: float
    rank: int
    metadata: DocumentMetadata
    snippet: Optional[str] = None
    matched_terms: Optional[List[str]] = None
    embedding: Optional[List[float]] = None

    @property
    def combined_score(self) -> float:
        """Combined score considering similarity and source priority"""
        source_priority = {
            RAGSourceType.CHAT_MESSAGE: 1.0,
            RAGSourceType.THEME: 0.9,
            RAGSourceType.SEMANTIC_NODE: 0.85,
            RAGSourceType.FILE: 0.8,
            RAGSourceType.VAULT_FILE: 0.8,
            RAGSourceType.CODE_FILE: 0.8,
            RAGSourceType.WORKFLOW: 0.7,
            RAGSourceType.KANBAN_TASK: 0.7,
            RAGSourceType.DOCUMENT: 0.6,
            RAGSourceType.SPREADSHEET: 0.6,
            RAGSourceType.DATASET_COLUMN: 0.5,
            RAGSourceType.TEAM_MESSAGE: 0.5,
        }
        priority = source_priority.get(self.source, 0.5)
        return (self.similarity * 0.7) + (priority * 0.3)


class FAISSSearchResponse(BaseModel):
    """Response from FAISS search"""
    results: List[FAISSSearchResult]
    total_found: int
    query_time_ms: float
    source_distribution: Dict[str, int]


# MARK: - Index Models

class FAISSIndexRequest(BaseModel):
    """Request to index content"""
    content: str = Field(..., min_length=1)
    source: RAGSourceType
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    chunk_if_needed: bool = Field(default=True)
    max_chunk_size: int = Field(default=512, ge=100, le=2000)
    chunk_overlap: int = Field(default=64, ge=0, le=500)

    class Config:
        json_schema_extra = {
            "example": {
                "content": "This is the content to index for semantic search...",
                "source": "file",
                "metadata": {
                    "file_id": "550e8400-e29b-41d4-a716-446655440001",
                    "title": "README.md"
                },
                "chunk_if_needed": True
            }
        }


class FAISSIndexResult(BaseModel):
    """Result from indexing operation"""
    document_ids: List[str]
    chunks_created: int
    tokens_indexed: int
    duration_ms: float


class FAISSBatchIndexRequest(BaseModel):
    """Request to index multiple items"""
    items: List[FAISSIndexRequest] = Field(..., min_length=1, max_length=100)


class FAISSBatchIndexResult(BaseModel):
    """Result from batch indexing"""
    total_documents: int
    total_chunks: int
    total_tokens: int
    duration_ms: float
    errors: List[str] = []


# MARK: - Delete Models

class FAISSDeleteRequest(BaseModel):
    """Request to delete documents"""
    document_ids: Optional[List[str]] = None
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    source: Optional[RAGSourceType] = None


class FAISSDeleteResult(BaseModel):
    """Result from delete operation"""
    deleted_count: int
    duration_ms: float


# MARK: - Statistics Models

class FAISSIndexStatistics(BaseModel):
    """Statistics about the FAISS index"""
    total_documents: int
    total_vectors: int
    embedding_dimension: int
    index_size_bytes: int
    documents_by_source: Dict[str, int]
    last_updated: Optional[datetime] = None
    index_type: str = "IVF"  # FAISS index type
    nprobe: int = 10  # Number of clusters to search


class FAISSHealthResponse(BaseModel):
    """Health check response"""
    status: str
    index_loaded: bool
    total_documents: int
    sentence_transformer_loaded: bool
    embedding_model: str
    last_indexing: Optional[datetime] = None


# MARK: - Configuration Models

class FAISSConfiguration(BaseModel):
    """Configuration for FAISS service"""
    embedding_model: str = Field(default="all-MiniLM-L6-v2")
    embedding_dimension: int = Field(default=384)
    index_type: str = Field(default="IVF")
    nlist: int = Field(default=100)  # Number of clusters
    nprobe: int = Field(default=10)  # Clusters to search
    use_gpu: bool = Field(default=False)
    max_batch_size: int = Field(default=100)
    auto_save_interval: int = Field(default=300)  # Seconds


# MARK: - Reindex Models

class FAISSReindexRequest(BaseModel):
    """Request to reindex specific content"""
    conversation_id: Optional[str] = None
    sources: Optional[List[RAGSourceType]] = None
    force: bool = Field(default=False)


class FAISSReindexResult(BaseModel):
    """Result from reindex operation"""
    reindexed_count: int
    duration_ms: float
    errors: List[str] = []
