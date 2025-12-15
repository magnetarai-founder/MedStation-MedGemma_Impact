"""
Chat Models Routes - Model management, Ollama config, hot slots, performance monitoring
NOTE: This file contains many endpoints from the original monolithic chat.py
For a complete extraction, see the original file at api/routes/chat.py lines 249-1360

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import StreamingResponse

from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user

logger = logging.getLogger(__name__)

# This router can be used in both authenticated and public contexts
router = APIRouter()


# ===== Model Listing & Status =====

@router.get(
    "/models",
    response_model=SuccessResponse[list],
    status_code=status.HTTP_200_OK,
    name="chat_list_models"
)
async def list_ollama_models_endpoint():
    """List available Ollama models (public endpoint)"""
    from api.services import chat
    from api.schemas.chat_models import OllamaModel

    try:
        models = await chat.list_ollama_models()
        data = [OllamaModel(**m) for m in models]
        return SuccessResponse(data=data, message=f"Found {len(data)} models")
    except Exception as e:
        logger.error(f"Failed to list models: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to list models"
            ).model_dump()
        )


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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to list models with tags"
            ).model_dump()
        )


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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get tags"
            ).model_dump()
        )


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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to check health"
            ).model_dump()
        )


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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get models status"
            ).model_dump()
        )


# ===== Model Preloading =====

@router.post(
    "/models/preload",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_preload_model"
)
async def preload_model_endpoint(
    request: Request,
    model: str,
    keep_alive: str = "1h",
    source: str = "user_manual",
    current_user: dict = Depends(get_current_user)
):
    """Pre-load a model into memory"""
    from api.services import chat

    try:
        success = await chat.preload_model(model, keep_alive, source=source)

        if success:
            data = {
                "status": "success",
                "model": model,
                "keep_alive": keep_alive,
                "source": source
            }
            return SuccessResponse(
                data=data,
                message=f"Model '{model}' pre-loaded successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message=f"Failed to pre-load model '{model}'"
                ).model_dump()
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to preload model: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to preload model"
            ).model_dump()
        )


@router.post(
    "/models/unload/{model_name}",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_unload_model"
)
async def unload_model_endpoint(
    request: Request,
    model_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Unload a specific model from memory"""
    from api.services import chat

    try:
        success = await chat.unload_model(model_name)

        if success:
            data = {
                "status": "unloaded",
                "model": model_name
            }
            return SuccessResponse(
                data=data,
                message=f"Model '{model_name}' unloaded successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message=f"Failed to unload model '{model_name}'"
                ).model_dump()
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unload model: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to unload model"
            ).model_dump()
        )


# ===== Hot Slots =====

@router.get(
    "/models/hot-slots",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_get_hot_slots"
)
async def get_hot_slots_endpoint():
    """Get current hot slot assignments (public endpoint)"""
    from api.services import chat

    try:
        slots = await chat.get_hot_slots()
        data = {"hot_slots": slots}
        return SuccessResponse(data=data, message="Hot slots retrieved")
    except Exception as e:
        logger.error(f"Failed to get hot slots: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get hot slots"
            ).model_dump()
        )


