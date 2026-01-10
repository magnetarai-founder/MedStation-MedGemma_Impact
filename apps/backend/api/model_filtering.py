"""
Model Filtering Patterns and Classification Functions

Pure functions for determining model suitability for different use cases.
Extracted from model_manager.py during P2 decomposition.

Contains:
- EMBEDDING_MODEL_PATTERNS: Patterns identifying embedding models
- FOUNDATION_MODEL_PATTERNS: Patterns identifying foundation (base) models
- is_chat_model(): Check if model is suitable for chat
- is_orchestrator_suitable(): Check if model is suitable for orchestration
- get_model_unavailable_reason(): Get reason why model can't be used for chat
- parse_model_size_gb(): Parse model size string to GB float
"""

from typing import Optional, List


# ============================================
# MODEL FILTERING PATTERNS
# ============================================

EMBEDDING_MODEL_PATTERNS: List[str] = [
    'embed',
    'embedding',
    'nomic-embed',
    'mxbai-embed',
    'bge-',
    'e5-',
    'gte-',
    'sentence-',
]
"""
Patterns that identify embedding models.
These models generate vector representations and are NOT suitable for chat.

Examples:
- nomic-embed-text
- mxbai-embed-large
- bge-large-en
- e5-base-v2
- sentence-transformers
"""

FOUNDATION_MODEL_PATTERNS: List[str] = [
    '-base',
    'foundation',
    'pretrain',
    'base-',
]
"""
Patterns that identify foundation/base models.
These models lack instruction tuning and produce poor chat responses.

Examples:
- llama-2-7b-base
- mistral-7b-foundation
- phi-2-pretrain
"""

# Orchestrator size threshold (models must be smaller than this for routing)
ORCHESTRATOR_MAX_SIZE_GB: float = 4.0
"""
Maximum model size in GB for orchestrator use.
Smaller models are preferred for always-running routing tasks.
"""


# ============================================
# PURE CLASSIFICATION FUNCTIONS
# ============================================

def is_chat_model(model_name: str) -> bool:
    """
    Determine if a model is suitable for chat.

    Returns False for:
    - Embedding models (nomic-embed-text, mxbai-embed-large, etc.)
    - Foundation models (base models without instruction tuning)

    Returns True for:
    - Instruction-tuned chat models
    - Code models
    - Reasoning models

    Args:
        model_name: Name of the model to check

    Returns:
        True if model is suitable for chat, False otherwise

    Examples:
        >>> is_chat_model("llama3.1:8b-instruct")
        True
        >>> is_chat_model("nomic-embed-text")
        False
        >>> is_chat_model("llama-2-7b-base")
        False
    """
    name_lower = model_name.lower()

    # Filter out embedding models
    for pattern in EMBEDDING_MODEL_PATTERNS:
        if pattern in name_lower:
            return False

    # Filter out foundation models
    for pattern in FOUNDATION_MODEL_PATTERNS:
        if pattern in name_lower:
            return False

    return True


def parse_model_size_gb(size_str: str) -> Optional[float]:
    """
    Parse a model size string to GB.

    Handles formats like:
    - "4.7 GB"
    - "986 MB"
    - "2.2GB"

    Args:
        size_str: Model size string

    Returns:
        Size in GB, or None if parsing fails

    Examples:
        >>> parse_model_size_gb("4.7 GB")
        4.7
        >>> parse_model_size_gb("986 MB")
        0.986
        >>> parse_model_size_gb("unknown")
        None
    """
    try:
        size_str = size_str.upper().replace(' ', '')
        if 'GB' in size_str:
            return float(size_str.replace('GB', ''))
        elif 'MB' in size_str:
            return float(size_str.replace('MB', '')) / 1000
        else:
            return None
    except (ValueError, AttributeError):
        return None


def is_orchestrator_suitable(model_name: str, model_size: str) -> bool:
    """
    Determine if a model is suitable for orchestrator use.

    Orchestrator needs:
    - Small, efficient models (1.5B-3B params recommended)
    - Can route/reason (doesn't need perfect chat formatting)
    - NOT embedding models

    Returns True for:
    - Small base models (< 4GB) - efficient for routing
    - Small instruction-tuned models
    - Code models

    Returns False for:
    - Embedding models (not suitable for reasoning)
    - Large models (> 4GB) - too heavy for always-running orchestrator

    Args:
        model_name: Name of the model to check
        model_size: Size string like "4.7 GB" or "986 MB"

    Returns:
        True if model is suitable for orchestration, False otherwise

    Examples:
        >>> is_orchestrator_suitable("phi-3:3.8b", "2.2 GB")
        True
        >>> is_orchestrator_suitable("llama3.1:70b", "40 GB")
        False
        >>> is_orchestrator_suitable("nomic-embed-text", "500 MB")
        False
    """
    name_lower = model_name.lower()

    # Filter out embedding models (can't reason/route)
    for pattern in EMBEDDING_MODEL_PATTERNS:
        if pattern in name_lower:
            return False

    # Parse size to check if model is small enough
    size_gb = parse_model_size_gb(model_size)

    if size_gb is not None:
        # Only allow models under threshold for orchestrator
        return size_gb < ORCHESTRATOR_MAX_SIZE_GB
    else:
        # Unknown format - fall back to chat model check
        return is_chat_model(model_name)


def get_model_unavailable_reason(model_name: str) -> Optional[str]:
    """
    Get the reason why a model is unavailable for chat.

    Args:
        model_name: Name of the model to check

    Returns:
        - "Embedding Model (not for chat)" for embedding models
        - "Foundation Model (requires instruction tuning)" for foundation models
        - None if model is available for chat

    Examples:
        >>> get_model_unavailable_reason("nomic-embed-text")
        'Embedding Model (not for chat)'
        >>> get_model_unavailable_reason("llama-2-7b-base")
        'Foundation Model (requires instruction tuning)'
        >>> get_model_unavailable_reason("llama3.1:8b-instruct")
        None
    """
    name_lower = model_name.lower()

    # Check embedding patterns first
    for pattern in EMBEDDING_MODEL_PATTERNS:
        if pattern in name_lower:
            return "Embedding Model (not for chat)"

    # Check foundation patterns
    for pattern in FOUNDATION_MODEL_PATTERNS:
        if pattern in name_lower:
            return "Foundation Model (requires instruction tuning)"

    return None


def get_model_type(model_name: str) -> str:
    """
    Get the type/category of a model.

    Args:
        model_name: Name of the model

    Returns:
        One of: "embedding", "foundation", "chat"

    Examples:
        >>> get_model_type("nomic-embed-text")
        'embedding'
        >>> get_model_type("llama-2-7b-base")
        'foundation'
        >>> get_model_type("llama3.1:8b-instruct")
        'chat'
    """
    name_lower = model_name.lower()

    for pattern in EMBEDDING_MODEL_PATTERNS:
        if pattern in name_lower:
            return "embedding"

    for pattern in FOUNDATION_MODEL_PATTERNS:
        if pattern in name_lower:
            return "foundation"

    return "chat"


__all__ = [
    # Constants
    "EMBEDDING_MODEL_PATTERNS",
    "FOUNDATION_MODEL_PATTERNS",
    "ORCHESTRATOR_MAX_SIZE_GB",
    # Functions
    "is_chat_model",
    "is_orchestrator_suitable",
    "get_model_unavailable_reason",
    "get_model_type",
    "parse_model_size_gb",
]
