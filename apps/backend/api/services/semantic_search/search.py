"""
Search functionality for semantic search
"""
import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

import numpy as np

from api.config.constants import CACHE_TTL_SHORT
from api.services.cache_service import get_cache
from api.utils.structured_logging import get_logger

from .models import SearchConfig, SemanticSearchResult
from .reranker import get_cross_encoder_reranker
from .utils import _cosine_similarity, _create_snippet

logger = get_logger(__name__)
cache = get_cache()

# Check if FAISS is available for 10-100x faster search
try:
    from api.services.faiss_search import FAISSSemanticSearch, FAISS_AVAILABLE

    if FAISS_AVAILABLE:
        logger.info("FAISS available - will use for accelerated search")
except ImportError:
    FAISS_AVAILABLE = False
    logger.info("FAISS not available - using brute-force search")


class SearchManager:
    """Manages semantic search operations with optional FAISS acceleration"""

    def __init__(self, db_path: Path):
        """
        Initialize search manager

        Args:
            db_path: Path to chat memory database
        """
        self.db_path = db_path
        self._local = threading.local()
        self._faiss_search = None  # Lazy-loaded FAISS search
        self._faiss_initialized = False

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path), check_same_thread=True, timeout=30.0
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            logger.debug(f"Created new DB connection for thread {threading.current_thread().name}")
        return self._local.conn

    async def search(
        self,
        query: str,
        query_embedding: list[float],
        config: SearchConfig | None = None,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> list[SemanticSearchResult]:
        """
        Semantic search across conversation history (cached)

        Args:
            query: Search query
            query_embedding: Pre-generated query embedding
            config: Search configuration
            user_id: Filter by user ID
            team_id: Filter by team ID

        Returns:
            List of search results ordered by relevance
        """
        if config is None:
            config = SearchConfig()

        # Create cache key from query + config + filters
        cache_params = {
            "query": query,
            "top_k": config.top_k,
            "threshold": config.similarity_threshold,
            "user_id": user_id,
            "team_id": team_id,
        }
        cache_hash = hashlib.md5(json.dumps(cache_params, sort_keys=True).encode()).hexdigest()
        cache_key = f"search:{cache_hash}"

        # Try cache first (5 minute TTL for search results)
        cached = await cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for search: {query[:30]}...")
            # Convert dicts back to SemanticSearchResult objects
            return [SemanticSearchResult(**r) for r in cached]

        # Try FAISS search if available (10-100x faster!)
        if FAISS_AVAILABLE and await self._try_faiss_search():
            try:
                results = await self._search_with_faiss(
                    query=query,
                    config=config,
                    user_id=user_id,
                    team_id=team_id,
                )
                if results:
                    logger.debug(f"FAISS search returned {len(results)} results")
                    # Cache results
                    await cache.set(
                        cache_key, [r.__dict__ for r in results], ttl=CACHE_TTL_SHORT
                    )
                    return results[:config.top_k]
            except Exception as e:
                logger.warning(f"FAISS search failed, falling back to brute-force: {e}")
                # Fall through to brute-force search

        # Fallback: Convert query embedding to numpy array
        query_embedding_np = np.array(query_embedding)

        # Retrieve candidates from database (brute-force)
        candidates = await self._retrieve_candidates(
            query=query, user_id=user_id, team_id=team_id, use_hybrid=config.use_hybrid
        )

        if not candidates:
            logger.info("No candidates found for search")
            return []

        # Calculate similarities
        results = []
        for candidate in candidates:
            embedding_json = candidate["embedding_json"]
            if not embedding_json:
                continue

            candidate_embedding = np.array(json.loads(embedding_json))
            similarity = _cosine_similarity(query_embedding_np, candidate_embedding)

            if similarity >= config.similarity_threshold:
                snippet = _create_snippet(
                    candidate["content"], query, config.max_snippet_length
                )

                results.append(
                    SemanticSearchResult(
                        session_id=candidate["session_id"],
                        session_title=(candidate.get("session_title", None)),
                        message_id=candidate["message_id"],
                        role=candidate["role"],
                        content=candidate["content"],
                        timestamp=candidate["timestamp"],
                        model=candidate.get("model", None),
                        similarity=float(similarity),
                        snippet=snippet,
                    )
                )

        # Sort by similarity
        results.sort(key=lambda x: x.similarity, reverse=True)

        # Re-rank if enabled
        if config.rerank and len(results) > 0:
            results = await self._rerank_results(query, results, config.top_k)

        # Get top-k results
        top_results = results[: config.top_k]

        # Cache results (convert to dicts for JSON serialization)
        cacheable_results = [
            {
                "session_id": r.session_id,
                "session_title": r.session_title,
                "message_id": r.message_id,
                "role": r.role,
                "content": r.content,
                "timestamp": r.timestamp,
                "model": r.model,
                "similarity": r.similarity,
                "snippet": r.snippet,
            }
            for r in top_results
        ]
        await cache.set(cache_key, cacheable_results, ttl=CACHE_TTL_SHORT)

        return top_results

    async def _retrieve_candidates(
        self,
        query: str,
        user_id: str | None,
        team_id: str | None,
        use_hybrid: bool = True,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """
        Retrieve candidate messages for search

        Args:
            query: Search query
            user_id: Filter by user ID
            team_id: Filter by team ID
            use_hybrid: Use hybrid search (semantic + keyword)
            limit: Maximum candidates to retrieve

        Returns:
            List of candidate messages with embeddings
        """
        conn = self._get_connection()

        # Build query based on filters
        base_query = """
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
            WHERE e.embedding_json IS NOT NULL
        """

        params = []

        # Add filters
        if team_id:
            base_query += " AND m.team_id = ?"
            params.append(team_id)
        elif user_id:
            base_query += " AND m.user_id = ? AND m.team_id IS NULL"
            params.append(user_id)

        # Hybrid search: also filter by keyword relevance
        if use_hybrid:
            # Add keyword filter (messages containing any query term)
            query_terms = query.lower().split()
            keyword_conditions = " OR ".join(["LOWER(m.content) LIKE ?" for _ in query_terms])
            base_query += f" AND ({keyword_conditions})"
            params.extend([f"%{term}%" for term in query_terms])

        # Order by timestamp (recent first) and limit
        base_query += " ORDER BY m.timestamp DESC LIMIT ?"
        params.append(limit)

        cur = conn.execute(base_query, params)
        return [dict(row) for row in cur.fetchall()]

    async def _rerank_results(
        self, query: str, results: list[SemanticSearchResult], top_k: int
    ) -> list[SemanticSearchResult]:
        """
        Re-rank results using cross-encoder for better relevance.

        Cross-encoders are more accurate than bi-encoders because they
        jointly encode query-document pairs, enabling cross-attention.
        This is 10-100x slower than bi-encoders but significantly more accurate.

        We use it only for re-ranking top candidates (typically 2*top_k).
        """
        if not results:
            return results

        # Only re-rank if we have enough results
        candidates = results[:top_k * 2]

        try:
            reranker = get_cross_encoder_reranker()
            if reranker is None:
                logger.debug("Cross-encoder not available, skipping re-ranking")
                return results

            # Re-rank candidates
            reranked = await reranker.rerank(query, candidates, top_k)
            logger.debug(f"Cross-encoder re-ranked {len(candidates)} -> {len(reranked)} results")

            return reranked

        except Exception as e:
            logger.warning(f"Cross-encoder re-ranking failed: {e}")
            return results

    async def search_similar_messages(
        self,
        session_id: str,
        message_id: int,
        top_k: int = 5,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> list[SemanticSearchResult]:
        """
        Find messages similar to a given message

        Args:
            session_id: Session ID
            message_id: Message ID to find similar to
            top_k: Number of similar messages to return
            user_id: Filter by user ID
            team_id: Filter by team ID

        Returns:
            List of similar messages
        """
        conn = self._get_connection()

        # Get source message embedding
        cur = conn.execute(
            """
            SELECT embedding_json
            FROM message_embeddings
            WHERE message_id = ? AND session_id = ?
        """,
            (message_id, session_id),
        )

        row = cur.fetchone()
        if not row or not row["embedding_json"]:
            logger.warning(f"No embedding found for message {message_id}")
            return []

        source_embedding = np.array(json.loads(row["embedding_json"]))

        # Retrieve all candidate embeddings
        candidates = await self._retrieve_candidates(
            query="",  # No query filter
            user_id=user_id,
            team_id=team_id,
            use_hybrid=False,  # Pure semantic search
            limit=500,
        )

        # Calculate similarities
        results = []
        for candidate in candidates:
            # Skip the source message itself
            if candidate["message_id"] == message_id:
                continue

            if not candidate["embedding_json"]:
                continue

            candidate_embedding = np.array(json.loads(candidate["embedding_json"]))
            similarity = _cosine_similarity(source_embedding, candidate_embedding)

            if similarity > 0.3:  # Threshold
                results.append(
                    SemanticSearchResult(
                        session_id=candidate["session_id"],
                        session_title=(candidate.get("session_title", None)),
                        message_id=candidate["message_id"],
                        role=candidate["role"],
                        content=candidate["content"],
                        timestamp=candidate["timestamp"],
                        model=candidate.get("model", None),
                        similarity=float(similarity),
                        snippet=candidate["content"][:200],
                    )
                )

        # Sort by similarity
        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]

    async def _try_faiss_search(self) -> bool:
        """
        Check if FAISS search is available and initialized.

        Returns:
            True if FAISS can be used, False otherwise
        """
        if not FAISS_AVAILABLE:
            return False

        if self._faiss_initialized:
            return self._faiss_search is not None

        # Lazy-load FAISS search
        try:
            from api.services.faiss_search import FAISSSemanticSearch

            self._faiss_search = FAISSSemanticSearch(self.db_path)

            # Check if index exists or try to build it
            if not self._faiss_search.index:
                logger.info("FAISS index not found, building from existing embeddings...")
                await self._faiss_search.build_index()

            self._faiss_initialized = True
            return self._faiss_search.index is not None
        except Exception as e:
            logger.warning(f"Failed to initialize FAISS search: {e}")
            self._faiss_initialized = True  # Don't try again
            return False

    async def _search_with_faiss(
        self,
        query: str,
        config: SearchConfig,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> list[SemanticSearchResult]:
        """
        Perform search using FAISS acceleration.

        Args:
            query: Search query
            config: Search configuration
            user_id: Filter by user ID
            team_id: Filter by team ID

        Returns:
            List of search results
        """
        if not self._faiss_search:
            return []

        # FAISS search returns FAISSSearchResult objects
        faiss_results = await self._faiss_search.search(
            query=query,
            top_k=config.top_k,
            similarity_threshold=config.similarity_threshold,
            user_id=user_id,
            team_id=team_id,
        )

        # Convert to SemanticSearchResult
        results = []
        for fr in faiss_results:
            snippet = _create_snippet(fr.content, query, config.max_snippet_length)
            results.append(
                SemanticSearchResult(
                    session_id=fr.session_id,
                    session_title=fr.session_title,
                    message_id=fr.message_id,
                    role=fr.role,
                    content=fr.content,
                    timestamp=fr.timestamp,
                    model=fr.model,
                    similarity=fr.similarity,
                    snippet=snippet,
                )
            )

        return results