@router.post(
    "/models/hot-slots/{slot_number}",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_assign_to_hot_slot"
)
async def assign_to_hot_slot_endpoint(
    request: Request,
    slot_number: int,
    model_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Assign a model to a specific hot slot"""
    from api.services import chat

    if slot_number not in [1, 2, 3, 4]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code=ErrorCode.BAD_REQUEST,
                message="Slot number must be between 1 and 4",
                details={"slot_number": slot_number}
            ).model_dump()
        )

    try:
        current_slots = await chat.get_hot_slots()
        if current_slots[slot_number] is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.CONFLICT,
                    message=f"Slot {slot_number} is already occupied by {current_slots[slot_number]}",
                    details={"slot_number": slot_number, "current_model": current_slots[slot_number]}
                ).model_dump()
            )

        result = await chat.assign_to_hot_slot(slot_number, model_name)
        return SuccessResponse(
            data=result,
            message=f"Model '{model_name}' assigned to slot {slot_number}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign to hot slot: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to assign to hot slot"
            ).model_dump()
        )


@router.delete(
    "/models/hot-slots/{slot_number}",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_remove_from_hot_slot"
)
async def remove_from_hot_slot_endpoint(
    request: Request,
    slot_number: int,
    current_user: dict = Depends(get_current_user)
):
    """Remove a model from a specific hot slot"""
    from api.services import chat

    if slot_number not in [1, 2, 3, 4]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code=ErrorCode.BAD_REQUEST,
                message="Slot number must be between 1 and 4",
                details={"slot_number": slot_number}
            ).model_dump()
        )

    try:
        current_slots = await chat.get_hot_slots()
        if current_slots[slot_number] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.BAD_REQUEST,
                    message=f"Slot {slot_number} is already empty",
                    details={"slot_number": slot_number}
                ).model_dump()
            )

        result = await chat.remove_from_hot_slot(slot_number)
        return SuccessResponse(
            data=result,
            message=f"Slot {slot_number} cleared successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove from hot slot: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to remove from hot slot"
            ).model_dump()
        )


@router.post(
    "/models/load-hot-slots",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_load_hot_slot_models"
)
async def load_hot_slot_models_endpoint(
    request: Request,
    keep_alive: str = "1h",
    current_user: dict = Depends(get_current_user)
):
    """Load all hot slot models into memory"""
    from api.services import chat

    try:
        result = await chat.load_hot_slot_models(keep_alive)
        return SuccessResponse(data=result, message="Hot slot models loaded")
    except Exception as e:
        logger.error(f"Failed to load hot slots: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to load hot slots"
            ).model_dump()
        )


# ===== Ollama Server Management =====

@router.get(
    "/system/memory",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_get_system_memory"
)
async def get_system_memory_endpoint():
    """Get system memory stats (public endpoint)"""
    from api.services import chat

    try:
        memory_stats = await chat.get_system_memory()
        return SuccessResponse(data=memory_stats, message="System memory retrieved")
    except Exception as e:
        logger.error(f"Failed to get system memory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get system memory"
            ).model_dump()
        )


@router.get(
    "/ollama/server/status",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_get_ollama_server_status"
)
async def get_ollama_server_status_endpoint():
    """Check if Ollama server is running (public endpoint)"""
    from api.services import chat

    try:
        server_status = await chat.get_ollama_server_status()
        return SuccessResponse(data=server_status, message="Server status retrieved")
    except Exception as e:
        logger.debug(f"Ollama server check failed: {e}")
        # Return default status instead of raising error for this endpoint
        default_status = {"running": False, "loaded_models": [], "model_count": 0}
        return SuccessResponse(data=default_status, message="Server not running")


@router.post(
    "/ollama/server/shutdown",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_shutdown_ollama_server"
)
async def shutdown_ollama_server_endpoint(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Shutdown Ollama server"""
    from api.services import chat

    try:
        result = await chat.shutdown_ollama_server()
        return SuccessResponse(data=result, message="Ollama server shutdown initiated")
    except Exception as e:
        logger.error(f"Failed to shutdown Ollama: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to shutdown Ollama server"
            ).model_dump()
        )


