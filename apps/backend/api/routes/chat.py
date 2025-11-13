"""
Chat router for ElohimOS - Chat management endpoints.

Thin router that delegates to api/services/chat.py for business logic.
Uses lazy imports in endpoints to avoid circular dependencies.

Includes both authenticated and public routers.
"""

import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request, Depends, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any

# Module-level safe imports
from auth_middleware import get_current_user
from permission_engine import require_perm_team

logger = logging.getLogger(__name__)

# Authenticated router (requires auth for most chat operations)
router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat"],
    dependencies=[Depends(get_current_user)]
)

# Public router (no auth required for health checks)
public_router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat-public"]
)


# ===== Session Management Endpoints =====

@router.post("/sessions", name="chat_create_session")
@require_perm_team("chat.use")
async def create_chat_session_endpoint(request: Request, current_user: Dict = Depends(get_current_user), team_id: Optional[str] = None):
    """Create a new chat session"""
    from api.services import chat
    from api.schemas.chat_models import CreateChatRequest, ChatSession

    try:
        body_data = await request.json()
        body = CreateChatRequest(**body_data)

        result = await chat.create_session(
            title=body.title or "New Chat",
            model=body.model or "qwen2.5-coder:7b-instruct",
            user_id=current_user["user_id"],
            team_id=team_id
        )

        return ChatSession(**result)
    except Exception as e:
        logger.error(f"Failed to create chat session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", name="chat_list_sessions")
async def list_chat_sessions_endpoint(request: Request, current_user: Dict = Depends(get_current_user), team_id: Optional[str] = None):
    """List all chat sessions for current user"""
    from api.services import chat
    from api.schemas.chat_models import ChatSession
    # Permission check: chat.use is required (manual check inline)

    try:
        sessions = await chat.list_sessions(
            user_id=current_user["user_id"],
            role=current_user.get("role"),
            team_id=team_id
        )

        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)

        return [ChatSession(**s) for s in sessions]
    except Exception as e:
        logger.error(f"Failed to list chat sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{chat_id}", name="chat_get_session")
