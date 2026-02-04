"""
Cross-Encoder Re-ranking

Uses cross-encoder models for more accurate relevance scoring.
Cross-encoders jointly encode query-document pairs, enabling
cross-attention which is more accurate than bi-encoder similarity.

Trade-off: 10-100x slower than bi-encoders, so only used for
re-ranking top candidates.
"""

import asyncio
import logging
import os
from typing import Any

from .models import SemanticSearchResult

logger = logging.getLogger(__name__)

# Check if cross-encoder is available
CROSS_ENCODER_AVAILABLE = False
_cross_encoder = None

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
    logger.info("CrossEncoder available for re-ranking")
except ImportError:
    logger.info("sentence-transformers not available - cross-encoder re-ranking disabled")


class CrossEncoderReranker:
    """
    Re-ranks search results using a cross-encoder model.

    Cross-encoders are more accurate because they:
    1. Jointly encode query and document together
    2. Allow cross-attention between query and document tokens
    3. Produce a relevance score directly (not via similarity)

    This is 10-100x slower than bi-encoder similarity but much more accurate.
    """

    # Default model - small but effective
    DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
    ):
        """
        Initialize cross-encoder reranker.

        Args:
            model_name: HuggingFace model name for cross-encoder
            device: Device to run on ('cpu', 'cuda', 'mps')
        """
        if not CROSS_ENCODER_AVAILABLE:
            raise ImportError("sentence-transformers required for cross-encoder re-ranking")

        self._model_name = model_name or os.getenv(
            "CROSS_ENCODER_MODEL", self.DEFAULT_MODEL
        )

        # Determine device
        if device is None:
            device = os.getenv("RERANKER_DEVICE", "cpu")
            # Auto-detect best device
            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
                elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    device = "mps"
            except ImportError:
                pass

        self._device = device

        # Lazy load model
        self._model: Any = None
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Ensure model is loaded."""
        if self._loaded:
            return

        logger.info(f"Loading cross-encoder model: {self._model_name}")
        self._model = CrossEncoder(self._model_name, device=self._device)
        self._loaded = True
        logger.info(f"Cross-encoder loaded on device: {self._device}")

    async def rerank(
        self,
        query: str,
        results: list[SemanticSearchResult],
        top_k: int,
    ) -> list[SemanticSearchResult]:
        """
        Re-rank results using cross-encoder.

        Args:
            query: Search query
            results: Results to re-rank
            top_k: Number of results to return

        Returns:
            Re-ranked results
        """
        if not results:
            return results

        # Load model if needed
        self._ensure_loaded()

        # Create query-document pairs
        pairs = [[query, result.content] for result in results]

        # Run prediction in thread pool (blocking operation)
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(
            None,
            lambda: self._model.predict(pairs, show_progress_bar=False)
        )

        # Pair scores with results
        scored_results = list(zip(scores, results))

        # Sort by cross-encoder score (higher is better)
        scored_results.sort(key=lambda x: x[0], reverse=True)

        # Update similarity scores and return top-k
        reranked = []
        for score, result in scored_results[:top_k]:
            # Create new result with updated similarity
            reranked.append(SemanticSearchResult(
                session_id=result.session_id,
                session_title=result.session_title,
                message_id=result.message_id,
                role=result.role,
                content=result.content,
                timestamp=result.timestamp,
                model=result.model,
                similarity=float(score),  # Cross-encoder score
                snippet=result.snippet,
            ))

        return reranked

    async def score_pair(self, query: str, document: str) -> float:
        """
        Score a single query-document pair.

        Args:
            query: Search query
            document: Document content

        Returns:
            Relevance score (higher is more relevant)
        """
        self._ensure_loaded()

        loop = asyncio.get_event_loop()
        score = await loop.run_in_executor(
            None,
            lambda: self._model.predict([[query, document]], show_progress_bar=False)[0]
        )

        return float(score)

    def get_stats(self) -> dict[str, Any]:
        """Get reranker statistics."""
        return {
            "model": self._model_name,
            "device": self._device,
            "loaded": self._loaded,
            "available": CROSS_ENCODER_AVAILABLE,
        }


# Global instance
_reranker: CrossEncoderReranker | None = None


def get_cross_encoder_reranker() -> CrossEncoderReranker | None:
    """
    Get or create global cross-encoder reranker.

    Returns None if cross-encoder is not available.
    """
    global _reranker

    if not CROSS_ENCODER_AVAILABLE:
        return None

    if _reranker is None:
        try:
            _reranker = CrossEncoderReranker()
        except Exception as e:
            logger.warning(f"Failed to create cross-encoder reranker: {e}")
            return None

    return _reranker


def is_reranking_available() -> bool:
    """Check if re-ranking is available."""
    return CROSS_ENCODER_AVAILABLE
