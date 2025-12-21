"""
Chat Service Hot Slot Management

Handles hot slot assignments for quick model access (global slots).
Delegates to ModelManager for slot storage and OllamaClient for preloading.

Phase 2.3b - Extracted from core.py, preserving existing global behavior.
Note: This uses the global ModelManager hot-slot system (not per-user).
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# ===== Lazy initialization helpers =====

_model_manager = None
_ollama_client = None


def _get_model_manager() -> Any:
    """Lazy init for model manager"""
    global _model_manager
    if _model_manager is None:
        try:
            from api.model_manager import get_model_manager
        except ImportError:
            from model_manager import get_model_manager
        _model_manager = get_model_manager()
    return _model_manager


def _get_ollama_client() -> Any:
    """Lazy init for Ollama client"""
    global _ollama_client
    if _ollama_client is None:
        from .streaming import OllamaClient
        _ollama_client = OllamaClient()
    return _ollama_client


# ============================================================================
# HOT SLOT OPERATIONS (GLOBAL)
# ============================================================================

async def get_hot_slots() -> Dict[int, Optional[str]]:
    """
    Get current hot slot assignments (global)

    Returns:
        Dictionary mapping slot number (1-4) to model name (or None)
        Example: {1: "qwen2.5-coder:7b", 2: "llama3.1:8b", 3: None, 4: None}
    """
    model_manager = _get_model_manager()
    return model_manager.get_hot_slots()


async def assign_to_hot_slot(slot_number: int, model_name: str) -> Dict[str, Any]:
    """
    Assign a model to a specific hot slot (global)

    If the model is already in another slot, it will be removed from that slot first.
    The model is then assigned to the new slot and preloaded into memory.

    Args:
        slot_number: Slot number (1-4)
        model_name: Model name to assign

    Returns:
        Dict with success status, model name, slot number, and updated hot slots
    """
    model_manager = _get_model_manager()
    ollama_client = _get_ollama_client()

    # Check if model already in another slot
    existing_slot = model_manager.get_slot_for_model(model_name)
    if existing_slot and existing_slot != slot_number:
        model_manager.remove_from_slot(existing_slot)

    # Assign to new slot
    success = model_manager.assign_to_slot(slot_number, model_name)

    # Preload the model
    await ollama_client.preload_model(model_name, "1h")

    return {
        "success": success,
        "model": model_name,
        "slot_number": slot_number,
        "hot_slots": model_manager.get_hot_slots()
    }


async def remove_from_hot_slot(slot_number: int) -> Dict[str, Any]:
    """
    Remove a model from a specific hot slot (global)

    The model is unloaded from memory and removed from the slot.

    Args:
        slot_number: Slot number (1-4)

    Returns:
        Dict with success status, slot number, model name, and updated hot slots
    """
    model_manager = _get_model_manager()
    ollama_client = _get_ollama_client()

    current_slots = model_manager.get_hot_slots()
    model_name = current_slots[slot_number]

    # Unload the model
    await ollama_client.preload_model(model_name, "0")

    # Remove from slot
    success = model_manager.remove_from_slot(slot_number)

    return {
        "success": success,
        "slot_number": slot_number,
        "model": model_name,
        "hot_slots": model_manager.get_hot_slots()
    }


async def load_hot_slot_models(keep_alive: str = "1h") -> Dict[str, Any]:
    """
    Load all hot slot models into memory (global)

    Iterates through all assigned slots and preloads each model.

    Args:
        keep_alive: How long to keep models in memory (default: 1h)

    Returns:
        Dict with total count, results per slot, and keep_alive setting
    """
    model_manager = _get_model_manager()
    ollama_client = _get_ollama_client()

    hot_slots = model_manager.get_hot_slots()
    results = []

    for slot_num, model_name in hot_slots.items():
        if model_name:
            success = await ollama_client.preload_model(model_name, keep_alive)
            results.append({
                "slot": slot_num,
                "model": model_name,
                "loaded": success
            })

    return {
        "total": len([m for m in hot_slots.values() if m is not None]),
        "results": results,
        "keep_alive": keep_alive
    }
