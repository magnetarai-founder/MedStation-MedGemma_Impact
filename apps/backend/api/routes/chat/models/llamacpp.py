"""
llama.cpp Server Routes

Endpoints for:
- Server lifecycle (start, stop, status)
- Model loading
- Chat completion (streaming)
"""

import logging
import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from api.errors import http_500
from api.auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llamacpp", tags=["llamacpp"])


# ==============================================================================
# Request/Response Models
# ==============================================================================

class ServerStatusResponse(BaseModel):
    """llama.cpp server status"""
    running: bool
    model_loaded: Optional[str] = None
    model_path: Optional[str] = None
    pid: Optional[int] = None
    started_at: Optional[str] = None
    health_ok: bool = False
    port: int = 8080
    error: Optional[str] = None


class StartServerRequest(BaseModel):
    """Request to start llama.cpp server"""
    model_id: str = Field(..., description="Registry model ID (e.g., 'medgemma-1.5-4b-q4')")
    timeout: int = Field(default=120, description="Startup timeout in seconds")


class ChatMessage(BaseModel):
    """A chat message"""
    role: str = Field(..., description="Message role: 'system', 'user', or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat completion request"""
    messages: List[ChatMessage] = Field(..., description="Chat messages")
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=2048, ge=1, le=8192)
    top_p: Optional[float] = Field(default=0.9, ge=0.0, le=1.0)
    stream: bool = Field(default=True, description="Enable streaming response")


# ==============================================================================
# Server Lifecycle Endpoints
# ==============================================================================

@router.get(
    "/status",
    response_model=SuccessResponse[ServerStatusResponse],
    status_code=status.HTTP_200_OK,
    name="llamacpp_server_status"
)
async def get_server_status():
    """
    Get llama.cpp server status (public endpoint)

    Returns whether server is running, loaded model, and health status.
    """
    from api.services.llamacpp import get_llamacpp_server

    try:
        server = get_llamacpp_server()
        status_info = await server.get_status()

        return SuccessResponse(
            data=ServerStatusResponse(
                running=status_info.running,
                model_loaded=status_info.model_loaded,
                model_path=status_info.model_path,
                pid=status_info.pid,
                started_at=status_info.started_at.isoformat() if status_info.started_at else None,
                health_ok=status_info.health_ok,
                port=status_info.port,
                error=status_info.error,
            ),
            message="Server status retrieved"
        )

    except Exception as e:
        logger.error(f"Failed to get server status: {e}", exc_info=True)
        raise http_500("Failed to get server status")


