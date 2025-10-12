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

# Storage path for favorites
FAVORITES_FILE = Path(".neutron_data/model_favorites.json")
FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)


class ModelManager:
    """Manages model favorites and status"""

    def __init__(self):
        self.favorites: List[str] = []
        self.load_favorites()

    def load_favorites(self):
        """Load favorites from disk"""
        try:
            if FAVORITES_FILE.exists():
                with open(FAVORITES_FILE, 'r') as f:
                    data = json.load(f)
                    self.favorites = data.get('favorites', [])
                    logger.info(f"Loaded {len(self.favorites)} favorite models")
        except Exception as e:
            logger.error(f"Failed to load favorites: {e}")
            self.favorites = []

    def save_favorites(self):
        """Save favorites to disk"""
        try:
            data = {
                'favorites': self.favorites,
                'updated_at': datetime.utcnow().isoformat()
            }
            with open(FAVORITES_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.favorites)} favorite models")
        except Exception as e:
            logger.error(f"Failed to save favorites: {e}")

    def add_favorite(self, model_name: str) -> bool:
        """Add a model to favorites"""
        if model_name not in self.favorites:
            self.favorites.append(model_name)
            self.save_favorites()
            logger.info(f"Added '{model_name}' to favorites")
            return True
        return False

    def remove_favorite(self, model_name: str) -> bool:
        """Remove a model from favorites"""
        if model_name in self.favorites:
            self.favorites.remove(model_name)
            self.save_favorites()
            logger.info(f"Removed '{model_name}' from favorites")
            return True
        return False

    def get_favorites(self) -> List[str]:
        """Get list of favorite models"""
        return self.favorites.copy()

    def is_favorite(self, model_name: str) -> bool:
        """Check if a model is favorited"""
        return model_name in self.favorites

    async def get_model_status(self, ollama_client) -> List[Dict[str, Any]]:
        """
        Get status of all models (loaded/unloaded, memory usage)

        Returns list of models with status info:
        - name: model name
        - loaded: whether model is currently loaded
        - is_favorite: whether model is in favorites
        - size: model size
        - memory_usage: estimated memory usage (if loaded)
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

            # Build status list
            status_list = []
            for model in models:
                status_list.append({
                    "name": model.name,
                    "loaded": model.name in running_models,
                    "is_favorite": self.is_favorite(model.name),
                    "size": model.size,
                    "modified_at": model.modified_at
                })

            return status_list

        except Exception as e:
            logger.error(f"Failed to get model status: {e}")
            return []


# Global instance
_model_manager = ModelManager()


def get_model_manager() -> ModelManager:
    """Get global model manager instance"""
    return _model_manager
