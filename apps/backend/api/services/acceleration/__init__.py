"""
Hardware Acceleration Package

Provides native acceleration for MagnetarCode:
- MLX inference on Apple Silicon (10-100x faster than Ollama)
- MPS-accelerated embeddings
- GPU-accelerated FAISS search
- Speculative decoding for faster completions
- Predictive caching
"""

from .mlx_inference import (
    MLXInferenceClient,
    MLXConfig,
    is_mlx_available,
    get_mlx_client,
)
from .mps_embeddings import (
    MPSEmbeddingModel,
    is_mps_available,
    get_mps_embeddings,
)
from .speculative import (
    SpeculativeDecoder,
    get_speculative_decoder,
)

__all__ = [
    # MLX Inference
    "MLXInferenceClient",
    "MLXConfig",
    "is_mlx_available",
    "get_mlx_client",
    # MPS Embeddings
    "MPSEmbeddingModel",
    "is_mps_available",
    "get_mps_embeddings",
    # Speculative Decoding
    "SpeculativeDecoder",
    "get_speculative_decoder",
]
