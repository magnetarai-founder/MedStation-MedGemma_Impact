"""
Model Library Routes - Pull, remove, version check, and library browsing

Split from models.py for maintainability.
"""

import logging
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse

from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from api.errors import http_500

from api.auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


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
            raise http_500(result["message"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove model: {e}", exc_info=True)
        raise http_500("Failed to remove model")


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
        raise http_500("Failed to check Ollama version")


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
        raise http_500("Failed to browse Ollama library")
