"""
Chat Sessions Routes - Session CRUD operations
"""

import logging
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, Request, Depends

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user
from api.permission_engine import require_perm_team

logger = logging.getLogger(__name__)

router = APIRouter()


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


@router.patch("/sessions/{chat_id}/model", name="chat_update_session_model")
@require_perm_team("chat.use")
async def update_session_model_endpoint(
    request: Request,
    chat_id: str,
    model: str,
    current_user: dict = Depends(get_current_user)
):
    """Update the model for a chat session"""
    from api.services import chat
    from audit_logger import get_audit_logger, AuditAction
    from telemetry import track_metric, TelemetryMetric
    from api.services.team_model_policy import get_policy_service

    try:
        # Verify session exists and user has access
        session = await chat.get_session(chat_id, user_id=current_user["user_id"])
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        # Enforce team model policy
        team_id = session.get("team_id")
        if team_id:
            policy_service = get_policy_service()
            if not policy_service.is_model_allowed(team_id, model):
                try:
                    audit_logger = get_audit_logger()
                    audit_logger.log(
                        user_id=current_user["user_id"],
                        action=AuditAction.MODEL_POLICY_VIOLATED,
                        resource="chat_session",
                        resource_id=chat_id,
                        details={"model": model, "team_id": team_id}
                    )
                except Exception as audit_error:
                    logger.warning(f"Audit logging failed: {audit_error}")

                raise HTTPException(
                    status_code=403,
                    detail={
                        "code": "model_not_allowed",
                        "model": model,
                        "team_id": team_id,
                        "message": f"Model '{model}' is not allowed by team policy"
                    }
                )

        # Update model
        updated_session = await chat.update_session_model(chat_id, model)

        # Telemetry
        track_metric(TelemetryMetric.MODEL_SESSION_UPDATED)

        # Audit log
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
    title: str,
    current_user: dict = Depends(get_current_user)
):
    """Rename a chat session"""
    from api.services import chat

    try:
        session = await chat.get_session(chat_id, user_id=current_user["user_id"])
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

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
    archived: bool,
    current_user: dict = Depends(get_current_user)
):
    """Archive or unarchive a chat session"""
    from api.services import chat

    try:
        session = await chat.get_session(chat_id, user_id=current_user["user_id"])
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        updated_session = await chat.set_session_archived(chat_id, archived)
        return updated_session

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to archive session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
    """Get token count for a chat session (GET variant with 30s cache)"""
    from api.services import chat
    import time

    # In-memory cache
    _token_count_cache: Dict[str, Dict] = {}
    _TOKEN_COUNT_CACHE_TTL = 30

    try:
        session = await chat.get_session(chat_id, user_id=current_user["user_id"])
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        # Check cache
        now = time.time()
        cached_entry = _token_count_cache.get(chat_id)

        if cached_entry and (now - cached_entry["timestamp"]) < _TOKEN_COUNT_CACHE_TTL:
            return {**cached_entry["data"], "cached": True}

        # Cache miss - compute fresh count
        result = await chat.get_token_count(chat_id)

        # Add to cache
        _token_count_cache[chat_id] = {
            "data": {
                "session_id": chat_id,
                "total_tokens": result.get("total_tokens", 0),
                "max_tokens": result.get("max_tokens", 128000),
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
