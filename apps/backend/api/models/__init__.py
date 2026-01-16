"""
Models Package

Model management for ElohimOS:
- Model filtering and classification
- Favorites and status tracking
- Auto-loading functionality
"""

from api.models.filtering import (
    EMBEDDING_MODEL_PATTERNS,
    FOUNDATION_MODEL_PATTERNS,
    is_chat_model,
    is_orchestrator_suitable,
    get_model_unavailable_reason,
    parse_model_size_gb,
)
from api.models.manager import (
    ModelManager,
    get_model_manager,
)

__all__ = [
    # Filtering
    "EMBEDDING_MODEL_PATTERNS",
    "FOUNDATION_MODEL_PATTERNS",
    "is_chat_model",
    "is_orchestrator_suitable",
    "get_model_unavailable_reason",
    "parse_model_size_gb",
    # Manager
    "ModelManager",
    "get_model_manager",
]
