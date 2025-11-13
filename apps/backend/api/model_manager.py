"""
Model Management Service
Handles model favorites, status tracking, and auto-loading
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Storage path for hot slots
from config_paths import get_config_paths
PATHS = get_config_paths()
HOT_SLOTS_FILE = PATHS.data_dir / "model_hot_slots.json"

# Model filtering patterns
EMBEDDING_MODEL_PATTERNS = [
    'embed',
    'embedding',
    'nomic-embed',
    'mxbai-embed',
    'bge-',
    'e5-',
    'gte-',
    'sentence-',
]

FOUNDATION_MODEL_PATTERNS = [
    '-base',
    'foundation',
    'pretrain',
    'base-',
]


def is_chat_model(model_name: str) -> bool:
    """
    Determine if a model is suitable for chat

    Returns False for:
    - Embedding models (nomic-embed-text, mxbai-embed-large, etc.)
    - Foundation models (base models without instruction tuning)

    Returns True for:
    - Instruction-tuned chat models
    - Code models
    - Reasoning models
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


def is_orchestrator_suitable(model_name: str, model_size: str) -> bool:
    """
    Determine if a model is suitable for orchestrator use

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
    """
    name_lower = model_name.lower()

    # Filter out embedding models (can't reason/route)
    for pattern in EMBEDDING_MODEL_PATTERNS:
        if pattern in name_lower:
            return False

    # Parse size to check if model is small enough
    # Size format examples: "4.7 GB", "986 MB", "2.2GB"
    try:
        size_str = model_size.upper().replace(' ', '')
        if 'GB' in size_str:
            size_gb = float(size_str.replace('GB', ''))
            # Only allow models < 4GB for orchestrator (lightweight, always-running)
            return size_gb < 4.0
        elif 'MB' in size_str:
            # MB models are definitely small enough
            return True
        else:
            # Unknown format, be conservative
            return False
    except (ValueError, AttributeError):
        # If we can't parse size, default to regular chat model check
        return is_chat_model(model_name)


