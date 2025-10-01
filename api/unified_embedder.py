#!/usr/bin/env python3
"""
Unified Embedding System for NeutronStar
Consolidates all embedding backends with hardware acceleration support
Adapted from Jarvis Agent implementation
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)


class UnifiedEmbedder:
    """
    Unified interface for all embedding backends
    Automatically selects best available backend:
    1. MLX (Metal + ANE) - Best performance on Apple Silicon
    2. Ollama - Local model server
    3. Hash - Lightweight fallback
    """

    def __init__(self, backend: Optional[str] = None):
        self.available_backends = ['mlx', 'ollama', 'hash']
        self.mlx_available = False
        self.metal_available = False
        self.ane_available = False
        self._embedder = None
        self._initialized = False
        self.backend = backend or self._get_backend()

    def _get_backend(self) -> str:
        """Automatically select best embedding backend"""
        # Check environment override
        backend = os.getenv('NEUTRON_EMBED_BACKEND', '').lower()
        if backend in self.available_backends:
            return backend

        # Auto-detect: prefer MLX on macOS
        try:
            import mlx
            import platform
            if platform.system() == 'Darwin':  # macOS
                logger.info("Detected macOS with MLX - using hardware acceleration")
                return 'mlx'
        except ImportError:
            pass

        # Fall back to Ollama if available
        try:
            import urllib.request
            req = urllib.request.Request('http://127.0.0.1:11434/api/tags')
            with urllib.request.urlopen(req, timeout=1):
                logger.info("Detected Ollama - using local model server")
                return 'ollama'
        except:
            pass

        # Final fallback
        logger.info("Using hash embedding fallback")
        return 'hash'

    def initialize(self) -> bool:
        """Initialize the embedding backend"""
        if self._initialized:
            return True

        logger.info(f"🚀 Initializing {self.backend.upper()} embedding backend")

        if self.backend == 'mlx':
            return self._initialize_mlx()
        elif self.backend == 'ollama':
            return self._initialize_ollama()
        else:  # hash
            self._initialized = True
            return True

    def _initialize_mlx(self) -> bool:
        """Initialize MLX backend (Metal + ANE)"""
        try:
            from api.mlx_embedder import get_mlx_embedder, validate_mlx_setup

            # Validate setup
            status = validate_mlx_setup()

            if status['mlx_available']:
                self._embedder = get_mlx_embedder()

                if self._embedder.initialize():
                    self._initialized = True
                    self.mlx_available = True
                    self.metal_available = status.get('metal_available', False)
                    self.ane_available = status.get('ane_available', False)

                    logger.info("✅ MLX embedder initialized")
                    logger.info(f"   Metal: {'✓' if self.metal_available else '✗'}")
                    logger.info(f"   ANE: {'✓' if self.ane_available else '✗'}")
                    logger.info(f"   Dimension: {status.get('embedding_dim', 'unknown')}")
                    return True

            logger.warning("MLX initialization failed, falling back to hash")
            self.backend = 'hash'
            self._initialized = True
            return True

        except Exception as e:
            logger.warning(f"MLX backend error: {e}")
            self.backend = 'hash'
            self._initialized = True
            return True

    def _initialize_ollama(self) -> bool:
        """Initialize Ollama backend"""
        try:
            import urllib.request

            # Test connection
            req = urllib.request.Request('http://127.0.0.1:11434/api/tags')
            with urllib.request.urlopen(req, timeout=2):
                self._initialized = True
                logger.info("✅ Ollama embedder initialized")
                return True

        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            logger.info("Falling back to hash embedding")
            self.backend = 'hash'
            self._initialized = True
            return True

    def embed(self, text: str) -> List[float]:
        """Embed a single text"""
        if not self._initialized:
            self.initialize()

        if self.backend == 'mlx' and self._embedder:
            try:
                return self._embedder.embed_single(text)
            except Exception as e:
                logger.warning(f"MLX embedding failed: {e}")

        elif self.backend == 'ollama':
            embedding = self._embed_ollama(text)
            if embedding:
                return embedding

        # Fallback to hash
        return self._embed_hash(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts efficiently"""
        if not self._initialized:
            self.initialize()

        if self.backend == 'mlx' and self._embedder:
            try:
                embeddings = self._embedder.encode(texts)
                return [emb.tolist() for emb in embeddings]
            except Exception as e:
                logger.warning(f"MLX batch embedding failed: {e}")

        # Fall back to sequential embedding
        return [self.embed(text) for text in texts]

    def _embed_ollama(self, text: str, model: str = "nomic-embed-text") -> Optional[List[float]]:
        """Embed using Ollama API"""
        try:
            import urllib.request

            payload = json.dumps({
                'model': model,
                'prompt': text
            }).encode('utf-8')

            req = urllib.request.Request(
                url='http://127.0.0.1:11434/api/embeddings',
                data=payload,
                headers={'Content-Type': 'application/json'}
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read())
                return data.get('embedding', [])

        except Exception as e:
            logger.debug(f"Ollama embedding failed: {e}")
            return None

    def _embed_hash(self, text: str, dim: int = 384) -> List[float]:
        """
        Lightweight hash-based embedding fallback
        Fast, deterministic, and works everywhere
        """
        import hashlib

        # Generate hash-based features
        hashes = []
        for i in range((dim + 15) // 16):  # Each MD5 gives 16 bytes
            h = hashlib.md5(f"{text}_{i}".encode()).digest()
            hashes.extend(int.from_bytes(h[j:j+2], 'big') for j in range(0, 16, 2))

        # Normalize to [-1, 1] range
        vec = [(h / 32768.0 - 1.0) for h in hashes[:dim]]

        # L2 normalize
        norm = sum(x*x for x in vec) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]

        return vec

    def get_info(self) -> Dict[str, Any]:
        """Get backend information"""
        return {
            'backend': self.backend,
            'initialized': self._initialized,
            'mlx_available': self.mlx_available,
            'metal_available': self.metal_available,
            'ane_available': self.ane_available,
            'embedding_dim': 384 if self.backend == 'hash' else (
                self._embedder.get_embedding_dim() if self._embedder else 384
            )
        }


# Singleton instance
_unified_embedder: Optional[UnifiedEmbedder] = None


def get_embedder(backend: Optional[str] = None) -> UnifiedEmbedder:
    """Get singleton embedder instance"""
    global _unified_embedder
    if _unified_embedder is None:
        _unified_embedder = UnifiedEmbedder(backend)
    return _unified_embedder


def embed_text(text: str) -> List[float]:
    """Convenient function to embed text"""
    return get_embedder().embed(text)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Convenient function to embed multiple texts"""
    return get_embedder().embed_batch(texts)


def get_backend_info() -> Dict[str, Any]:
    """Get information about current embedding backend"""
    return get_embedder().get_info()