@router.post(
    "/start",
    response_model=SuccessResponse[ServerStatusResponse],
    status_code=status.HTTP_200_OK,
    name="llamacpp_start_server"
)
async def start_server(
    request: StartServerRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Start llama.cpp server with a specific GGUF model

    The model must be downloaded first via the HuggingFace endpoints.
    This will stop any existing server and start with the new model.
    """
    from api.services.llamacpp import get_llamacpp_server
    from api.services.huggingface import get_gguf_registry
    from api.services.huggingface.storage import get_huggingface_storage

    try:
        # Validate model exists in registry
        registry = get_gguf_registry()
        model = registry.get_model(request.model_id)

        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Model not found in registry: {request.model_id}"
                ).model_dump()
            )

        # Check if model is downloaded
        storage = get_huggingface_storage()
        if not storage.is_model_downloaded(model.repo_id, model.filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.BAD_REQUEST,
                    message=f"Model not downloaded: {request.model_id}. Download it first via /huggingface/models/download"
                ).model_dump()
            )

        # Get model path
        model_path = str(storage.get_model_path(model.repo_id, model.filename))

        # Start server
        server = get_llamacpp_server()
        status_info = await server.start(
            model_path=model_path,
            model_name=model.name,
            wait_ready=True,
            timeout=request.timeout
        )

        if status_info.error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message=f"Failed to start server: {status_info.error}"
                ).model_dump()
            )

        return SuccessResponse(
            data=ServerStatusResponse(
                running=status_info.running,
                model_loaded=status_info.model_loaded,
                model_path=status_info.model_path,
                pid=status_info.pid,
                started_at=status_info.started_at.isoformat() if status_info.started_at else None,
                health_ok=status_info.health_ok,
                port=status_info.port,
                error=status_info.error,
            ),
            message=f"Server started with {model.name}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        raise http_500("Failed to start server")


@router.post(
    "/stop",
    response_model=SuccessResponse[ServerStatusResponse],
    status_code=status.HTTP_200_OK,
    name="llamacpp_stop_server"
)
async def stop_server(
    current_user: dict = Depends(get_current_user)
):
    """Stop the llama.cpp server"""
    from api.services.llamacpp import get_llamacpp_server

    try:
        server = get_llamacpp_server()
        status_info = await server.stop()

        return SuccessResponse(
            data=ServerStatusResponse(
                running=status_info.running,
                model_loaded=status_info.model_loaded,
                model_path=status_info.model_path,
                pid=status_info.pid,
                started_at=status_info.started_at.isoformat() if status_info.started_at else None,
                health_ok=status_info.health_ok,
                port=status_info.port,
                error=status_info.error,
            ),
            message="Server stopped"
        )

    except Exception as e:
        logger.error(f"Failed to stop server: {e}", exc_info=True)
        raise http_500("Failed to stop server")


@router.post(
    "/restart",
    response_model=SuccessResponse[ServerStatusResponse],
    status_code=status.HTTP_200_OK,
    name="llamacpp_restart_server"
)
async def restart_server(
    current_user: dict = Depends(get_current_user)
):
    """Restart the llama.cpp server with the same model"""
    from api.services.llamacpp import get_llamacpp_server

    try:
        server = get_llamacpp_server()
        status_info = await server.restart()

        if status_info.error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message=f"Failed to restart server: {status_info.error}"
                ).model_dump()
            )

        return SuccessResponse(
            data=ServerStatusResponse(
                running=status_info.running,
                model_loaded=status_info.model_loaded,
                model_path=status_info.model_path,
                pid=status_info.pid,
                started_at=status_info.started_at.isoformat() if status_info.started_at else None,
                health_ok=status_info.health_ok,
                port=status_info.port,
                error=status_info.error,
            ),
            message="Server restarted"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restart server: {e}", exc_info=True)
        raise http_500("Failed to restart server")


# ==============================================================================
# Chat Completion Endpoint
# ==============================================================================

@router.post(
    "/chat",
    status_code=status.HTTP_200_OK,
    name="llamacpp_chat_completion"
)
async def chat_completion(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Chat completion via llama.cpp server

    Supports streaming (SSE) and non-streaming responses.
    The llama.cpp server must be running with a loaded model.
    """
    from api.services.llamacpp import get_llamacpp_server, get_llamacpp_inference
    from api.services.llamacpp.inference import ChatMessage as InferenceChatMessage

    # Check server status
    server = get_llamacpp_server()
    status_info = await server.get_status()

    if not status_info.running or not status_info.health_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error_code=ErrorCode.SERVICE_UNAVAILABLE,
                message="llama.cpp server is not running. Start it first with /llamacpp/start"
            ).model_dump()
        )

    # Convert messages
    messages = [
        InferenceChatMessage(role=m.role, content=m.content)
        for m in request.messages
    ]

    inference = get_llamacpp_inference()

    if request.stream:
        # Streaming response
        async def event_stream():
            """Stream chat completion as Server-Sent Events"""
            full_response = ""

            try:
                async for chunk in inference.chat(
                    messages=messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    top_p=request.top_p,
                    stream=True
                ):
                    full_response += chunk.content

                    data = {
                        "content": chunk.content,
                        "finish_reason": chunk.finish_reason,
                        "model": chunk.model or status_info.model_loaded,
                    }
                    yield f"data: {json.dumps(data)}\n\n"

                    if chunk.finish_reason:
                        break

                # Final message with done marker
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"Error in chat stream: {e}", exc_info=True)
                error_data = {
                    "error": str(e),
                    "finish_reason": "error"
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    else:
        # Non-streaming response
        try:
            result = await inference.chat_sync(
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
            )

            return SuccessResponse(
                data={
                    "content": result.content,
                    "finish_reason": result.finish_reason,
                    "model": result.model,
                    "usage": result.usage,
                },
                message="Chat completion successful"
            )

        except Exception as e:
            logger.error(f"Chat completion failed: {e}", exc_info=True)
            raise http_500(f"Chat completion failed: {str(e)}")


# ==============================================================================
# Configuration Endpoint
# ==============================================================================

@router.get(
    "/config",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="llamacpp_get_config"
)
async def get_config():
    """Get llama.cpp configuration (public endpoint)"""
    from api.services.llamacpp import get_llamacpp_config

    try:
        config = get_llamacpp_config()

        return SuccessResponse(
            data={
                "host": config.host,
                "port": config.port,
                "context_size": config.context_size,
                "batch_size": config.batch_size,
                "n_gpu_layers": config.n_gpu_layers,
                "flash_attn": config.flash_attn,
                "binary_path": config.llama_cpp_path,
                "binary_found": config.llama_cpp_path is not None,
            },
            message="Configuration retrieved"
        )

    except Exception as e:
        logger.error(f"Failed to get config: {e}", exc_info=True)
        raise http_500("Failed to get configuration")
