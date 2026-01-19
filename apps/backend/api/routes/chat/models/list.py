"""
Model Listing & Status Routes - Model listing, status, tags, and caching

Split from models.py for maintainability.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC
from fastapi import APIRouter, HTTPException, status

from api.routes.schemas import SuccessResponse
from api.errors import http_500

logger = logging.getLogger(__name__)

router = APIRouter()


# ===== Model List Cache for Graceful Fallback =====

class ModelListCache:
    """
    Cache for model listings to provide graceful fallback when Ollama is unreachable.

    RESILIENCE: Returns cached data when Ollama API fails, with 'cached: true' flag.
    """

    def __init__(self):
        self._models: List[Dict[str, Any]] = []
        self._models_with_tags: List[Dict[str, Any]] = []
        self._last_updated: Optional[datetime] = None
        self._cache_ttl_seconds: int = 300  # 5 minutes

    def update_models(self, models: List[Dict[str, Any]]) -> None:
        """Update cached model list"""
        self._models = models
        self._last_updated = datetime.now(UTC)

    def update_models_with_tags(self, models: List[Dict[str, Any]]) -> None:
        """Update cached model list with tags"""
        self._models_with_tags = models
        self._last_updated = datetime.now(UTC)

    def get_models(self) -> tuple[List[Dict[str, Any]], bool]:
        """
        Get cached models.

        Returns:
            Tuple of (models, is_cached)
        """
        return self._models, len(self._models) > 0

    def get_models_with_tags(self) -> tuple[List[Dict[str, Any]], bool]:
        """
        Get cached models with tags.

        Returns:
            Tuple of (models, is_cached)
        """
        return self._models_with_tags, len(self._models_with_tags) > 0

    @property
    def has_cache(self) -> bool:
        """Check if we have any cached data"""
        return len(self._models) > 0 or len(self._models_with_tags) > 0

    @property
    def cache_age_seconds(self) -> Optional[float]:
        """Get cache age in seconds"""
        if self._last_updated is None:
            return None
        return (datetime.now(UTC) - self._last_updated).total_seconds()


# Global cache instance
_model_cache = ModelListCache()


# ===== Model Listing & Status =====

@router.get(
    "/models",
    response_model=SuccessResponse[list],
    status_code=status.HTTP_200_OK,
    name="chat_list_models"
)
async def list_ollama_models_endpoint():
    """
    List available Ollama models (public endpoint)

    RESILIENCE: Returns cached data if Ollama is unreachable, with 'cached: true' in response.
    """
    from api.services import chat
    from api.schemas.chat_models import OllamaModel

    try:
        models = await chat.list_ollama_models()
        data = [OllamaModel(**m) for m in models]

        # Update cache on successful fetch
        _model_cache.update_models([m.model_dump() if hasattr(m, 'model_dump') else m.__dict__ for m in data])

        return SuccessResponse(data=data, message=f"Found {len(data)} models")

    except Exception as e:
        logger.warning(f"Ollama unreachable, checking cache: {e}")

        # Try to return cached data
        cached_models, has_cache = _model_cache.get_models()
        if has_cache:
            from api.schemas.chat_models import OllamaModel
            data = [OllamaModel(**m) for m in cached_models]
            cache_age = _model_cache.cache_age_seconds
            logger.info(f"Returning {len(data)} cached models (age: {cache_age:.0f}s)")
            return SuccessResponse(
                data=data,
                message=f"Found {len(data)} models (cached, age: {int(cache_age or 0)}s)"
            )

        # No cache available - return error
        logger.error(f"Failed to list models (no cache): {e}", exc_info=True)
        raise http_500("Failed to list models")


@router.get(
    "/models/with-tags",
    response_model=SuccessResponse[list],
    status_code=status.HTTP_200_OK,
    name="chat_list_models_with_tags"
)
async def list_ollama_models_with_tags_endpoint():
    """List available Ollama models with auto-detected capability tags (public endpoint)"""
    from api.services import chat
    from api.services.model_tags import detect_tags_from_name, get_tag_description, get_tag_icon

    try:
        models = await chat.list_ollama_models()

        # Add auto-detected tags to each model
        models_with_tags = []
        for model in models:
            tags = list(detect_tags_from_name(model['name']))

            # Add tag metadata
            tag_details = [
                {
                    "id": tag,
                    "name": tag.replace("-", " ").title(),
                    "description": get_tag_description(tag),
                    "icon": get_tag_icon(tag)
                }
                for tag in tags
            ]

            model_with_tags = {
                **model,
                "tags": tags,
                "tag_details": tag_details
            }
            models_with_tags.append(model_with_tags)

        return SuccessResponse(
            data=models_with_tags,
            message=f"Found {len(models_with_tags)} models with tags"
        )
    except Exception as e:
        logger.error(f"Failed to list models with tags: {e}", exc_info=True)
        raise http_500("Failed to list models with tags")


@router.get(
    "/models/tags",
    response_model=SuccessResponse[list],
    status_code=status.HTTP_200_OK,
    name="chat_get_all_tags"
)
async def get_all_tags_endpoint():
    """Get all available model capability tags (public endpoint)"""
    from api.services.model_tags import get_all_tags

    try:
        tags = get_all_tags()
        return SuccessResponse(data=tags, message=f"Found {len(tags)} tags")
    except Exception as e:
        logger.error(f"Failed to get tags: {e}", exc_info=True)
        raise http_500("Failed to get tags")


@router.get(
    "/health",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_check_health"
)
async def check_health_endpoint():
    """Check Ollama health status (public endpoint)"""
    from api.services import chat

    try:
        health = await chat.check_health()
        return SuccessResponse(data=health, message="Health check completed")
    except Exception as e:
        logger.error(f"Failed to check health: {e}", exc_info=True)
        raise http_500("Failed to check health")


@router.get(
    "/models/status",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_get_models_status"
)
async def get_models_status_endpoint():
    """Get status of all models (public endpoint)"""
    from api.services import chat

    try:
        models_status = await chat.get_models_status()
        return SuccessResponse(data=models_status, message="Models status retrieved")
    except Exception as e:
        logger.error(f"Failed to get models status: {e}", exc_info=True)
        raise http_500("Failed to get models status")
