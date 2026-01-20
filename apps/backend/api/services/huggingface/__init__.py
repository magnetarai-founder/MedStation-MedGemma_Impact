"""
HuggingFace Integration Services

Provides:
- GGUF model downloads from HuggingFace Hub
- Model registry with curated GGUF models
- Storage management for downloaded models
"""

from .downloader import HuggingFaceDownloader, get_huggingface_downloader
from .gguf_registry import GGUFRegistry, MEDGEMMA_MODELS, RECOMMENDED_MODELS, get_gguf_registry
from .storage import HuggingFaceStorage, get_huggingface_storage

__all__ = [
    "HuggingFaceDownloader",
    "get_huggingface_downloader",
    "GGUFRegistry",
    "get_gguf_registry",
    "HuggingFaceStorage",
    "get_huggingface_storage",
    "MEDGEMMA_MODELS",
    "RECOMMENDED_MODELS",
]