@require_perm_team("chat.use")
async def get_chat_session_endpoint(
    request: Request,
    chat_id: str,
    current_user: Dict = Depends(get_current_user),
    limit: Optional[int] = None,
    team_id: Optional[str] = None
):
    """Get chat session with message history"""
    from api.services import chat
    from api.schemas.chat_models import ChatSession

    try:
        session = await chat.get_session(
            chat_id,
            user_id=current_user["user_id"],
            role=current_user.get("role"),
            team_id=team_id
        )

        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found or access denied")

        messages = await chat.get_messages(chat_id, limit=limit)

        return {
            "session": ChatSession(**session).model_dump(),
            "messages": messages
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chat session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{chat_id}", name="chat_delete_session")
async def delete_chat_session_endpoint(request: Request, chat_id: str, current_user: Dict = Depends(get_current_user)):
    """Delete a chat session"""
    from api.services import chat

    try:
        deleted = await chat.delete_session(
            chat_id,
            user_id=current_user["user_id"],
            role=current_user.get("role")
        )

        if not deleted:
            raise HTTPException(status_code=404, detail="Chat session not found or access denied")

        return {"status": "deleted", "chat_id": chat_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete chat session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Message Endpoints =====

@router.post("/sessions/{chat_id}/messages", name="chat_send_message")
@require_perm_team("chat.use")
async def send_message_endpoint(
    request: Request,
    chat_id: str,
    current_user: Dict = Depends(get_current_user),
    team_id: Optional[str] = None
):
    """Send a message and get streaming response"""
    from api.services import chat as chat_service
    from api.schemas.chat_models import SendMessageRequest

    try:
        # Verify session exists
        session = await chat_service.get_session(
            chat_id,
            user_id=current_user["user_id"],
            role=current_user.get("role"),
            team_id=team_id
        )

        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found or access denied")

        body_data = await request.json()
        body = SendMessageRequest(**body_data)

        # Use model from body or session default
        model = body.model or session.get("model", "qwen2.5-coder:7b-instruct")

        # Stream response using service layer
        return StreamingResponse(
            chat_service.send_message_stream(
                chat_id=chat_id,
                content=body.content,
                user_id=current_user["user_id"],
                role=current_user.get("role"),
                team_id=team_id,
                model=model,
                temperature=body.temperature,
                top_p=body.top_p,
                top_k=body.top_k,
                repeat_penalty=body.repeat_penalty,
                system_prompt=body.system_prompt,
                use_recursive=body.use_recursive
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== File Management Endpoints =====

@router.post("/sessions/{chat_id}/upload", name="chat_upload_file")
async def upload_file_to_chat_endpoint(
    request: Request,
    chat_id: str,
    file: UploadFile = File(...),
    current_user: Dict = Depends(get_current_user)
):
    """Upload a file to a chat session"""
    from api.services import chat

    try:
        # Verify session exists
        session = await chat.get_session(chat_id, user_id=current_user["user_id"])
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        # Read file content
        content = await file.read()

        # Upload file
        file_info = await chat.upload_file_to_chat(
            chat_id=chat_id,
            filename=file.filename or "upload",
            content=content,
            content_type=file.content_type or "application/octet-stream"
        )

        return file_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Model Management Endpoints =====

@public_router.get("/models", name="chat_list_models")
async def list_ollama_models_endpoint():
    """List available Ollama models (public endpoint)"""
    from api.services import chat
    from api.schemas.chat_models import OllamaModel

    try:
        models = await chat.list_ollama_models()
        return [OllamaModel(**m) for m in models]
    except Exception as e:
        logger.error(f"Failed to list models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/preload", name="chat_preload_model")
async def preload_model_endpoint(
    request: Request,
    model: str,
    keep_alive: str = "1h",
    source: str = "user_manual",  # Default to user manual for API calls
    current_user: dict = Depends(get_current_user)
):
    """
    Pre-load a model into memory

    Args:
        model: Model name to preload
        keep_alive: How long to keep model loaded (default: 1h)
        source: Source of request (e.g., "frontend_default", "hot_slot", "user_manual")
    """
    from api.services import chat
    # Permission check: chat.use is required (manual check inline)

    try:
        success = await chat.preload_model(model, keep_alive, source=source)

        if success:
            return {
                "status": "success",
                "model": model,
                "keep_alive": keep_alive,
                "source": source,
                "message": f"Model '{model}' pre-loaded successfully"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to pre-load model '{model}'"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to preload model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/unload/{model_name}", name="chat_unload_model")
async def unload_model_endpoint(request: Request, model_name: str, current_user: dict = Depends(get_current_user)):
    """Unload a specific model from memory"""
    from api.services import chat

    try:
        success = await chat.unload_model(model_name)

        if success:
            return {
                "status": "unloaded",
                "model": model_name,
                "message": f"Model '{model_name}' unloaded successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to unload model '{model_name}'")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unload model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Search & Analytics Endpoints =====

@router.get("/search", name="chat_semantic_search")
@require_perm_team("chat.use")
async def semantic_search_endpoint(
    query: str,
    limit: int = 10,
    team_id: Optional[str] = None,
    current_user: dict = None
):
    """Search across conversations using semantic similarity"""
    from api.services import chat

    if not query or len(query) < 3:
        raise HTTPException(status_code=400, detail="Query must be at least 3 characters")

    try:
        user_id = current_user.get("user_id")
        result = await chat.semantic_search(query, limit, user_id, team_id)
        return result
    except Exception as e:
        logger.error(f"Failed to search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics", name="chat_get_analytics")
@require_perm_team("chat.use")
async def get_analytics_endpoint(
    session_id: Optional[str] = None,
    team_id: Optional[str] = None,
    current_user: dict = None
):
    """Get analytics for a session or scoped analytics"""
    from api.services import chat

    try:
        user_id = current_user.get("user_id")
        analytics = await chat.get_analytics(session_id, user_id, team_id)
        return analytics
    except Exception as e:
        logger.error(f"Failed to get analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{chat_id}/analytics", name="chat_get_session_analytics")
@require_perm_team("chat.use")
async def get_session_analytics_endpoint(
    chat_id: str,
    team_id: Optional[str] = None,
    current_user: dict = None
):
    """Get detailed analytics for a specific session"""
    from api.services import chat

    try:
        user_id = current_user.get("user_id")
        role = current_user.get("role")

        # Verify session access
        session = await chat.get_session(chat_id, user_id, role, team_id)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found or access denied")

        # Get analytics
        analytics = await chat.get_session_analytics(chat_id)

        return {
            "session_id": chat_id,
            "title": session.get("title"),
            "stats": analytics.get("stats"),
            "topics": analytics.get("topics"),
            "team_id": team_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== ANE Context Endpoints =====

@router.get("/ane/stats", name="chat_get_ane_stats")
async def get_ane_stats_endpoint():
    """Get Apple Neural Engine context stats"""
    from api.services import chat

    try:
        stats = await chat.get_ane_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get ANE stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ane/search", name="chat_search_ane_context")
async def search_ane_context_endpoint(query: str, top_k: int = 5, threshold: float = 0.5):
    """Search for similar chat contexts using ANE-accelerated embeddings"""
    from api.services import chat

    if not query or len(query) < 3:
        raise HTTPException(status_code=400, detail="Query must be at least 3 characters")

    try:
        result = await chat.search_ane_context(query, top_k, threshold)
        return result
    except Exception as e:
        logger.error(f"Failed to search ANE context: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Embedding Info Endpoint =====

@router.get("/embedding/info", name="chat_get_embedding_info")
async def get_embedding_info_endpoint():
    """Get information about the embedding backend"""
    from api.services import chat

    try:
        info = await chat.get_embedding_info()
        return info
    except Exception as e:
        logger.error(f"Failed to get embedding info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Token Counting Endpoint =====

# In-memory cache for token counts (session_id -> {count, timestamp})
_token_count_cache: Dict[str, Dict] = {}
_TOKEN_COUNT_CACHE_TTL = 30  # seconds

@router.post("/sessions/{chat_id}/token-count", name="chat_get_token_count")
async def get_token_count_endpoint(request: Request, chat_id: str, current_user: dict = Depends(get_current_user)):
    """Get token count for a chat session"""
    from api.services import chat

    try:
        session = await chat.get_session(chat_id, user_id=current_user["user_id"])
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        result = await chat.get_token_count(chat_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get token count: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{chat_id}/token-count", name="chat_get_token_count_cached")
async def get_token_count_cached_endpoint(request: Request, chat_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get token count for a chat session (GET variant with 30s cache)

    Returns:
        {
            "session_id": str,
            "total_tokens": int,
            "max_tokens": int,
            "percentage": float,
            "cached": bool
        }
    """
    from api.services import chat
    import time

    try:
        # Verify session exists and user has access
        session = await chat.get_session(chat_id, user_id=current_user["user_id"])
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        # Check cache
        now = time.time()
        cached_entry = _token_count_cache.get(chat_id)

        if cached_entry and (now - cached_entry["timestamp"]) < _TOKEN_COUNT_CACHE_TTL:
            # Return cached value
            return {
                **cached_entry["data"],
                "cached": True
            }

        # Cache miss or expired - compute fresh count
        result = await chat.get_token_count(chat_id)

        # Add to cache
        _token_count_cache[chat_id] = {
            "data": {
                "session_id": chat_id,
                "total_tokens": result.get("total_tokens", 0),
                "max_tokens": result.get("max_tokens", 128000),  # Default context window
                "percentage": (result.get("total_tokens", 0) / result.get("max_tokens", 128000)) * 100 if result.get("max_tokens") else 0,
                "cached": False
            },
            "timestamp": now
        }

        return _token_count_cache[chat_id]["data"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get token count: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Session Model Update Endpoint =====

@router.patch("/sessions/{chat_id}/model", name="chat_update_session_model")
@require_perm_team("chat.use")
async def update_session_model_endpoint(
    request: Request,
    chat_id: str,
    model: str = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    Update the model for a chat session

    Body:
        {
            "model": "qwen2.5-coder:7b-instruct"
        }

    Returns updated session
    """
    from api.services import chat
    from audit_logger import get_audit_logger, AuditAction
    from telemetry import track_metric, TelemetryMetric

    try:
        # Verify session exists and user has access
        session = await chat.get_session(chat_id, user_id=current_user["user_id"])
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        # Update model
        updated_session = await chat.update_session_model(chat_id, model)

        # Telemetry (non-blocking, best-effort)
        track_metric(TelemetryMetric.MODEL_SESSION_UPDATED)

        # Audit log (non-blocking)
        try:
            audit_logger = get_audit_logger()
            audit_logger.log(
                user_id=current_user["user_id"],
                action=AuditAction.SESSION_MODEL_UPDATED,
                resource="chat_session",
                resource_id=chat_id,
                details={"model": model, "previous_model": session.get("model")}
            )
        except Exception as audit_error:
            logger.warning(f"Audit logging failed: {audit_error}")

        return updated_session

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update session model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/sessions/{chat_id}/rename", name="chat_rename_session")
@require_perm_team("chat.use")
async def rename_session_endpoint(
    request: Request,
    chat_id: str,
    title: str = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    Rename a chat session

    Body:
        {
            "title": "New Session Title"
        }

    Returns updated session
    """
    from api.services import chat

    try:
        # Verify session exists and user has access
        session = await chat.get_session(chat_id, user_id=current_user["user_id"])
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        # Update title
        updated_session = await chat.update_session_title(chat_id, title)
        return updated_session

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to rename session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/sessions/{chat_id}/archive", name="chat_archive_session")
@require_perm_team("chat.use")
async def archive_session_endpoint(
    request: Request,
    chat_id: str,
    archived: bool = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    Archive or unarchive a chat session

    Body:
        {
            "archived": true
        }

    Returns updated session
    """
    from api.services import chat

    try:
        # Verify session exists and user has access
        session = await chat.get_session(chat_id, user_id=current_user["user_id"])
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        # Update archived status
        updated_session = await chat.set_session_archived(chat_id, archived)
        return updated_session

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to archive session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Health & Status Endpoints (Public) =====

@public_router.get("/health", name="chat_check_health")
async def check_health_endpoint():
    """Check Ollama health status (public endpoint)"""
    from api.services import chat

    try:
        health = await chat.check_health()
        return health
    except Exception as e:
        logger.error(f"Failed to check health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@public_router.get("/models/status", name="chat_get_models_status")
async def get_models_status_endpoint():
    """Get status of all models (public endpoint)"""
    from api.services import chat

    try:
        status = await chat.get_models_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get models status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@public_router.get("/models/hot-slots", name="chat_get_hot_slots")
async def get_hot_slots_endpoint():
    """Get current hot slot assignments (public endpoint)"""
    from api.services import chat

    try:
        slots = await chat.get_hot_slots()
        return {"hot_slots": slots}
    except Exception as e:
        logger.error(f"Failed to get hot slots: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@public_router.get("/models/orchestrator-suitable", name="chat_get_orchestrator_suitable_models")
async def get_orchestrator_suitable_models_endpoint():
    """Get models suitable for orchestrator use (public endpoint)"""
    from api.services import chat

    try:
        models = await chat.get_orchestrator_suitable_models()
        return models
    except Exception as e:
        logger.error(f"Failed to get orchestrator models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@public_router.get("/ollama/server/status", name="chat_get_ollama_server_status")
async def get_ollama_server_status_endpoint():
    """Check if Ollama server is running (public endpoint)"""
    from api.services import chat

    try:
        status = await chat.get_ollama_server_status()
        return status
    except Exception as e:
        logger.debug(f"Ollama server check failed: {e}")
        return {"running": False, "loaded_models": [], "model_count": 0}


# ===== System Management Endpoints =====

@router.get("/system/memory", name="chat_get_system_memory")
async def get_system_memory_endpoint(request: Request, current_user: dict = Depends(get_current_user)):
    """Get actual system memory stats"""
    from api.services import chat

    try:
        memory = await chat.get_system_memory()
        return memory
    except Exception as e:
        logger.error(f"Failed to get system memory: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/ollama/server/shutdown", name="chat_shutdown_ollama_server")
async def shutdown_ollama_server_endpoint(request: Request, current_user: dict = Depends(get_current_user)):
    """Shutdown Ollama server"""
    from api.services import chat

    try:
        result = await chat.shutdown_ollama_server()
        return result
    except Exception as e:
        logger.error(f"Failed to shutdown Ollama: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ollama/server/start", name="chat_start_ollama_server")
async def start_ollama_server_endpoint(request: Request, current_user: dict = Depends(get_current_user)):
    """Start Ollama server in background"""
    from api.services import chat

    try:
        result = await chat.start_ollama_server()
        return result
    except Exception as e:
        logger.error(f"Failed to start Ollama: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ollama/server/restart", name="chat_restart_ollama_server")
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

        return result
    except Exception as e:
        logger.error(f"Failed to restart Ollama: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Data Export Endpoint =====

@router.post("/data/export-to-chat", name="chat_export_data_to_chat")
async def export_data_to_chat_endpoint(request: Request, current_user: dict = Depends(get_current_user)):
    """Export query results from Data tab to AI Chat"""
    from api.services import chat
    from api.schemas.chat_models import ExportToChatRequest

    try:
        body_data = await request.json()
        body = ExportToChatRequest(**body_data)

        result = await chat.export_data_to_chat(
            session_id=body.session_id,
            query_id=body.query_id,
            query=body.query,
            results=body.results,
            user_id=current_user["user_id"]
        )

        return result
    except Exception as e:
        logger.error(f"Failed to export to chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# ===== Model Hot Slots Endpoints =====

@router.post("/models/hot-slots/{slot_number}", name="chat_assign_to_hot_slot")
async def assign_to_hot_slot_endpoint(
    request: Request,
    slot_number: int,
    model_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Assign a model to a specific hot slot"""
    from api.services import chat

    if slot_number not in [1, 2, 3, 4]:
        raise HTTPException(status_code=400, detail="Slot number must be between 1 and 4")

    try:
        # Check if slot already occupied
        current_slots = await chat.get_hot_slots()
        if current_slots[slot_number] is not None:
            raise HTTPException(
                status_code=400,
                detail=f"Slot {slot_number} is already occupied by {current_slots[slot_number]}"
            )

        result = await chat.assign_to_hot_slot(slot_number, model_name)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign to hot slot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/models/hot-slots/{slot_number}", name="chat_remove_from_hot_slot")
async def remove_from_hot_slot_endpoint(
    request: Request,
    slot_number: int,
    current_user: dict = Depends(get_current_user)
):
    """Remove a model from a specific hot slot"""
    from api.services import chat

    if slot_number not in [1, 2, 3, 4]:
        raise HTTPException(status_code=400, detail="Slot number must be between 1 and 4")

    try:
        current_slots = await chat.get_hot_slots()
        if current_slots[slot_number] is None:
            raise HTTPException(status_code=400, detail=f"Slot {slot_number} is already empty")

        result = await chat.remove_from_hot_slot(slot_number)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove from hot slot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/load-hot-slots", name="chat_load_hot_slot_models")
async def load_hot_slot_models_endpoint(
    request: Request,
    keep_alive: str = "1h",
    current_user: dict = Depends(get_current_user)
):
    """Load all hot slot models into memory"""
    from api.services import chat

    try:
        result = await chat.load_hot_slot_models(keep_alive)
        return result
    except Exception as e:
        logger.error(f"Failed to load hot slots: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Adaptive Router Endpoints =====

@router.post("/adaptive-router/feedback", name="chat_submit_router_feedback")
async def submit_router_feedback_endpoint(request: Request, current_user: dict = Depends(get_current_user)):
    """Submit feedback for adaptive router to learn from"""
    from api.services import chat
    from api.schemas.chat_models import RouterFeedback

    try:
        body_data = await request.json()
        feedback = RouterFeedback(**body_data)

        result = await chat.submit_router_feedback(
            command=feedback.command,
            tool_used=feedback.tool_used,
            success=feedback.success,
            execution_time=feedback.execution_time,
            user_satisfaction=feedback.user_satisfaction
        )

        return result
    except Exception as e:
        logger.error(f"Failed to submit router feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/adaptive-router/stats", name="chat_get_router_stats")
async def get_router_stats_endpoint(request: Request, current_user: dict = Depends(get_current_user)):
    """Get adaptive router statistics and learning progress"""
    from api.services import chat

    try:
        stats = await chat.get_router_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get router stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/adaptive-router/explain", name="chat_explain_routing")
async def explain_routing_endpoint(command: str, current_user: dict = Depends(get_current_user)):
    """Explain how a command would be routed"""
    from api.services import chat

    try:
        explanation = await chat.explain_routing(command)
        return explanation
    except Exception as e:
        logger.error(f"Failed to explain routing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Router Mode Endpoints =====

@router.get("/router/mode", name="chat_get_router_mode")
async def get_router_mode_endpoint():
    """Get current router mode"""
    from api.services import chat

    try:
        mode = chat.get_router_mode()
        return mode
    except Exception as e:
        logger.error(f"Failed to get router mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/router/mode", name="chat_set_router_mode")
async def set_router_mode_endpoint(request: Request, mode: str, current_user: dict = Depends(get_current_user)):
    """Set router mode"""
    from api.services import chat

    if mode not in ['adaptive', 'ane']:
        raise HTTPException(status_code=400, detail="Mode must be 'adaptive' or 'ane'")

    try:
        result = chat.set_router_mode(mode)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to set router mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/router/stats", name="chat_get_combined_router_stats")
async def get_combined_router_stats_endpoint(request: Request, current_user: dict = Depends(get_current_user)):
    """Get combined stats from both routers"""
    from api.services import chat

    try:
        stats = await chat.get_combined_router_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get router stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Recursive Prompt Endpoints =====

@router.post("/recursive-prompt/execute", name="chat_execute_recursive_prompt")
async def execute_recursive_prompt_endpoint(request: Request, current_user: dict = Depends(get_current_user)):
    """Execute a query using recursive prompt decomposition"""
    from api.services import chat
    from api.schemas.chat_models import RecursiveQueryRequest

    try:
        body_data = await request.json()
        body = RecursiveQueryRequest(**body_data)

        result = await chat.execute_recursive_prompt(
            query=body.query,
            model=body.model
        )

        return result
    except Exception as e:
        logger.error(f"Failed to execute recursive prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recursive-prompt/stats", name="chat_get_recursive_stats")
async def get_recursive_stats_endpoint():
    """Get recursive prompt library statistics"""
    from api.services import chat

    try:
        stats = await chat.get_recursive_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get recursive stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Ollama Configuration Endpoints =====

@router.get("/ollama/config", name="chat_get_ollama_configuration")
async def get_ollama_configuration_endpoint():
    """Get current Ollama configuration"""
    from api.services import chat

    try:
        config = chat.get_ollama_configuration()
        return config
    except Exception as e:
        logger.error(f"Failed to get Ollama config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ollama/config/mode", name="chat_set_ollama_mode")
async def set_ollama_mode_endpoint(request: Request, current_user: dict = Depends(get_current_user)):
    """Set Ollama performance mode"""
    from api.services import chat
    from api.schemas.chat_models import SetModeRequest

    try:
        body_data = await request.json()
        body = SetModeRequest(**body_data)

        result = chat.set_ollama_mode(body.mode)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to set Ollama mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ollama/config/auto-detect", name="chat_auto_detect_ollama_config")
async def auto_detect_ollama_config_endpoint(request: Request, current_user: dict = Depends(get_current_user)):
    """Auto-detect optimal Ollama settings for current hardware"""
    from api.services import chat

    try:
        result = chat.auto_detect_ollama_config()
        return result
    except Exception as e:
        logger.error(f"Failed to auto-detect config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Performance Monitoring Endpoints =====

@router.get("/performance/current", name="chat_get_current_performance")
async def get_current_performance_endpoint():
    """Get current performance metrics"""
    from api.services import chat

    try:
        metrics = chat.get_current_performance()
        return metrics
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/stats", name="chat_get_performance_statistics")
async def get_performance_statistics_endpoint():
    """Get performance statistics over time"""
    from api.services import chat

    try:
        stats = chat.get_performance_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get performance stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/history", name="chat_get_performance_history")
async def get_performance_history_endpoint(last_n: int = 20):
    """Get recent performance history"""
    from api.services import chat

    try:
        history = chat.get_performance_history(last_n)
        return history
    except Exception as e:
        logger.error(f"Failed to get performance history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/thermal", name="chat_check_thermal_throttling")
async def check_thermal_throttling_endpoint():
    """Check for thermal throttling"""
    from api.services import chat

    try:
        thermal_check = chat.check_thermal_throttling()
        return thermal_check
    except Exception as e:
        logger.error(f"Failed to check thermal status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/performance/reset", name="chat_reset_performance_metrics")
async def reset_performance_metrics_endpoint(request: Request, current_user: dict = Depends(get_current_user)):
    """Reset performance metrics"""
    from api.services import chat

    try:
        result = chat.reset_performance_metrics()
        return result
    except Exception as e:
        logger.error(f"Failed to reset performance metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Panic Mode Endpoints =====

@router.post("/panic/trigger", name="chat_trigger_panic_mode")
async def trigger_panic_mode_endpoint(request: Request, current_user: dict = Depends(get_current_user)):
    """EMERGENCY: Trigger panic mode"""
    from api.services import chat
    from api.schemas.chat_models import PanicTriggerRequest

    try:
        body_data = await request.json()
        body = PanicTriggerRequest(**body_data)

        if body.confirmation != "CONFIRM":
            raise HTTPException(
                status_code=400,
                detail="Panic mode requires confirmation='CONFIRM'"
            )

        result = await chat.trigger_panic_mode(body.reason)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.critical(f"Panic mode execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/panic/status", name="chat_get_panic_status")
async def get_panic_status_endpoint():
    """Get current panic mode status"""
    from api.services import chat

    try:
        status = chat.get_panic_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get panic status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/panic/reset", name="chat_reset_panic_mode")
async def reset_panic_mode_endpoint(request: Request, current_user: dict = Depends(get_current_user)):
    """Reset panic mode (admin only)"""
    from api.services import chat

    try:
        result = chat.reset_panic_mode()
        return result
    except Exception as e:
        logger.error(f"Failed to reset panic mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== Learning System Endpoints =====

@router.get("/learning/patterns", name="chat_get_learning_patterns")
async def get_learning_patterns_endpoint(days: int = 30):
    """Get usage patterns and learning insights"""
    from api.services import chat

    try:
        patterns = await chat.get_learning_patterns(days)
        return patterns
    except Exception as e:
        logger.error(f"Failed to get learning patterns: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/recommendations", name="chat_get_recommendations")
async def get_recommendations_endpoint():
    """Get current classification recommendations"""
    from api.services import chat

    try:
        recommendations = await chat.get_recommendations()
        return recommendations
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning/recommendations/{recommendation_id}/accept", name="chat_accept_recommendation")
async def accept_recommendation_endpoint(
    request: Request,
    recommendation_id: int,
    feedback: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Accept a classification recommendation"""
    from api.services import chat

    try:
        success = await chat.accept_recommendation(recommendation_id, feedback)

        if success:
            return {"status": "success", "message": "Recommendation accepted"}
        else:
            raise HTTPException(status_code=400, detail="Failed to accept recommendation")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to accept recommendation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning/recommendations/{recommendation_id}/reject", name="chat_reject_recommendation")
async def reject_recommendation_endpoint(
    request: Request,
    recommendation_id: int,
    feedback: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Reject a classification recommendation"""
    from api.services import chat

    try:
        success = await chat.reject_recommendation(recommendation_id, feedback)

        if success:
            return {"status": "success", "message": "Recommendation rejected"}
        else:
            raise HTTPException(status_code=400, detail="Failed to reject recommendation")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reject recommendation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/optimal-model/{task_type}", name="chat_get_optimal_model")
async def get_optimal_model_endpoint(task_type: str, top_n: int = 3):
    """Get the optimal models for a specific task type"""
    from api.services import chat

    try:
        result = await chat.get_optimal_model_for_task(task_type, top_n)
        return result
    except Exception as e:
        logger.error(f"Failed to get optimal model for task '{task_type}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning/track-usage", name="chat_track_usage")
async def track_usage_manually_endpoint(
    request: Request,
    model_name: str,
    classification: Optional[str] = None,
    session_id: Optional[str] = None,
    message_count: int = 1,
    tokens_used: int = 0,
    task_detected: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Manually track model usage"""
    from api.services import chat

    try:
        result = await chat.track_usage_manually(
            model_name=model_name,
            classification=classification,
            session_id=session_id,
            message_count=message_count,
            tokens_used=tokens_used,
            task_detected=task_detected
        )
        return result
    except Exception as e:
        logger.error(f"Failed to track usage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Export routers
__all__ = ["router", "public_router"]
