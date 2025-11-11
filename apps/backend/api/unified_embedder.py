#!/usr/bin/env python3
"""
Unified Embedding System for Jarvis
Consolidates all embedding backends into a single interface
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)


class UnifiedEmbedder:
    """Unified interface for all embedding backends"""
    
    def __init__(self):
        self.backend = self._get_backend()
        self._embedder = None
        self._initialized = False
        self.available_backends = ['mlx', 'ollama', 'sentence-transformers', 'hash']
        self.mlx_available = False  # Will be set during initialization
        self.model_name = None  # Will be set during initialization
        
    def _get_backend(self) -> str:
        """Get configured embedding backend"""
        # Check environment
        backend = os.getenv('JARVIS_EMBED_BACKEND', '').lower()
        if backend in ['mlx', 'ollama', 'sentence-transformers', 'hash']:
            return backend
            
        # Check config
        try:
            cfg_path = Path(os.getenv('JARVIS_HOME', str(Path.home()/'.ai_agent'))).expanduser() / 'config.json'
            if cfg_path.exists():
                data = json.loads(cfg_path.read_text())
                backend = data.get('embedding_backend', 'mlx').lower()
                if backend in ['mlx', 'ollama', 'sentence-transformers', 'hash']:
                    return backend
        except Exception:
            pass
            
        return 'mlx'  # Default
    
    def is_available(self) -> bool:
        """Check if embedder is available"""
        if not self._initialized:
            self.initialize()
        return self._initialized

    def initialize(self) -> bool:
        """Initialize the embedding backend"""
        if self._initialized:
            return True

        # Silently try backends (only log success)

        if self.backend == 'mlx':
            # PHASE 1.1: Try Metal 4 MPS embedder first (5-10x faster)
            try:
                from metal4_mps_embedder import get_metal4_mps_embedder
                self._embedder = get_metal4_mps_embedder()
                if self._embedder.is_available():
                    self._initialized = True
                    self.mlx_available = self._embedder.uses_metal()
                    self.model_name = f"Metal 4 MPS ({self._embedder.model_name})"
                    logger.info(f"✅ Metal 4 MPS embedder initialized (GPU: {self.mlx_available})")
                    return True
            except Exception as e:
                logger.debug(f"Metal 4 MPS embedder unavailable: {e}")
                pass  # Silently fall back

            try:
                # Try MLX sentence transformer
                from mlx_sentence_transformer import MLXSentenceTransformer
                self._embedder = MLXSentenceTransformer()
                if self._embedder.initialize():
                    self._initialized = True
                    self.mlx_available = True
                    self.model_name = "MLX Sentence Transformer"
                    logger.info("MLX sentence transformer initialized")
                    return True
            except Exception:
                pass  # Silently fail

            try:
                # Fall back to MLX embedder
                from mlx_embedder import MLXEmbedder
                self._embedder = MLXEmbedder()
                if self._embedder.initialize():
                    self._initialized = True
                    self.mlx_available = True
                    self.model_name = "MLX Embedder"
                    logger.info("MLX embedder initialized")
                    return True
            except Exception:
                pass  # Silently fail

        elif self.backend == 'sentence-transformers':
            try:
                from embedding_system import EmbeddingSystem
                self._embedder = EmbeddingSystem()
                self._initialized = True
                self.model_name = "sentence-transformers"
                logger.info("Sentence transformers initialized")
                return True
            except Exception as e:
                logger.warning(f"Sentence transformers failed: {e}")

        elif self.backend == 'ollama':
            # Ollama doesn't need initialization
            self._initialized = True
            self.model_name = os.getenv('JARVIS_EMBED_MODEL', 'nomic-embed-text')
            return True

        # Fall back to hash
        logger.info("Using hash embedding fallback")
        self.backend = 'hash'
        self.model_name = "Hash Fallback (384d)"
        self._initialized = True
        return True
    
    def embed(self, text: str) -> List[float]:
        """Embed a single text"""
        if not self._initialized:
            self.initialize()
            
        if self.backend == 'mlx' and self._embedder:
            if hasattr(self._embedder, 'encode'):
                # MLXSentenceTransformer
                embeddings = self._embedder.encode([text])
                if embeddings.size > 0:
                    return embeddings[0].tolist()
            elif hasattr(self._embedder, 'embed'):
                # MLXEmbedder
                return self._embedder.embed(text)
                
        elif self.backend == 'sentence-transformers' and self._embedder:
            embedding = self._embedder.embed(text)
            if isinstance(embedding, (list, tuple)):
                return list(embedding)
            elif hasattr(embedding, 'tolist'):
                return embedding.tolist()
                
        elif self.backend == 'ollama':
            embedding = self._embed_ollama(text)
            if embedding:
                return embedding
                
        # Fall back to hash
        return self._embed_hash(text)
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts efficiently"""
        if not self._initialized:
            self.initialize()
            
        if self.backend == 'mlx' and self._embedder and hasattr(self._embedder, 'encode'):
            # MLXSentenceTransformer supports batch encoding
            embeddings = self._embedder.encode(texts)
            return [emb.tolist() for emb in embeddings]
            
        # Fall back to single embedding
        return [self.embed(text) for text in texts]
    
    def _embed_ollama(self, text: str) -> Optional[List[float]]:
        """Embed using Ollama API"""
        try:
            import urllib.request
            model = os.getenv('JARVIS_EMBED_MODEL', 'nomic-embed-text')
            
            req = urllib.request.Request(
                url='http://127.0.0.1:11434/api/embeddings',
                data=json.dumps({
                    'model': model,
                    'prompt': text
                }).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read())
                return data.get('embedding', [])
                
        except Exception as e:
            logger.warning(f"Ollama embedding failed: {e}")
            return None
    
    def _embed_hash(self, text: str, dim: int = 384) -> List[float]:
        """Simple hash-based embedding fallback"""
        import hashlib
        
        # Create multiple hash values for higher dimensions
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


# Singleton instance
_unified_embedder = None


def get_embedder() -> UnifiedEmbedder:
    """Get the singleton embedder instance"""
    global _unified_embedder
    if _unified_embedder is None:
        _unified_embedder = UnifiedEmbedder()
    return _unified_embedder


def get_unified_embedder() -> Optional[UnifiedEmbedder]:
    """Alias for get_embedder() - for compatibility"""
    embedder = get_embedder()
    embedder.initialize()
    return embedder if embedder._initialized else None


def embed_text(text: str) -> List[float]:
    """Convenient function to embed text"""
    return get_embedder().embed(text)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Convenient function to embed multiple texts"""
    return get_embedder().embed_batch(texts)