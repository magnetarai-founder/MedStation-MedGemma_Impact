"""
Unified Models Routes - Combined model listing from all sources

Provides a single endpoint that returns models from:
- Ollama (local inference server)
- HuggingFace GGUF (llama.cpp inference)
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, status
from pydantic import BaseModel

from api.routes.schemas import SuccessResponse
from api.errors import http_500

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# Response Models
# ==============================================================================

class UnifiedModelResponse(BaseModel):
    """Unified model info for API responses"""
    id: str
    name: str
    source: str  # "ollama" or "huggingface"
    size_bytes: Optional[int] = None
    size_formatted: str
    quantization: Optional[str] = None
    parameter_count: Optional[str] = None
    is_downloaded: bool = False
    is_running: bool = False
    capabilities: List[str] = []
    context_length: Optional[int] = None
    description: Optional[str] = None

    # Source-specific
    ollama_name: Optional[str] = None
    repo_id: Optional[str] = None
    filename: Optional[str] = None

    # Hardware info
    min_vram_gb: Optional[float] = None
    recommended_vram_gb: Optional[float] = None


class UnifiedModelsListResponse(BaseModel):
    """Response for unified models list"""
    models: List[UnifiedModelResponse]
    ollama_count: int
    huggingface_count: int
    total_count: int
    ollama_running: bool
    llamacpp_running: bool
    llamacpp_model: Optional[str] = None


# ==============================================================================
# Unified Models Endpoint
# ==============================================================================

@router.get(
    "/models/unified",
    response_model=SuccessResponse[UnifiedModelsListResponse],
    status_code=status.HTTP_200_OK,
    name="chat_list_unified_models"
)
async def list_unified_models(
    source: Optional[str] = None,
    capability: Optional[str] = None,
    downloaded_only: bool = False,
):
    """
    List all available models from Ollama and HuggingFace (public endpoint)

    Combines models from both sources into a unified format for the UI.

    Query Parameters:
    - source: Filter by source ("ollama" or "huggingface")
    - capability: Filter by capability ("medical", "code", "chat", "vision")
    - downloaded_only: Only show downloaded/installed models
    """
    from api.services import chat
    from api.services.huggingface import GGUFRegistry, get_gguf_registry
    from api.services.huggingface.storage import get_huggingface_storage
    from api.services.llamacpp import get_llamacpp_server
    from api.services.model_source.types import ModelCapability

    models: List[UnifiedModelResponse] = []
    ollama_count = 0
    huggingface_count = 0

    # Check backend statuses
    ollama_running = False
    llamacpp_running = False
    llamacpp_model = None

    try:
        # Get llama.cpp server status
        server = get_llamacpp_server()
        server_status = await server.get_status()
        llamacpp_running = server_status.running and server_status.health_ok
        llamacpp_model = server_status.model_loaded
    except Exception as e:
        logger.warning(f"Failed to get llama.cpp status: {e}")

    # Get Ollama models
    if source is None or source == "ollama":
        try:
            ollama_models = await chat.list_ollama_models()
            ollama_running = True

            for m in ollama_models:
                # Filter by capability if specified (basic tag matching)
                if capability:
                    model_name = m.get("name", "").lower()
                    if capability == "code" and "code" not in model_name:
                        continue
                    if capability == "vision" and "vision" not in model_name and "llava" not in model_name:
                        continue
                    if capability == "medical" and "med" not in model_name:
                        continue

                size_bytes = m.get("size", 0)
                size_gb = size_bytes / (1024**3) if size_bytes else 0

                models.append(UnifiedModelResponse(
                    id=f"ollama:{m.get('name', '')}",
                    name=m.get("name", ""),
                    source="ollama",
                    size_bytes=size_bytes,
                    size_formatted=f"{size_gb:.1f} GB" if size_gb >= 1 else f"{size_bytes / (1024**2):.0f} MB",
                    is_downloaded=True,  # Ollama models are always downloaded
                    is_running=False,  # Would need to check /api/ps
                    ollama_name=m.get("name"),
                ))

            ollama_count = len([m for m in models if m.source == "ollama"])

        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
            ollama_running = False

    # Get HuggingFace models
    if source is None or source == "huggingface":
        try:
            registry = get_gguf_registry()
            storage = get_huggingface_storage()

            # Get models based on capability filter
            if capability:
                try:
                    cap = ModelCapability(capability)
                    gguf_models = registry.list_by_capability(cap)
                except ValueError:
                    gguf_models = registry.list_all_models()
            else:
                gguf_models = registry.list_all_models()

            for m in gguf_models:
                is_downloaded = storage.is_model_downloaded(m.repo_id, m.filename)

                # Skip if downloaded_only and not downloaded
                if downloaded_only and not is_downloaded:
                    continue

                # Check if this model is running in llama.cpp
                is_running = (
                    llamacpp_running and
                    llamacpp_model and
                    m.name.lower() in llamacpp_model.lower()
                )

                models.append(UnifiedModelResponse(
                    id=f"hf:{m.id}",
                    name=m.name,
                    source="huggingface",
                    size_bytes=int(m.size_gb * 1024**3),
                    size_formatted=f"{m.size_gb:.1f} GB",
                    quantization=m.quantization.value,
                    parameter_count=m.parameter_count,
                    is_downloaded=is_downloaded,
                    is_running=is_running,
                    capabilities=[c.value for c in m.capabilities],
                    context_length=m.context_length,
                    description=m.description,
                    repo_id=m.repo_id,
                    filename=m.filename,
                    min_vram_gb=m.min_vram_gb,
                    recommended_vram_gb=m.recommended_vram_gb,
                ))

            huggingface_count = len([m for m in models if m.source == "huggingface"])

        except Exception as e:
            logger.warning(f"Failed to list HuggingFace models: {e}")

    # Apply downloaded_only filter for ollama (they're always downloaded, so keep them)
    # Already applied for HuggingFace above

    return SuccessResponse(
        data=UnifiedModelsListResponse(
            models=models,
            ollama_count=ollama_count,
            huggingface_count=huggingface_count,
            total_count=len(models),
            ollama_running=ollama_running,
            llamacpp_running=llamacpp_running,
            llamacpp_model=llamacpp_model,
        ),
        message=f"Found {len(models)} models ({ollama_count} Ollama, {huggingface_count} HuggingFace)"
    )


@router.get(
    "/models/backends",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_backends_status"
)
async def get_backends_status():
    """
    Get status of all inference backends (public endpoint)

    Returns the running status of Ollama and llama.cpp servers.
    """
    from api.services.chat.ollama_ops import get_ollama_server_status
    from api.services.llamacpp import get_llamacpp_server

    try:
        # Get Ollama status
        ollama_status = await get_ollama_server_status()

        # Get llama.cpp status
        server = get_llamacpp_server()
        llamacpp_status = await server.get_status()

        return SuccessResponse(
            data={
                "ollama": {
                    "running": ollama_status.get("running", False),
                    "loaded_models": ollama_status.get("loaded_models", []),
                    "model_count": ollama_status.get("model_count", 0),
                },
                "llamacpp": {
                    "running": llamacpp_status.running,
                    "health_ok": llamacpp_status.health_ok,
                    "model_loaded": llamacpp_status.model_loaded,
                    "port": llamacpp_status.port,
                },
            },
            message="Backend status retrieved"
        )

    except Exception as e:
        logger.error(f"Failed to get backends status: {e}", exc_info=True)
        raise http_500("Failed to get backends status")
