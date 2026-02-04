"""
FAISS-Accelerated Semantic Search

Provides fast approximate nearest neighbor search using FAISS.

Features:
- 10-100x faster search than brute-force
- Scales to millions of embeddings
- Incremental index updates
- Index persistence to disk
- Multiple index types (Flat, IVF, HNSW)

Uses DatabaseConnection for thread-safe database access.

Installation:
    pip install faiss-cpu  # or faiss-gpu for GPU support

Usage:
    from api.services.faiss_search import FAISSSemanticSearch

    search = FAISSSemanticSearch(db_path)
    await search.build_index()  # Build from existing embeddings

    results = await search.search("find code examples", top_k=10)
"""

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from api.config.constants import EMBEDDING_DIMENSION
from api.services.db import DatabaseConnection
from api.utils.structured_logging import get_logger

logger = get_logger(__name__)

# Check if FAISS is available
try:
    import faiss

    FAISS_AVAILABLE = True
    logger.info("FAISS library loaded successfully")
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not available - falling back to brute-force search")


@dataclass
class FAISSSearchResult:
    """A single FAISS search result"""

    message_id: int
    session_id: str
    session_title: str | None
    role: str
    content: str
    timestamp: str
    model: str | None
    similarity: float
    snippet: str


class FAISSSemanticSearch:
    """
    FAISS-accelerated semantic search engine.

    Provides fast approximate nearest neighbor search for embeddings.
    """

    def __init__(
        self,
        db_path: Path,
        index_type: str = "IVFFlat",
        nlist: int = 100,
        nprobe: int = 10,
    ):
        """
        Initialize FAISS search engine.

        Args:
            db_path: Path to chat memory database
            index_type: FAISS index type (Flat, IVFFlat, HNSW)
            nlist: Number of clusters for IVF index
            nprobe: Number of clusters to search

        Index types:
            - Flat: Exact search, slower but most accurate
            - IVFFlat: Inverted file index, 10-100x faster
            - HNSW: Hierarchical NSW graph, very fast
        """
        if not FAISS_AVAILABLE:
            raise ImportError(
                "FAISS not installed. Install with: pip install faiss-cpu or faiss-gpu"
            )

        self.index_type = index_type
        self.nlist = nlist
        self.nprobe = nprobe

        self.index: faiss.Index | None = None
        self.id_map: list[int] = []  # Maps FAISS index to message IDs
        self.dimension = EMBEDDING_DIMENSION

        # Use DatabaseConnection for thread-safe database access
        self._db = DatabaseConnection(db_path)
        self._lock = threading.Lock()

        logger.info(
            f"Initialized FAISS search engine",
            index_type=index_type,
            nlist=nlist,
            nprobe=nprobe,
        )

    async def build_index(self, force_rebuild: bool = False) -> dict[str, Any]:
        """
        Build FAISS index from existing embeddings.

        Args:
            force_rebuild: Force rebuild even if index exists

        Returns:
            Statistics about index building
        """
        # Check if we can load existing index
        if not force_rebuild:
            loaded = await self.load_index()
            if loaded:
                logger.info("Loaded existing FAISS index from disk")
                return {"loaded": True, "embeddings_count": len(self.id_map)}

        logger.info("Building FAISS index from database...")

        # Fetch all embeddings from database using DatabaseConnection
        rows = self._db.fetchall(
            """
            SELECT message_id, embedding_json
            FROM message_embeddings
            WHERE embedding_json IS NOT NULL
            ORDER BY message_id
            """
        )

        embeddings_list = []
        message_ids = []

        for row in rows:
            try:
                embedding = json.loads(row["embedding_json"])
                embeddings_list.append(embedding)
                message_ids.append(row["message_id"])
            except Exception as e:
                logger.error(f"Failed to parse embedding for message {row['message_id']}: {e}")
                continue

        if not embeddings_list:
            logger.warning("No embeddings found in database")
            return {"error": "No embeddings to index"}

        # Convert to numpy array
        embeddings_np = np.array(embeddings_list, dtype=np.float32)
        num_embeddings = len(embeddings_np)

        logger.info(f"Building index with {num_embeddings} embeddings")

        # Build FAISS index based on type
        if self.index_type == "Flat":
            # Exact search (slowest but most accurate)
            self.index = faiss.IndexFlatIP(self.dimension)

        elif self.index_type == "IVFFlat":
            # Inverted file index (fast approximate search)
            quantizer = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, self.nlist)

            # Train index on data
            logger.info("Training IVF index...")
            self.index.train(embeddings_np)

        elif self.index_type == "HNSW":
            # Hierarchical NSW graph (very fast)
            self.index = faiss.IndexHNSWFlat(self.dimension, 32)

        else:
            raise ValueError(f"Unknown index type: {self.index_type}")

        # Add embeddings to index
        logger.info("Adding embeddings to index...")
        self.index.add(embeddings_np)

        # Store ID mapping
        self.id_map = message_ids

        # Set search parameters
        if self.index_type == "IVFFlat":
            self.index.nprobe = self.nprobe

        # Save index to disk
        await self.save_index()

        logger.info(
            f"FAISS index built successfully",
            embeddings_count=num_embeddings,
            index_type=self.index_type,
        )

        return {
            "embeddings_count": num_embeddings,
            "index_type": self.index_type,
            "dimension": self.dimension,
        }

    async def add_embedding(self, message_id: int, embedding: list[float]) -> None:
        """
        Add a single embedding to the index (incremental update).

        Args:
            message_id: Message ID
            embedding: Embedding vector
        """
        if self.index is None:
            logger.warning("Index not built yet, skipping add")
            return

        with self._lock:
            # Convert to numpy
            embedding_np = np.array([embedding], dtype=np.float32)

            # Add to index
            self.index.add(embedding_np)

            # Update ID map
            self.id_map.append(message_id)

        logger.debug(f"Added embedding for message {message_id} to index")

    async def search(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.3,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> list[FAISSSearchResult]:
        """
        Search for similar messages using FAISS.

        Args:
            query: Search query
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score
            user_id: Filter by user ID
            team_id: Filter by team ID

        Returns:
            List of search results
        """
        if self.index is None:
            raise RuntimeError("Index not built. Call build_index() first.")

        # Generate query embedding
        from api.services.semantic_search import get_semantic_search

        semantic_search = get_semantic_search(self.db_path)
        query_embedding = await semantic_search.generate_embedding(query)
        query_embedding_np = np.array([query_embedding], dtype=np.float32)

        # Search FAISS index
        # k should be larger to account for filtering
        search_k = min(top_k * 5, len(self.id_map))
        distances, indices = self.index.search(query_embedding_np, search_k)

        # Get message IDs from index
        candidate_message_ids = [
            self.id_map[idx] for idx in indices[0] if idx < len(self.id_map)
        ]

        if not candidate_message_ids:
            return []

        # Fetch message details from database using DatabaseConnection
        # Build query with filters
        placeholders = ",".join("?" * len(candidate_message_ids))
        query_sql = f"""
            SELECT
                m.id as message_id,
                m.session_id,
                m.role,
                m.content,
                m.timestamp,
                m.model,
                s.title as session_title,
                e.embedding_json
            FROM chat_messages m
            JOIN chat_sessions s ON m.session_id = s.id
            LEFT JOIN message_embeddings e ON m.id = e.message_id
            WHERE m.id IN ({placeholders})
        """

        params: list[Any] = list(candidate_message_ids)

        # Add filters
        if team_id:
            query_sql += " AND m.team_id = ?"
            params.append(team_id)
        elif user_id:
            query_sql += " AND m.user_id = ? AND m.team_id IS NULL"
            params.append(user_id)

        rows = self._db.fetchall(query_sql, params)
        messages = {row["message_id"]: dict(row) for row in rows}

        # Build results with similarity scores
        results = []
        for idx, (distance, faiss_idx) in enumerate(zip(distances[0], indices[0])):
            if faiss_idx >= len(self.id_map):
                continue

            message_id = self.id_map[faiss_idx]
            message = messages.get(message_id)

            if not message:
                continue

            # Convert distance to similarity (cosine similarity)
            similarity = float(distance)

            if similarity >= similarity_threshold:
                # Create snippet
                content = message["content"]
                snippet = content[:200] + "..." if len(content) > 200 else content

                results.append(
                    FAISSSearchResult(
                        message_id=message_id,
                        session_id=message["session_id"],
                        session_title=message.get("session_title"),
                        role=message["role"],
                        content=content,
                        timestamp=message["timestamp"],
                        model=message.get("model"),
                        similarity=similarity,
                        snippet=snippet,
                    )
                )

        # Sort by similarity and return top_k
        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]

    async def save_index(self, index_path: Path | None = None) -> None:
        """
        Save FAISS index to disk.

        Args:
            index_path: Path to save index (defaults to data/faiss_index.bin)
        """
        if self.index is None:
            logger.warning("No index to save")
            return

        if index_path is None:
            index_path = Path("data/faiss_index.bin")

        index_path.parent.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        faiss.write_index(self.index, str(index_path))

        # SECURITY FIX: Save ID mapping as JSON (safe serialization)
        id_map_path = index_path.with_suffix(".id_map.json")
        with open(id_map_path, "w", encoding="utf-8") as f:
            json.dump(self.id_map, f)

        logger.info(f"Saved FAISS index to {index_path}")

    async def load_index(self, index_path: Path | None = None) -> bool:
        """
        Load FAISS index from disk.

        Args:
            index_path: Path to load index from

        Returns:
            True if loaded successfully, False otherwise
        """
        if index_path is None:
            index_path = Path("data/faiss_index.bin")

        if not index_path.exists():
            logger.info("No saved index found")
            return False

        try:
            # Load FAISS index
            self.index = faiss.read_index(str(index_path))

            # SECURITY FIX: Load ID mapping from JSON (safe deserialization)
            id_map_path = index_path.with_suffix(".id_map.json")

            # Check for legacy unsafe format and reject it
            legacy_path = index_path.with_suffix(".id_map")
            if legacy_path.exists() and not id_map_path.exists():
                logger.error(
                    "Legacy unsafe index format detected. "
                    "Please rebuild index with: await search.build_index(force_rebuild=True)"
                )
                return False

            with open(id_map_path, "r", encoding="utf-8") as f:
                self.id_map = json.load(f)

            # Set search parameters
            if self.index_type == "IVFFlat":
                self.index.nprobe = self.nprobe

            logger.info(
                f"Loaded FAISS index from {index_path}",
                embeddings_count=len(self.id_map),
            )

            return True

        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False

    def get_index_stats(self) -> dict[str, Any]:
        """
        Get statistics about the FAISS index.

        Returns:
            Dict with index statistics
        """
        if self.index is None:
            return {"built": False}

        return {
            "built": True,
            "index_type": self.index_type,
            "dimension": self.dimension,
            "embeddings_count": len(self.id_map),
            "total_vectors": self.index.ntotal,
            "is_trained": self.index.is_trained if hasattr(self.index, "is_trained") else True,
        }


# Global instance
_faiss_search: FAISSSemanticSearch | None = None


def get_faiss_search(db_path: Path) -> FAISSSemanticSearch:
    """
    Get or create FAISS search instance.

    Args:
        db_path: Path to chat memory database

    Returns:
        FAISSSemanticSearch instance
    """
    global _faiss_search

    if _faiss_search is None:
        _faiss_search = FAISSSemanticSearch(db_path)

    return _faiss_search
