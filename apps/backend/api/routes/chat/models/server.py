"""
Ollama Server Management Routes - Server control, memory, status

Split from models.py for maintainability.
"""

import logging
from fastapi import APIRouter, HTTPException, Request, Depends, status

from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from api.auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


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
