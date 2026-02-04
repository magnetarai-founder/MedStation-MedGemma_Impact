#!/usr/bin/env python3
"""
MPS-Accelerated Embeddings

Uses Metal Performance Shaders for GPU-accelerated embedding generation.
Falls back to CPU if MPS is not available.

Features:
- Metal GPU acceleration on Apple Silicon
- Batch processing for throughput
- Caching of embeddings
- Multiple model support
- Automatic device selection
"""

import asyncio
import hashlib
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from api.utils.structured_logging import get_logger

logger = get_logger(__name__)

# Check MPS availability
MPS_AVAILABLE = False
_device = "cpu"

try:
    import torch

    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        MPS_AVAILABLE = True
        _device = "mps"
        logger.info("MPS (Metal Performance Shaders) available for embeddings")
    elif torch.cuda.is_available():
        _device = "cuda"
        logger.info("CUDA available for embeddings")
    else:
        logger.info("Using CPU for embeddings (MPS/CUDA not available)")
except ImportError:
    logger.info("PyTorch not available - using CPU embeddings")


def is_mps_available() -> bool:
    """Check if MPS acceleration is available."""
    return MPS_AVAILABLE


@dataclass
class EmbeddingConfig:
    """Configuration for embedding model."""

    model_name: str = "all-MiniLM-L6-v2"
    device: str | None = None  # Auto-detect if None
    batch_size: int = 32
    max_seq_length: int = 512
    normalize: bool = True
    cache_embeddings: bool = True
    cache_dir: Path | None = None

    def __post_init__(self):
        if self.device is None:
            self.device = _device
        if self.cache_dir is None:
            self.cache_dir = Path("~/.magnetarcode/embeddings_cache").expanduser()
            self.cache_dir.mkdir(parents=True, exist_ok=True)


