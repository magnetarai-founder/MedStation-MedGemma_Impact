"""
Context Retriever

Combines vector and full-text search for hybrid retrieval.
Implements RAG (Retrieval Augmented Generation) pipeline.
"""

from typing import Any

from .indexer import FullTextIndexer, VectorIndexer


class ContextRetriever:
    """
    Hybrid context retriever combining semantic and keyword search.

    Uses reciprocal rank fusion (RRF) to combine results from:
    - Vector search (semantic similarity)
    - Full-text search (keyword matching)
    """

    def __init__(self, db_path: str = "context.db"):
        """
        Initialize retriever.

        Args:
            db_path: Path to SQLite database
        """
        self.vector_indexer = VectorIndexer(db_path=db_path)
        self.fts_indexer = FullTextIndexer(db_path=db_path)

    def search(
        self,
        query: str,
        top_k: int = 5,
        source_filter: str | None = None,
        use_hybrid: bool = True,
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4,
    ) -> list[dict[str, Any]]:
        """
        Search for relevant context using hybrid retrieval.

        Args:
            query: Search query
            top_k: Number of results to return
            source_filter: Optional source filter
            use_hybrid: Use both semantic and keyword search
            semantic_weight: Weight for semantic search (0-1)
            keyword_weight: Weight for keyword search (0-1)

        Returns:
            List of results ranked by relevance
        """
        if not use_hybrid:
            # Use only vector search
            return self.vector_indexer.search(query, top_k, source_filter)

        # Get results from both methods
        semantic_results = self.vector_indexer.search(query, top_k * 2, source_filter)
        keyword_results = self.fts_indexer.search(query, top_k * 2, source_filter)

        # Combine using reciprocal rank fusion
        combined = self._reciprocal_rank_fusion(
            semantic_results, keyword_results, semantic_weight, keyword_weight
        )

        return combined[:top_k]

    def _reciprocal_rank_fusion(
        self,
        semantic_results: list[dict[str, Any]],
        keyword_results: list[dict[str, Any]],
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4,
        k: int = 60,  # RRF constant
    ) -> list[dict[str, Any]]:
        """
        Combine results using reciprocal rank fusion.

        Args:
            semantic_results: Results from vector search
            keyword_results: Results from full-text search
            semantic_weight: Weight for semantic results
            keyword_weight: Weight for keyword results
            k: RRF constant (typically 60)

        Returns:
            Combined and re-ranked results
        """
        # Build rank maps
        semantic_ranks = {r["id"]: i for i, r in enumerate(semantic_results)}
        keyword_ranks = {r["id"]: i for i, r in enumerate(keyword_results)}

        # Get all unique document IDs
        all_ids = set(semantic_ranks.keys()) | set(keyword_ranks.keys())

        # Calculate RRF scores
        rrf_scores = {}
        for doc_id in all_ids:
            score = 0.0

            # Add semantic score
            if doc_id in semantic_ranks:
                rank = semantic_ranks[doc_id]
                score += semantic_weight * (1.0 / (k + rank + 1))

            # Add keyword score
            if doc_id in keyword_ranks:
                rank = keyword_ranks[doc_id]
                score += keyword_weight * (1.0 / (k + rank + 1))

            rrf_scores[doc_id] = score

        # Build result list with combined scores
        results = []
        doc_map = {}

        for r in semantic_results:
            doc_map[r["id"]] = r

        for r in keyword_results:
            if r["id"] not in doc_map:
                doc_map[r["id"]] = r

        for doc_id, score in rrf_scores.items():
            result = doc_map[doc_id].copy()
            result["score"] = score
            result["search_method"] = self._get_search_method(doc_id, semantic_ranks, keyword_ranks)
            results.append(result)

        # Sort by RRF score (highest first)
        results.sort(key=lambda x: x["score"], reverse=True)

        return results

    def _get_search_method(
        self, doc_id: str, semantic_ranks: dict[str, int], keyword_ranks: dict[str, int]
    ) -> str:
        """Determine which search method found the document"""
        in_semantic = doc_id in semantic_ranks
        in_keyword = doc_id in keyword_ranks

        if in_semantic and in_keyword:
            return "hybrid"
        elif in_semantic:
            return "semantic"
        else:
            return "keyword"

    def search_semantic(
        self, query: str, top_k: int = 5, source_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """Search using only semantic (vector) search"""
        return self.vector_indexer.search(query, top_k, source_filter)

    def search_keyword(
        self, query: str, top_k: int = 5, source_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """Search using only keyword (full-text) search"""
        return self.fts_indexer.search(query, top_k, source_filter)

    def format_context(
        self, results: list[dict[str, Any]], max_tokens: int = 4000, include_metadata: bool = False
    ) -> str:
        """
        Format search results as context for LLM.

        Args:
            results: Search results
            max_tokens: Approximate token limit
            include_metadata: Include source and metadata

        Returns:
            Formatted context string
        """
        context_parts = []
        total_chars = 0
        char_limit = max_tokens * 4  # Rough estimate: 1 token ≈ 4 chars

        for i, result in enumerate(results, 1):
            # Build context piece
            parts = []

            if include_metadata:
                parts.append(f"### Result {i} (score: {result['score']:.3f})")
                parts.append(f"**Source:** `{result['source']}`")

                if result.get("metadata"):
                    metadata = result["metadata"]
                    if "path" in metadata:
                        parts.append(f"**Path:** `{metadata['path']}`")
                    if "language" in metadata:
                        parts.append(f"**Language:** {metadata['language']}")

            parts.append(result["content"])
            parts.append("")  # Empty line separator

            piece = "\n".join(parts)
            piece_len = len(piece)

            # Check if adding this would exceed limit
            if total_chars + piece_len > char_limit and context_parts:
                break

            context_parts.append(piece)
            total_chars += piece_len

        return "\n".join(context_parts)
