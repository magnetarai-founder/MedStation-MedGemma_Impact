"""
HuggingFace Integration Services

Provides:
- GGUF model downloads from HuggingFace Hub
- Model registry with curated GGUF models
- Storage management for downloaded models
"""

from .downloader import HuggingFaceDownloader
from .gguf_registry import GGUFRegistry, MEDGEMMA_MODELS, RECOMMENDED_MODELS
from .storage import HuggingFaceStorage

__all__ = [
    "HuggingFaceDownloader",
    "GGUFRegistry",
    "HuggingFaceStorage",
    "MEDGEMMA_MODELS",
    "RECOMMENDED_MODELS",
]