class MPSEmbeddingModel:
    """
    GPU-accelerated embedding model using MPS or CUDA.

    Provides significant speedup over CPU-only embeddings:
    - MPS (Apple Silicon): 5-20x faster
    - CUDA: 10-50x faster

    Usage:
        model = MPSEmbeddingModel()
        embeddings = await model.embed_batch(["Hello", "World"])
    """

    # Available models with dimensions
    MODELS = {
        "all-MiniLM-L6-v2": 384,  # Fast, good quality
        "all-MiniLM-L12-v2": 384,  # Better quality
        "all-mpnet-base-v2": 768,  # Best quality
        "paraphrase-MiniLM-L6-v2": 384,  # Good for paraphrasing
        "multi-qa-MiniLM-L6-cos-v1": 384,  # Good for Q&A
    }

    def __init__(self, config: EmbeddingConfig | None = None):
        """
        Initialize embedding model.

        Args:
            config: Embedding configuration
        """
        self.config = config or EmbeddingConfig()
        self._model = None
        self._loaded = False
        self._load_lock = asyncio.Lock()

        # Simple in-memory cache
        self._cache: dict[str, np.ndarray] = {}
        self._cache_max_size = 10000

        # Stats
        self._embeddings_generated = 0
        self._cache_hits = 0
        self._total_time = 0.0

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self.MODELS.get(self.config.model_name, 384)

    async def _ensure_loaded(self) -> None:
        """Ensure model is loaded."""
        async with self._load_lock:
            if self._loaded:
                return

            logger.info(
                f"Loading embedding model: {self.config.model_name} "
                f"on device: {self.config.device}"
            )
            start = time.perf_counter()

            # Load in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._load_model)

            elapsed = (time.perf_counter() - start) * 1000
            logger.info(f"Embedding model loaded in {elapsed:.0f}ms")
            self._loaded = True

    def _load_model(self) -> None:
        """Load the model (blocking)."""
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                self.config.model_name,
                device=self.config.device,
            )

            # Set max sequence length
            self._model.max_seq_length = self.config.max_seq_length

        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def _cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(text.encode()).hexdigest()

    def _get_from_cache(self, text: str) -> np.ndarray | None:
        """Get embedding from cache."""
        if not self.config.cache_embeddings:
            return None

        key = self._cache_key(text)
        if key in self._cache:
            self._cache_hits += 1
            return self._cache[key]
        return None

    def _add_to_cache(self, text: str, embedding: np.ndarray) -> None:
        """Add embedding to cache."""
        if not self.config.cache_embeddings:
            return

        # Simple LRU-like cleanup
        if len(self._cache) >= self._cache_max_size:
            # Remove first 10% of entries
            keys_to_remove = list(self._cache.keys())[: self._cache_max_size // 10]
            for key in keys_to_remove:
                del self._cache[key]

        self._cache[self._cache_key(text)] = embedding

    async def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding as numpy array
        """
        # Check cache
        cached = self._get_from_cache(text)
        if cached is not None:
            return cached

        await self._ensure_loaded()

        start = time.perf_counter()

        # Generate embedding
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            lambda: self._model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=self.config.normalize,
            ),
        )

        elapsed = time.perf_counter() - start
        self._embeddings_generated += 1
        self._total_time += elapsed

        # Cache result
        self._add_to_cache(text, embedding)

        return embedding

    async def embed_batch(
        self,
        texts: Sequence[str],
        show_progress: bool = False,
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts
            show_progress: Show progress bar

        Returns:
            Embeddings as 2D numpy array (n_texts x dimension)
        """
        if not texts:
            return np.array([])

        await self._ensure_loaded()

        # Check cache for each text
        embeddings = []
        texts_to_embed = []
        indices_to_embed = []

        for i, text in enumerate(texts):
            cached = self._get_from_cache(text)
            if cached is not None:
                embeddings.append((i, cached))
            else:
                texts_to_embed.append(text)
                indices_to_embed.append(i)

        # Generate embeddings for uncached texts
        if texts_to_embed:
            start = time.perf_counter()

            loop = asyncio.get_event_loop()
            new_embeddings = await loop.run_in_executor(
                None,
                lambda: self._model.encode(
                    texts_to_embed,
                    batch_size=self.config.batch_size,
                    convert_to_numpy=True,
                    normalize_embeddings=self.config.normalize,
                    show_progress_bar=show_progress,
                ),
            )

            elapsed = time.perf_counter() - start
            self._embeddings_generated += len(texts_to_embed)
            self._total_time += elapsed

            # Add to cache and results
            for idx, text, emb in zip(
                indices_to_embed, texts_to_embed, new_embeddings
            ):
                self._add_to_cache(text, emb)
                embeddings.append((idx, emb))

        # Sort by original index and stack
        embeddings.sort(key=lambda x: x[0])
        return np.vstack([emb for _, emb in embeddings])

    async def similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Cosine similarity (0-1)
        """
        embeddings = await self.embed_batch([text1, text2])
        return float(np.dot(embeddings[0], embeddings[1]))

    async def find_similar(
        self,
        query: str,
        candidates: Sequence[str],
        top_k: int = 5,
    ) -> list[tuple[str, float]]:
        """
        Find most similar texts to query.

        Args:
            query: Query text
            candidates: Candidate texts to search
            top_k: Number of results

        Returns:
            List of (text, similarity) tuples
        """
        if not candidates:
            return []

        # Embed query and candidates
        all_texts = [query] + list(candidates)
        embeddings = await self.embed_batch(all_texts)

        query_emb = embeddings[0]
        candidate_embs = embeddings[1:]

        # Compute similarities
        similarities = np.dot(candidate_embs, query_emb)

        # Get top-k
        top_indices = np.argsort(similarities)[::-1][:top_k]

        return [(candidates[i], float(similarities[i])) for i in top_indices]

    def get_stats(self) -> dict[str, Any]:
        """Get embedding statistics."""
        avg_time = (
            self._total_time / self._embeddings_generated
            if self._embeddings_generated > 0
            else 0
        )

        cache_hit_rate = (
            self._cache_hits / (self._cache_hits + self._embeddings_generated)
            if (self._cache_hits + self._embeddings_generated) > 0
            else 0
        )

        return {
            "model": self.config.model_name,
            "device": self.config.device,
            "dimension": self.dimension,
            "mps_available": MPS_AVAILABLE,
            "loaded": self._loaded,
            "embeddings_generated": self._embeddings_generated,
            "cache_hits": self._cache_hits,
            "cache_hit_rate": round(cache_hit_rate * 100, 1),
            "cache_size": len(self._cache),
            "avg_time_per_embedding_ms": round(avg_time * 1000, 2),
        }

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._cache.clear()
        logger.info("Embedding cache cleared")


# Global instance
_mps_embeddings: MPSEmbeddingModel | None = None


def get_mps_embeddings(config: EmbeddingConfig | None = None) -> MPSEmbeddingModel:
    """Get or create global MPS embedding model."""
    global _mps_embeddings

    if _mps_embeddings is None:
        _mps_embeddings = MPSEmbeddingModel(config)

    return _mps_embeddings
