"""
FAISS Search Service - Phase 3: Backend RAG Integration

Production-grade vector search using FAISS with sentence-transformers.
Provides fast, scalable semantic search across all workspace content.
"""

import os
import json
import time
import logging
import sqlite3
import threading
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

import numpy as np

# Lazy imports for optional dependencies
faiss = None
SentenceTransformer = None

from api.services.faiss.models import (
    RAGSourceType,
    DocumentMetadata,
    FAISSDocument,
    FAISSSearchRequest,
    FAISSSearchResult,
    FAISSSearchResponse,
    FAISSIndexRequest,
    FAISSIndexResult,
    FAISSBatchIndexResult,
    FAISSDeleteResult,
    FAISSIndexStatistics,
    FAISSHealthResponse,
    FAISSConfiguration,
)

logger = logging.getLogger(__name__)


# MARK: - FAISS Search Service

class FAISSSearchService:
    """
    FAISS-accelerated vector search service.

    Features:
    - Sentence-transformer embeddings (all-MiniLM-L6-v2)
    - IVF index for fast approximate search
    - SQLite metadata storage
    - Hybrid semantic + keyword search
    - Thread-safe operations
    """

    def __init__(
        self,
        data_dir: str = "data/faiss",
        config: Optional[FAISSConfiguration] = None
    ):
        self.data_dir = Path(data_dir)
        self.config = config or FAISSConfiguration()

        # Paths
        self.index_path = self.data_dir / "vectors.index"
        self.metadata_path = self.data_dir / "metadata.db"

        # State
        self._index = None
        self._id_map: Dict[str, int] = {}  # doc_id -> faiss_idx
        self._reverse_map: Dict[int, str] = {}  # faiss_idx -> doc_id
        self._model = None
        self._lock = threading.RLock()
        self._next_idx = 0

        # Statistics
        self._stats = {
            "searches": 0,
            "indexings": 0,
            "last_search": None,
            "last_index": None,
        }

        # Initialize
        self._ensure_data_dir()
        self._load_dependencies()
        self._load_or_create_index()
        self._load_metadata_db()

    # MARK: - Initialization

    def _ensure_data_dir(self):
        """Create data directory if needed"""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _load_dependencies(self):
        """Lazy load FAISS and sentence-transformers"""
        global faiss, SentenceTransformer

        try:
            import faiss as _faiss
            faiss = _faiss
            logger.info("FAISS loaded successfully")
        except ImportError:
            logger.warning("FAISS not installed, using fallback search")
            faiss = None

        try:
            from sentence_transformers import SentenceTransformer as _ST
            SentenceTransformer = _ST
            self._model = SentenceTransformer(self.config.embedding_model)
            logger.info(f"Loaded embedding model: {self.config.embedding_model}")
        except ImportError:
            logger.warning("sentence-transformers not installed, using hash embeddings")
            SentenceTransformer = None
            self._model = None

    def _load_or_create_index(self):
        """Load existing FAISS index or create new one"""
        if faiss is None:
            return

        with self._lock:
            if self.index_path.exists():
                try:
                    self._index = faiss.read_index(str(self.index_path))
                    self._load_id_maps()
                    logger.info(f"Loaded FAISS index with {self._index.ntotal} vectors")
                except Exception as e:
                    logger.error(f"Failed to load FAISS index: {e}")
                    self._create_new_index()
            else:
                self._create_new_index()

    def _create_new_index(self):
        """Create new FAISS index"""
        if faiss is None:
            return

        dim = self.config.embedding_dimension

        if self.config.index_type == "IVF":
            # IVF index for fast approximate search
            quantizer = faiss.IndexFlatL2(dim)
            self._index = faiss.IndexIVFFlat(
                quantizer, dim, self.config.nlist
            )
            self._index.nprobe = self.config.nprobe
        else:
            # Flat index for exact search (slower but more accurate)
            self._index = faiss.IndexFlatL2(dim)

        self._id_map = {}
        self._reverse_map = {}
        self._next_idx = 0

        logger.info(f"Created new FAISS index (type={self.config.index_type}, dim={dim})")

    def _load_id_maps(self):
        """Load ID mappings from metadata DB"""
        try:
            conn = sqlite3.connect(str(self.metadata_path))
            cursor = conn.cursor()
            cursor.execute("SELECT doc_id, faiss_idx FROM id_map")
            for row in cursor.fetchall():
                doc_id, faiss_idx = row
                self._id_map[doc_id] = faiss_idx
                self._reverse_map[faiss_idx] = doc_id
                self._next_idx = max(self._next_idx, faiss_idx + 1)
            conn.close()
        except Exception as e:
            logger.error(f"Failed to load ID maps: {e}")

    def _load_metadata_db(self):
        """Initialize metadata SQLite database"""
        conn = sqlite3.connect(str(self.metadata_path))
        cursor = conn.cursor()

        # Create tables
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source TEXT NOT NULL,
                metadata TEXT,
                created_at REAL NOT NULL,
                last_accessed_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS id_map (
                doc_id TEXT PRIMARY KEY,
                faiss_idx INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_docs_source ON documents(source);
            CREATE INDEX IF NOT EXISTS idx_docs_created ON documents(created_at);
        """)

        conn.commit()
        conn.close()

    # MARK: - Embedding

    def _embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for texts"""
        if self._model is not None:
            # Use sentence-transformers
            embeddings = self._model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            return embeddings.astype(np.float32)
        else:
            # Fallback to hash-based embeddings
            return self._hash_embed(texts)

    def _hash_embed(self, texts: List[str]) -> np.ndarray:
        """Hash-based embeddings (fallback when sentence-transformers unavailable)"""
        import hashlib

        embeddings = []
        dim = self.config.embedding_dimension

        for text in texts:
            # Generate multiple hashes
            hash_values = []
            for i in range((dim + 7) // 8):
                hash_input = f"{text}_{i}".encode()
                hash_bytes = hashlib.md5(hash_input).digest()
                for j in range(0, 16, 2):
                    value = int.from_bytes(hash_bytes[j:j+2], 'big')
                    hash_values.append(value)

            # Convert to floats in [-1, 1]
            vector = np.array(hash_values[:dim], dtype=np.float32)
            vector = vector / 32768.0 - 1.0

            # L2 normalize
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm

            embeddings.append(vector)

        return np.array(embeddings, dtype=np.float32)

    # MARK: - Search

    async def search(
        self,
        request: FAISSSearchRequest,
        user_id: str
    ) -> FAISSSearchResponse:
        """Perform semantic search"""
        start_time = time.time()

        with self._lock:
            # Generate query embedding
            query_embedding = self._embed([request.query])[0]

            # Search FAISS index
            if self._index is not None and self._index.ntotal > 0:
                # Train index if needed (for IVF)
                if hasattr(self._index, 'is_trained') and not self._index.is_trained:
                    logger.warning("FAISS index not trained, returning empty results")
                    return FAISSSearchResponse(
                        results=[],
                        total_found=0,
                        query_time_ms=0,
                        source_distribution={}
                    )

                # Perform search
                distances, indices = self._index.search(
                    query_embedding.reshape(1, -1),
                    min(request.limit * 3, self._index.ntotal)  # Get more for filtering
                )
            else:
                distances, indices = np.array([[]]), np.array([[]])

        # Load documents and filter
        results = []
        source_dist: Dict[str, int] = {}

        conn = sqlite3.connect(str(self.metadata_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue

            doc_id = self._reverse_map.get(int(idx))
            if not doc_id:
                continue

            # Calculate similarity from L2 distance
            # Normalized vectors: sim = 1 - (dist^2 / 2)
            similarity = float(1 - (dist / 2))

            if similarity < request.min_similarity:
                continue

            # Load document
            cursor.execute(
                "SELECT * FROM documents WHERE doc_id = ?",
                (doc_id,)
            )
            row = cursor.fetchone()
            if not row:
                continue

            # Parse metadata
            metadata_dict = json.loads(row['metadata']) if row['metadata'] else {}
            source = RAGSourceType(row['source'])

            # Apply source filter
            if request.sources and source not in request.sources:
                continue

            # Apply conversation filter
            if request.conversation_id:
                if metadata_dict.get('conversation_id') != request.conversation_id:
                    continue

            # Create result
            content = row['content']
            snippet = content[:200] + "..." if len(content) > 200 else content

            result = FAISSSearchResult(
                id=doc_id,
                content=content,
                source=source,
                similarity=similarity,
                rank=len(results) + 1,
                metadata=DocumentMetadata(**metadata_dict),
                snippet=snippet,
                embedding=query_embedding.tolist() if request.include_embeddings else None
            )

            results.append(result)
            source_dist[source.value] = source_dist.get(source.value, 0) + 1

            if len(results) >= request.limit:
                break

        conn.close()

        # Apply hybrid keyword boost if enabled
        if request.use_hybrid_search:
            results = self._apply_keyword_boost(results, request.query)

        # Sort by combined score
        results.sort(key=lambda r: r.combined_score, reverse=True)

        # Update ranks
        for i, result in enumerate(results):
            result.rank = i + 1

        # Update stats
        self._stats["searches"] += 1
        self._stats["last_search"] = datetime.utcnow()

        query_time_ms = (time.time() - start_time) * 1000

        return FAISSSearchResponse(
            results=results,
            total_found=len(results),
            query_time_ms=query_time_ms,
            source_distribution=source_dist
        )

    def _apply_keyword_boost(
        self,
        results: List[FAISSSearchResult],
        query: str
    ) -> List[FAISSSearchResult]:
        """Boost results that contain query keywords"""
        keywords = self._extract_keywords(query)

        boosted = []
        for result in results:
            content_lower = result.content.lower()
            matched = [k for k in keywords if k in content_lower]

            if matched:
                # Boost similarity
                boost = min(len(matched) * 0.05, 0.2)
                boosted_result = FAISSSearchResult(
                    id=result.id,
                    content=result.content,
                    source=result.source,
                    similarity=min(1.0, result.similarity + boost),
                    rank=result.rank,
                    metadata=result.metadata,
                    snippet=result.snippet,
                    matched_terms=matched,
                    embedding=result.embedding
                )
                boosted.append(boosted_result)
            else:
                boosted.append(result)

        return boosted

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract searchable keywords from query"""
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
            'we', 'they', 'what', 'which', 'who', 'when', 'where',
            'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more'
        }

        words = query.lower().split()
        return [w.strip('.,!?') for w in words if len(w) > 2 and w not in stop_words]

    # MARK: - Indexing

    async def index_document(
        self,
        request: FAISSIndexRequest,
        user_id: str
    ) -> FAISSIndexResult:
        """Index a document for search"""
        start_time = time.time()

        # Chunk if needed
        if request.chunk_if_needed and len(request.content) > request.max_chunk_size:
            chunks = self._chunk_text(
                request.content,
                request.max_chunk_size,
                request.chunk_overlap
            )
        else:
            chunks = [request.content]

        document_ids = []
        total_tokens = 0

        for i, chunk in enumerate(chunks):
            # Create document ID
            import uuid
            doc_id = str(uuid.uuid4())

            # Update metadata with chunk info
            metadata = request.metadata.model_copy()
            if len(chunks) > 1:
                metadata.chunk_index = i
                metadata.total_chunks = len(chunks)

            # Generate embedding
            embedding = self._embed([chunk])[0]

            # Store in FAISS and SQLite
            with self._lock:
                faiss_idx = self._next_idx
                self._next_idx += 1

                self._id_map[doc_id] = faiss_idx
                self._reverse_map[faiss_idx] = doc_id

                if self._index is not None:
                    # Train IVF index if needed
                    if hasattr(self._index, 'is_trained') and not self._index.is_trained:
                        if self._index.ntotal < self.config.nlist:
                            # Not enough vectors to train, use flat index temporarily
                            self._index.add(embedding.reshape(1, -1))
                        else:
                            self._index.train(embedding.reshape(1, -1))
                            self._index.add(embedding.reshape(1, -1))
                    else:
                        self._index.add(embedding.reshape(1, -1))

            # Store in SQLite
            conn = sqlite3.connect(str(self.metadata_path))
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO documents
                (doc_id, content, source, metadata, created_at, last_accessed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                chunk,
                request.source.value,
                json.dumps(metadata.model_dump()),
                time.time(),
                time.time()
            ))

            cursor.execute("""
                INSERT OR REPLACE INTO id_map (doc_id, faiss_idx)
                VALUES (?, ?)
            """, (doc_id, faiss_idx))

            conn.commit()
            conn.close()

            document_ids.append(doc_id)
            total_tokens += len(chunk) // 4

        # Update stats
        self._stats["indexings"] += 1
        self._stats["last_index"] = datetime.utcnow()

        duration_ms = (time.time() - start_time) * 1000

        return FAISSIndexResult(
            document_ids=document_ids,
            chunks_created=len(chunks),
            tokens_indexed=total_tokens,
            duration_ms=duration_ms
        )

    def _chunk_text(
        self,
        text: str,
        chunk_size: int,
        overlap: int
    ) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))

            # Try to break at sentence boundary
            if end < len(text):
                for sep in ['. ', '\n', ' ']:
                    last_sep = text.rfind(sep, start + chunk_size - 100, end)
                    if last_sep > start:
                        end = last_sep + len(sep)
                        break

            chunks.append(text[start:end].strip())
            start = end - overlap if end < len(text) else len(text)

        return [c for c in chunks if c]

    async def index_batch(
        self,
        items: List[FAISSIndexRequest],
        user_id: str
    ) -> FAISSBatchIndexResult:
        """Index multiple documents"""
        start_time = time.time()

        total_docs = 0
        total_chunks = 0
        total_tokens = 0
        errors = []

        for item in items:
            try:
                result = await self.index_document(item, user_id)
                total_docs += 1
                total_chunks += result.chunks_created
                total_tokens += result.tokens_indexed
            except Exception as e:
                errors.append(str(e))
                logger.error(f"Failed to index item: {e}")

        duration_ms = (time.time() - start_time) * 1000

        return FAISSBatchIndexResult(
            total_documents=total_docs,
            total_chunks=total_chunks,
            total_tokens=total_tokens,
            duration_ms=duration_ms,
            errors=errors
        )

    # MARK: - Delete

    async def delete(
        self,
        document_ids: Optional[List[str]] = None,
        conversation_id: Optional[str] = None,
        source: Optional[RAGSourceType] = None,
        user_id: str = None
    ) -> FAISSDeleteResult:
        """Delete documents from index"""
        start_time = time.time()
        deleted_count = 0

        conn = sqlite3.connect(str(self.metadata_path))
        cursor = conn.cursor()

        # Build query
        if document_ids:
            placeholders = ','.join(['?' for _ in document_ids])
            cursor.execute(
                f"SELECT doc_id FROM documents WHERE doc_id IN ({placeholders})",
                document_ids
            )
        elif conversation_id:
            cursor.execute(
                "SELECT doc_id FROM documents WHERE json_extract(metadata, '$.conversation_id') = ?",
                (conversation_id,)
            )
        elif source:
            cursor.execute(
                "SELECT doc_id FROM documents WHERE source = ?",
                (source.value,)
            )
        else:
            cursor.execute("SELECT doc_id FROM documents")

        docs_to_delete = [row[0] for row in cursor.fetchall()]

        # Delete from SQLite
        for doc_id in docs_to_delete:
            cursor.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            cursor.execute("DELETE FROM id_map WHERE doc_id = ?", (doc_id,))

            # Remove from memory maps
            if doc_id in self._id_map:
                faiss_idx = self._id_map.pop(doc_id)
                self._reverse_map.pop(faiss_idx, None)

            deleted_count += 1

        conn.commit()
        conn.close()

        # Note: FAISS doesn't support true deletion, vectors remain but are orphaned
        # Periodically rebuild index to reclaim space

        duration_ms = (time.time() - start_time) * 1000

        return FAISSDeleteResult(
            deleted_count=deleted_count,
            duration_ms=duration_ms
        )

    # MARK: - Statistics & Health

    def get_statistics(self) -> FAISSIndexStatistics:
        """Get index statistics"""
        conn = sqlite3.connect(str(self.metadata_path))
        cursor = conn.cursor()

        # Count documents
        cursor.execute("SELECT COUNT(*) FROM documents")
        total_docs = cursor.fetchone()[0]

        # Count by source
        cursor.execute("SELECT source, COUNT(*) FROM documents GROUP BY source")
        by_source = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()

        # Get index size
        index_size = 0
        if self.index_path.exists():
            index_size = self.index_path.stat().st_size

        return FAISSIndexStatistics(
            total_documents=total_docs,
            total_vectors=self._index.ntotal if self._index else 0,
            embedding_dimension=self.config.embedding_dimension,
            index_size_bytes=index_size,
            documents_by_source=by_source,
            last_updated=self._stats.get("last_index"),
            index_type=self.config.index_type,
            nprobe=self.config.nprobe
        )

    def health_check(self) -> FAISSHealthResponse:
        """Health check for the service"""
        return FAISSHealthResponse(
            status="healthy" if self._index is not None else "degraded",
            index_loaded=self._index is not None,
            total_documents=self._index.ntotal if self._index else 0,
            sentence_transformer_loaded=self._model is not None,
            embedding_model=self.config.embedding_model,
            last_indexing=self._stats.get("last_index")
        )

    # MARK: - Persistence

    def save_index(self):
        """Save FAISS index to disk"""
        if self._index is not None and faiss is not None:
            with self._lock:
                faiss.write_index(self._index, str(self.index_path))
                logger.info(f"Saved FAISS index ({self._index.ntotal} vectors)")

    def rebuild_index(self):
        """Rebuild FAISS index from metadata DB (for compaction)"""
        logger.info("Rebuilding FAISS index...")

        # Load all documents
        conn = sqlite3.connect(str(self.metadata_path))
        cursor = conn.cursor()
        cursor.execute("SELECT doc_id, content FROM documents ORDER BY created_at")
        docs = cursor.fetchall()
        conn.close()

        if not docs:
            logger.info("No documents to rebuild")
            return

        # Create new index
        self._create_new_index()

        # Re-embed and add all documents
        batch_size = 100
        for i in range(0, len(docs), batch_size):
            batch = docs[i:i + batch_size]
            doc_ids = [d[0] for d in batch]
            contents = [d[1] for d in batch]

            embeddings = self._embed(contents)

            with self._lock:
                for doc_id, embedding in zip(doc_ids, embeddings):
                    faiss_idx = self._next_idx
                    self._next_idx += 1

                    self._id_map[doc_id] = faiss_idx
                    self._reverse_map[faiss_idx] = doc_id

                    if self._index is not None:
                        self._index.add(embedding.reshape(1, -1))

                # Update id_map in DB
                conn = sqlite3.connect(str(self.metadata_path))
                cursor = conn.cursor()
                for doc_id in doc_ids:
                    cursor.execute(
                        "INSERT OR REPLACE INTO id_map (doc_id, faiss_idx) VALUES (?, ?)",
                        (doc_id, self._id_map[doc_id])
                    )
                conn.commit()
                conn.close()

        self.save_index()
        logger.info(f"Rebuilt FAISS index with {len(docs)} documents")


# MARK: - Singleton

_faiss_service: Optional[FAISSSearchService] = None
_lock = threading.Lock()


def get_faiss_service(data_dir: str = "data/faiss") -> FAISSSearchService:
    """Get singleton FAISS service instance"""
    global _faiss_service

    with _lock:
        if _faiss_service is None:
            _faiss_service = FAISSSearchService(data_dir=data_dir)
        return _faiss_service
