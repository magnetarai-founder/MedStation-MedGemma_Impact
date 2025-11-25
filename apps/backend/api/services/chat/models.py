"""
Chat Service Model Management

Handles model listing, preloading, unloading, and status tracking.
Delegates to ModelManager and OllamaClient for actual operations.

Phase 2.3b - Extracted from core.py, preserving all existing behavior.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# ===== Lazy initialization helpers =====

_model_manager = None
_ollama_client = None


def _get_model_manager():
    """Lazy init for model manager"""
    global _model_manager
    if _model_manager is None:
        try:
            from api.model_manager import get_model_manager
        except ImportError:
            from model_manager import get_model_manager
        _model_manager = get_model_manager()
    return _model_manager


def _get_ollama_client():
    """Lazy init for Ollama client - recreate on each call for now"""
    from .streaming import OllamaClient
    return OllamaClient()


# ============================================================================
# MODEL LISTING & STATUS
# ============================================================================

async def list_ollama_models() -> List[Dict[str, Any]]:
    """
    List available Ollama models

    Returns:
        List of chat-suitable models (filters out embedding models)
    """
    ollama_client = _get_ollama_client()
    models = await ollama_client.list_models()

    logger.info(f"OllamaClient returned {len(models)} models")

    # Filter out non-chat models
    excluded_patterns = ['embed', 'embedding', '-vision']

    chat_models = []
    for model in models:
        model_name_lower = model["name"].lower()
        if not any(pattern in model_name_lower for pattern in excluded_patterns):
            chat_models.append(model)

    logger.info(f"After filtering: {len(chat_models)} chat models")
    return chat_models


async def get_models_status() -> Dict[str, Any]:
    """
    Get status of all models

    Returns:
        Dict with 'available' and 'unavailable' model lists,
        including load status and slot assignments
    """
    model_manager = _get_model_manager()
    ollama_client = _get_ollama_client()
    return await model_manager.get_model_status(ollama_client)


async def get_orchestrator_suitable_models() -> List[Dict[str, Any]]:
    """
    Get models suitable for orchestrator use

    Returns:
        List of small, efficient models suitable for routing/orchestration
    """
    from model_manager import is_orchestrator_suitable

    ollama_client = _get_ollama_client()
    models = await ollama_client.list_models()

    suitable_models = []
    for model in models:
        if is_orchestrator_suitable(model["name"], model["size"]):
            suitable_models.append(model)

    return suitable_models


# ============================================================================
# MODEL PRELOADING & UNLOADING
# ============================================================================

async def preload_model(model: str, keep_alive: str = "1h", source: str = "unknown") -> bool:
    """
    Pre-load a model into memory

    Args:
        model: Model name to preload
        keep_alive: How long to keep model in memory (default: 1h)
        source: Source of preload request (e.g., "frontend_default", "hot_slot", "user_manual")

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"🔄 Preloading model '{model}' from source: {source} (keep_alive: {keep_alive})")
    ollama_client = _get_ollama_client()
    result = await ollama_client.preload_model(model, keep_alive)

    if result:
        logger.info(f"✅ Model '{model}' preloaded successfully (source: {source})")
    else:
        logger.warning(f"⚠️ Failed to preload model '{model}' (source: {source})")

    return result


async def unload_model(model_name: str) -> bool:
    """
    Unload a specific model from memory

    Args:
        model_name: Name of model to unload

    Returns:
        True if successful, False otherwise
    """
    ollama_client = _get_ollama_client()

    try:
        import httpx

        payload = {
            "model": model_name,
            "prompt": "",
            "stream": False,
            "keep_alive": 0
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{ollama_client.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()

        logger.info(f"✓ Unloaded model '{model_name}'")
        return True

    except Exception as e:
        logger.error(f"Failed to unload model '{model_name}': {e}")
        return False