def get_model_unavailable_reason(model_name: str) -> Optional[str]:
    """
    Get the reason why a model is unavailable for chat

    Returns:
    - "Embedding Model (not for chat)" for embedding models
    - "Foundation Model (requires instruction tuning)" for foundation models
    - None if model is available
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


class ModelManager:
    """Manages model hot slots and status"""

    def __init__(self):
        self.hot_slots: Dict[int, Optional[str]] = {1: None, 2: None, 3: None, 4: None}
        self.load_hot_slots()

    def load_hot_slots(self):
        """
        Load hot slots from disk

        Note: model_hot_slots.json is initialized on demand (first assignment).
        If file doesn't exist, hot slots are empty (no models preloaded).
        """
        try:
            if HOT_SLOTS_FILE.exists():
                with open(HOT_SLOTS_FILE, 'r') as f:
                    data = json.load(f)
                    slots = data.get('hot_slots', {})
                    # Convert string keys to int
                    self.hot_slots = {int(k): v for k, v in slots.items()}
                    logger.info(f"✅ Loaded hot slots from {HOT_SLOTS_FILE}: {self.hot_slots}")
            else:
                logger.info(f"ℹ️ Hot slots file not found (will be created on first assignment): {HOT_SLOTS_FILE}")
                self.hot_slots = {1: None, 2: None, 3: None, 4: None}
        except Exception as e:
            logger.error(f"❌ Failed to load hot slots: {e}")
            self.hot_slots = {1: None, 2: None, 3: None, 4: None}

    def save_hot_slots(self):
        """
        Save hot slots to disk (creates file if doesn't exist)

        This is called on-demand when:
        - User assigns a model to a hot slot
        - User removes a model from a hot slot
        """
        try:
            # Ensure parent directory exists
            HOT_SLOTS_FILE.parent.mkdir(parents=True, exist_ok=True)

            data = {
                'hot_slots': self.hot_slots,
                'updated_at': datetime.utcnow().isoformat()
            }

            file_exists = HOT_SLOTS_FILE.exists()
            with open(HOT_SLOTS_FILE, 'w') as f:
                json.dump(data, f, indent=2)

            if file_exists:
                logger.info(f"💾 Updated hot slots in {HOT_SLOTS_FILE}: {self.hot_slots}")
            else:
                logger.info(f"✨ Created hot slots file at {HOT_SLOTS_FILE}: {self.hot_slots}")
        except Exception as e:
            logger.error(f"❌ Failed to save hot slots: {e}")

    def assign_to_slot(self, slot_number: int, model_name: str) -> bool:
        """Assign a model to a specific hot slot (1-4)"""
        if slot_number not in [1, 2, 3, 4]:
            logger.error(f"Invalid slot number: {slot_number}")
            return False

        self.hot_slots[slot_number] = model_name
        self.save_hot_slots()
        logger.info(f"Assigned '{model_name}' to slot {slot_number}")
        return True

    def remove_from_slot(self, slot_number: int) -> bool:
        """Remove a model from a specific hot slot"""
        if slot_number not in [1, 2, 3, 4]:
            logger.error(f"Invalid slot number: {slot_number}")
            return False

        if self.hot_slots[slot_number] is not None:
            model_name = self.hot_slots[slot_number]
            self.hot_slots[slot_number] = None
            self.save_hot_slots()
            logger.info(f"Removed '{model_name}' from slot {slot_number}")
            return True
        return False

    def get_hot_slots(self) -> Dict[int, Optional[str]]:
        """Get current hot slot assignments"""
        return self.hot_slots.copy()

    def get_slot_for_model(self, model_name: str) -> Optional[int]:
        """Get the slot number for a specific model (if assigned)"""
        for slot_num, assigned_model in self.hot_slots.items():
            if assigned_model == model_name:
                return slot_num
        return None

    def get_favorites(self) -> List[str]:
        """
        Get list of favorite models (models assigned to hot slots)

        Returns:
            List of model names assigned to hot slots, excluding None values
        """
        favorites = []
        for slot_num in sorted(self.hot_slots.keys()):
            model = self.hot_slots[slot_num]
            if model is not None:
                favorites.append(model)

        logger.debug(f"Retrieved {len(favorites)} favorite models: {favorites}")
        return favorites

    async def get_model_status(self, ollama_client) -> Dict[str, Any]:
        """
        Get status of all models (loaded/unloaded, memory usage)

        Returns dict with two categories:
        {
            "available": [...],    # Chat models suitable for conversation
            "unavailable": [...]   # Embedding/foundation models with reasons
        }

        Each model entry contains:
        - name: model name
        - loaded: whether model is currently loaded
        - slot_number: which hot slot (1-4) the model is assigned to, or null if not assigned
        - size: model size
        - modified_at: last modified timestamp
        - unavailable_reason: (for unavailable models only) reason why unavailable
        """
        try:
            # Get all available models
            models = await ollama_client.list_models()

            # Get running models from Ollama
            import httpx
            running_models = set()
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.get(f"{ollama_client.base_url}/api/ps")
                    if response.status_code == 200:
                        data = response.json()
                        for model_info in data.get("models", []):
                            running_models.add(model_info.get("name"))
            except Exception as e:
                logger.debug(f"Could not get running models: {e}")

            # Separate models into available and unavailable
            available_models = []
            unavailable_models = []

            for model in models:
                # Handle both dict and object formats from different OllamaClient implementations
                model_name = model.get("name") if isinstance(model, dict) else model.name
                model_size = model.get("size") if isinstance(model, dict) else model.size
                model_modified = model.get("modified_at") if isinstance(model, dict) else model.modified_at

                model_info = {
                    "name": model_name,
                    "loaded": model_name in running_models,
                    "slot_number": self.get_slot_for_model(model_name),
                    "size": model_size,
                    "modified_at": model_modified
                }

                # Check if model is suitable for chat
                if is_chat_model(model_name):
                    available_models.append(model_info)
                else:
                    # Add reason why model is unavailable
                    reason = get_model_unavailable_reason(model_name)
                    model_info["unavailable_reason"] = reason
                    unavailable_models.append(model_info)

            return {
                "available": available_models,
                "unavailable": unavailable_models
            }

        except Exception as e:
            logger.error(f"Failed to get model status: {e}")
            return {
                "available": [],
                "unavailable": []
            }


# Global instance
_model_manager = ModelManager()


def get_model_manager() -> ModelManager:
    """Get global model manager instance"""
    return _model_manager