@router.post(
    "/ollama/server/start",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_start_ollama_server"
)
async def start_ollama_server_endpoint(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Start Ollama server in background"""
    from api.services import chat

    try:
        result = await chat.start_ollama_server()
        return SuccessResponse(data=result, message="Ollama server start initiated")
    except Exception as e:
        logger.error(f"Failed to start Ollama: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to start Ollama server"
            ).model_dump()
        )


@router.post(
    "/ollama/server/restart",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_restart_ollama_server"
)
async def restart_ollama_server_endpoint(
    request: Request,
    reload_models: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """Restart Ollama server and optionally reload specific models"""
    from api.services import chat
    from api.schemas.chat_models import RestartServerRequest

    try:
        body_data = await request.json() if request.method == "POST" else None
        body = RestartServerRequest(**body_data) if body_data else None

        result = await chat.restart_ollama_server(
            reload_models=reload_models,
            models_to_load=body.models_to_load if body else None
        )

        return SuccessResponse(data=result, message="Ollama server restart initiated")
    except Exception as e:
        logger.error(f"Failed to restart Ollama: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to restart Ollama server"
            ).model_dump()
        )


# ===== Model Download/Delete Operations =====

@router.post(
    "/models/pull/{model_name}",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    name="chat_pull_model"
)
async def pull_model_endpoint(
    model_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Pull/download a model from Ollama library with streaming progress updates

    Returns a Server-Sent Events stream with progress updates in JSON format:
    - {"status": "progress", "message": "pulling manifest", "model": "qwen2.5-coder:7b"}
    - {"status": "completed", "message": "Successfully pulled...", "model": "qwen2.5-coder:7b"}
    - {"status": "error", "message": "Error message", "model": "qwen2.5-coder:7b"}
    """
    from api.services.chat.ollama_ops import pull_model
    import json

    async def event_stream():
        """Stream progress updates as Server-Sent Events"""
        try:
            async for update in pull_model(model_name):
                # Format as SSE data
                yield f"data: {json.dumps(update)}\n\n"
        except Exception as e:
            logger.error(f"Error in pull stream: {e}", exc_info=True)
            error_update = {
                "status": "error",
                "message": str(e),
                "model": model_name
            }
            yield f"data: {json.dumps(error_update)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.delete(
    "/models/{model_name}",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_remove_model"
)
async def remove_model_endpoint(
    model_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove/delete a local model using ollama rm"""
    from api.services.chat.ollama_ops import remove_model

    try:
        result = await remove_model(model_name)

        if result["status"] == "success":
            return SuccessResponse(
                data=result,
                message=f"Model '{model_name}' removed successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message=result["message"]
                ).model_dump()
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove model: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to remove model"
            ).model_dump()
        )


@router.get(
    "/ollama/version",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_get_ollama_version"
)
async def get_ollama_version_endpoint():
    """Check installed Ollama version (public endpoint)"""
    from api.services.chat.ollama_ops import check_ollama_version

    try:
        version_info = await check_ollama_version()
        return SuccessResponse(data=version_info, message="Ollama version retrieved")
    except Exception as e:
        logger.error(f"Failed to check Ollama version: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to check Ollama version"
            ).model_dump()
        )


# ===== Model Discovery (Ollama Library) =====

@router.get(
    "/models/library",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="chat_browse_ollama_library"
)
async def browse_ollama_library_endpoint(
    search: Optional[str] = None,
    model_type: Optional[str] = None,
    capability: Optional[str] = None,
    sort_by: Optional[str] = "pulls",
    order: Optional[str] = "desc",
    limit: int = 20,
    skip: int = 0
):
    """
    Browse Ollama model library with search and filtering (public endpoint)

    Proxies requests to ollamadb.dev API for model discovery

    Query Parameters:
    - search: Search models by name or description
    - model_type: Filter by 'official' or 'community'
    - capability: Filter by capability (e.g., 'code', 'chat', 'vision')
    - sort_by: Sort by 'pulls' or 'last_updated' (default: 'pulls')
    - order: Sort order 'asc' or 'desc' (default: 'desc')
    - limit: Results per page (default: 20, max: 100)
    - skip: Results to skip for pagination (default: 0)
    """
    import httpx

    try:
        # Build query parameters
        params = {
            "sort_by": sort_by,
            "order": order,
            "limit": min(limit, 100),  # Cap at 100
            "skip": skip
        }

        if search:
            params["search"] = search
        if model_type:
            params["model_type"] = model_type
        if capability:
            params["capability"] = capability

        # Fetch from ollamadb.dev API
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://ollamadb.dev/api/v1/models",
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                return SuccessResponse(
                    data=data,
                    message="Ollama library models retrieved"
                )
            else:
                logger.error(f"ollamadb.dev API error: {response.status_code}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=ErrorResponse(
                        error_code=ErrorCode.GATEWAY_ERROR,
                        message=f"Upstream API error: {response.status_code}"
                    ).model_dump()
                )

    except httpx.TimeoutException:
        logger.error("Timeout fetching from ollamadb.dev", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=ErrorResponse(
                error_code=ErrorCode.TIMEOUT,
                message="Upstream API timeout"
            ).model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to browse Ollama library: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to browse Ollama library"
            ).model_dump()
        )


# NOTE: Additional endpoints from original chat.py include:
# - ANE Context endpoints (lines 410-452)
# - Embedding info endpoint (line 442-452)
# - Adaptive router endpoints (lines 942-990)
# - Router mode endpoints (lines 994-1036)
# - Recursive prompt endpoints (lines 1040-1072)
# - Ollama configuration endpoints (lines 1076-1119)
# - Performance monitoring endpoints (lines 1123-1186)
# - Panic mode endpoints (lines 1190-1239)
# - Learning system endpoints (lines 1243-1357)
# - Data export endpoint (lines 840-862)
# - Model recommendation endpoints
# For complete implementation, extract these from the original file
