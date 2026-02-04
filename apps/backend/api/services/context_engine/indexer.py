"""
Indexers for Context Engine

Handles indexing of code and text for retrieval:
- VectorIndexer: Semantic search with embeddings
- FullTextIndexer: Keyword search with SQLite FTS5

Uses DatabaseConnection for thread-safe database access.
"""
# ruff: noqa: S608

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from api.services.db import BaseRepository, DatabaseConnection
from api.utils.structured_logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class Embedding:
    """An embedding record."""

    id: str
    source: str
    content: str
    embedding: bytes  # numpy array as bytes
    metadata: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class FTSMetadata:
    """Metadata for full-text search content."""

    id: str
    source: str
    created_at: str | None = None
    updated_at: str | None = None


# ============================================================================
# Repository Classes
# ============================================================================


class EmbeddingRepository(BaseRepository[Embedding]):
    """Repository for vector embeddings."""

    @property
    def table_name(self) -> str:
        return "embeddings"

    def _create_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS embeddings (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding BLOB NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """

    def _row_to_entity(self, row: sqlite3.Row) -> Embedding:
        return Embedding(
            id=row["id"],
            source=row["source"],
            content=row["content"],
            embedding=row["embedding"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _run_migrations(self) -> None:
        """Create indexes for performance."""
        self._create_index(["source"], name="idx_embeddings_source")

    def upsert(self, embedding: Embedding) -> None:
        """Insert or replace an embedding."""
        self.db.execute(
            """
            INSERT OR REPLACE INTO embeddings
            (id, source, content, embedding, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                embedding.id,
                embedding.source,
                embedding.content,
                embedding.embedding,
                json.dumps(embedding.metadata) if embedding.metadata else None,
            ),
        )
        self.db.get().commit()

    def upsert_batch(self, embeddings: list[Embedding]) -> None:
        """Insert or replace multiple embeddings efficiently."""
        for emb in embeddings:
            self.db.execute(
                """
                INSERT OR REPLACE INTO embeddings
                (id, source, content, embedding, metadata, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    emb.id,
                    emb.source,
                    emb.content,
                    emb.embedding,
                    json.dumps(emb.metadata) if emb.metadata else None,
                ),
            )
        self.db.get().commit()

    def find_by_source_prefix(self, source_prefix: str) -> list[Embedding]:
        """Find embeddings by source prefix."""
        return self.find_where("source LIKE ?", (f"{source_prefix}%",))

    def delete_by_source_prefix(self, source_prefix: str) -> int:
        """Delete embeddings by source prefix."""
        return self.delete_where("source LIKE ?", (f"{source_prefix}%",))


class FTSMetadataRepository(BaseRepository[FTSMetadata]):
    """Repository for FTS metadata tracking."""

    @property
    def table_name(self) -> str:
        return "fts_metadata"

    def _create_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS fts_metadata (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """

    def _row_to_entity(self, row: sqlite3.Row) -> FTSMetadata:
        return FTSMetadata(
            id=row["id"],
            source=row["source"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def upsert(self, metadata: FTSMetadata) -> None:
        """Insert or replace metadata."""
        self.db.execute(
            """
            INSERT OR REPLACE INTO fts_metadata (id, source, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (metadata.id, metadata.source),
        )
        self.db.get().commit()

    def delete_by_source_prefix(self, source_prefix: str) -> int:
        """Delete metadata by source prefix."""
        return self.delete_where("source LIKE ?", (f"{source_prefix}%",))


class VectorIndexer:
    """
    Vector embedding indexer using sentence-transformers.

    Provides semantic search by converting text to dense vectors.
    Uses all-MiniLM-L6-v2 model (lightweight, fast, good quality).
    Uses DatabaseConnection and EmbeddingRepository for thread-safe DB access.
    """

    def __init__(
        self, model_name: str = "all-MiniLM-L6-v2", db_path: str | Path = "context.db"
    ):
        """
        Initialize vector indexer.

        Args:
            model_name: Sentence transformer model name
            db_path: Path to SQLite database
        """
        self.model_name = model_name
        self.model: SentenceTransformer | None = None
        self.dimension: int | None = None

        # Initialize database connection and repository
        self._db = DatabaseConnection(Path(db_path))
        self._repo = EmbeddingRepository(self._db)

    def _load_model(self):
        """Lazy load the embedding model"""
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            # Get embedding dimension
            test_embedding = self.model.encode(["test"])
            self.dimension = test_embedding.shape[1]
            logger.info(f"Model loaded. Embedding dimension: {self.dimension}")

    def _generate_id(self, source: str, content: str) -> str:
        """Generate unique ID for content"""
        hash_input = f"{source}:{content}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def index(self, source: str, content: str, metadata: dict[str, Any] | None = None) -> str:
        """
        Index a piece of content.

        Args:
            source: Source identifier (e.g., "file:path/to/file.py")
            content: Text content to index
            metadata: Optional metadata dict

        Returns:
            Document ID
        """
        self._load_model()

        # Generate ID
        doc_id = self._generate_id(source, content)

        # Generate embedding
        embedding_array = self.model.encode([content])[0]
        embedding_bytes = embedding_array.tobytes()

        # Store using repository
        self._repo.upsert(
            Embedding(
                id=doc_id,
                source=source,
                content=content,
                embedding=embedding_bytes,
                metadata=metadata,
            )
        )

        return doc_id

    def index_batch(self, items: list[tuple[str, str, dict | None]]) -> list[str]:
        """
        Index multiple items in batch for efficiency.

        Args:
            items: List of (source, content, metadata) tuples

        Returns:
            List of document IDs
        """
        if not items:
            return []

        self._load_model()

        # Generate embeddings in batch (much faster)
        contents = [item[1] for item in items]
        embeddings_array = self.model.encode(contents, show_progress_bar=len(contents) > 10)

        # Build embedding objects
        doc_ids = []
        embedding_objects = []

        for i, (source, content, metadata) in enumerate(items):
            doc_id = self._generate_id(source, content)
            embedding_bytes = embeddings_array[i].tobytes()

            embedding_objects.append(
                Embedding(
                    id=doc_id,
                    source=source,
                    content=content,
                    embedding=embedding_bytes,
                    metadata=metadata,
                )
            )
            doc_ids.append(doc_id)

        # Store using repository batch operation
        self._repo.upsert_batch(embedding_objects)

        return doc_ids

    def search(
        self, query: str, top_k: int = 5, source_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Search for similar content using cosine similarity.

        Args:
            query: Query text
            top_k: Number of results to return
            source_filter: Optional source prefix filter

        Returns:
            List of results with content and similarity scores
        """
        self._load_model()

        # Generate query embedding
        query_embedding = self.model.encode([query])[0]

        # Fetch embeddings using repository
        if source_filter:
            embeddings = self._repo.find_by_source_prefix(source_filter)
        else:
            embeddings = self._repo.find_all()

        # Calculate similarities
        results = []
        for emb in embeddings:
            # Convert bytes back to numpy array
            embedding_array = np.frombuffer(emb.embedding, dtype=np.float32)

            # Calculate cosine similarity
            similarity = np.dot(query_embedding, embedding_array) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(embedding_array)
            )

            results.append(
                {
                    "id": emb.id,
                    "source": emb.source,
                    "content": emb.content,
                    "score": float(similarity),
                    "metadata": emb.metadata,
                }
            )

        # Sort by similarity (highest first)
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:top_k]

    def delete(self, doc_id: str) -> bool:
        """Delete a document by ID."""
        return self._repo.delete_by_id(doc_id)

    def clear(self, source_filter: str | None = None) -> None:
        """Clear all embeddings or by source filter."""
        if source_filter:
            self._repo.delete_by_source_prefix(source_filter)
        else:
            self._repo.delete_where("1=1", ())


class FullTextIndexer:
    """
    Full-text search indexer using SQLite FTS5.

    Provides fast keyword search with ranking.
    Uses DatabaseConnection for thread-safe access.
    Note: FTS5 virtual tables don't fit the repository pattern,
    so queries are inline but use the shared connection.
    """

    def __init__(self, db_path: str | Path = "context.db"):
        """
        Initialize full-text indexer.

        Args:
            db_path: Path to SQLite database
        """
        # Initialize database connection and metadata repository
        self._db = DatabaseConnection(Path(db_path))
        self._metadata_repo = FTSMetadataRepository(self._db)

        # Create FTS5 virtual table (special syntax, not via repository)
        self._init_fts_table()

    def _init_fts_table(self) -> None:
        """Initialize SQLite FTS5 virtual table."""
        self._db.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_content USING fts5(
                id UNINDEXED,
                source UNINDEXED,
                content,
                metadata UNINDEXED,
                tokenize='porter unicode61'
            )
            """
        )
        self._db.get().commit()

    def index(self, source: str, content: str, metadata: dict[str, Any] | None = None) -> str:
        """
        Index content for full-text search.

        Args:
            source: Source identifier
            content: Text content
            metadata: Optional metadata

        Returns:
            Document ID
        """
        # Generate ID (same as VectorIndexer for consistency)
        hash_input = f"{source}:{content}"
        doc_id = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        metadata_json = json.dumps(metadata) if metadata else None

        # Insert into FTS table (special syntax, not via repository)
        self._db.execute(
            """
            INSERT OR REPLACE INTO fts_content (id, source, content, metadata)
            VALUES (?, ?, ?, ?)
            """,
            (doc_id, source, content, metadata_json),
        )
        self._db.get().commit()

        # Insert into metadata table using repository
        self._metadata_repo.upsert(FTSMetadata(id=doc_id, source=source))

        return doc_id

    def search(
        self, query: str, top_k: int = 5, source_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Search using full-text search.

        Args:
            query: Search query
            top_k: Number of results
            source_filter: Optional source filter

        Returns:
            List of results with BM25 scores
        """
        # FTS5 query with ranking (special syntax, not via repository)
        if source_filter:
            rows = self._db.fetchall(
                """
                SELECT id, source, content, bm25(fts_content) as score, metadata
                FROM fts_content
                WHERE fts_content MATCH ? AND source LIKE ?
                ORDER BY score
                LIMIT ?
                """,
                (query, f"{source_filter}%", top_k),
            )
        else:
            rows = self._db.fetchall(
                """
                SELECT id, source, content, bm25(fts_content) as score, metadata
                FROM fts_content
                WHERE fts_content MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (query, top_k),
            )

        results = []
        for row in rows:
            metadata = json.loads(row["metadata"]) if row["metadata"] else None

            results.append(
                {
                    "id": row["id"],
                    "source": row["source"],
                    "content": row["content"],
                    "score": abs(float(row["score"])),  # BM25 scores are negative
                    "metadata": metadata,
                }
            )

        return results

    def delete(self, doc_id: str) -> bool:
        """Delete a document."""
        # Delete from FTS table
        cursor = self._db.execute("DELETE FROM fts_content WHERE id = ?", (doc_id,))
        deleted = cursor.rowcount > 0
        self._db.get().commit()

        # Delete from metadata table using repository
        self._metadata_repo.delete_by_id(doc_id)

        return deleted

    def clear(self, source_filter: str | None = None) -> None:
        """Clear all or filtered documents."""
        if source_filter:
            self._db.execute(
                "DELETE FROM fts_content WHERE source LIKE ?", (f"{source_filter}%",)
            )
            self._db.get().commit()
            self._metadata_repo.delete_by_source_prefix(source_filter)
        else:
            self._db.execute("DELETE FROM fts_content")
            self._db.get().commit()
            self._metadata_repo.delete_where("1=1", ())
