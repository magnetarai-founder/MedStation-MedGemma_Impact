"""
Chat Sessions Routes - Session CRUD operations

Provides endpoints for managing chat sessions:
- Create, list, get, delete chat sessions
- Update session model, title, archive status
- Token counting and model preferences
- Team-based access control

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException, Request, Depends, Query, status

try:
    from api.auth_middleware import get_current_user, User
except ImportError:
    from auth_middleware import get_current_user, User
from api.permission_engine import require_perm_team
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["chat-sessions"]
)


@router.post(
    "/sessions",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="chat_create_session",
    summary="Create chat session",
    description="Create a new chat session for the current user"
)
@require_perm_team("chat.use")
async def create_chat_session(
    body: 'CreateChatRequest',
    current_user: User = Depends(get_current_user),
    team_id: Optional[str] = None
) -> SuccessResponse[Dict]:
    """Create a new chat session"""
    from api.services import chat
    from api.schemas.chat_models import CreateChatRequest, ChatSession

    try:
        result = await chat.create_session(
            title=body.title or "New Chat",
            model=body.model,
            user_id=current_user.get("user_id") if isinstance(current_user, dict) else current_user.user_id,
            team_id=team_id
        )

        return SuccessResponse(
            data=ChatSession(**result).model_dump(),
            message="Chat session created successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to create chat session", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to create chat session"
            ).model_dump()
        )


@router.get(
    "/sessions",
    response_model=SuccessResponse[List[Dict]],
    status_code=status.HTTP_200_OK,
    name="chat_list_sessions",
    summary="List chat sessions",
    description="List all chat sessions for the current user, sorted by last updated"
)
async def list_chat_sessions(
    current_user: User = Depends(get_current_user),
    team_id: Optional[str] = None
) -> SuccessResponse[List[Dict]]:
    """List all chat sessions for current user"""
    from api.services import chat
    from api.schemas.chat_models import ChatSession

    try:
        user_id = current_user.get("user_id") if isinstance(current_user, dict) else current_user.user_id
        role = current_user.get("role") if isinstance(current_user, dict) else getattr(current_user, "role", None)

        sessions = await chat.list_sessions(
            user_id=user_id,
            role=role,
            team_id=team_id
        )

        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)

        session_list = [ChatSession(**s).model_dump() for s in sessions]
        return SuccessResponse(
            data=session_list,
            message=f"Found {len(session_list)} chat session(s)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list chat sessions", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve chat sessions"
            ).model_dump()
        )


@router.get(
    "/sessions/{chat_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="chat_get_session",
    summary="Get chat session",
    description="Get chat session with message history"
)
@require_perm_team("chat.use")
async def get_chat_session(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    limit: Optional[int] = Query(None, description="Maximum number of messages to return"),
    team_id: Optional[str] = None
) -> SuccessResponse[Dict]:
    """Get chat session with message history"""
    from api.services import chat
    from api.schemas.chat_models import ChatSession

    try:
        user_id = current_user.get("user_id") if isinstance(current_user, dict) else current_user.user_id
        role = current_user.get("role") if isinstance(current_user, dict) else getattr(current_user, "role", None)

        session = await chat.get_session(
            chat_id,
            user_id=user_id,
            role=role,
            team_id=team_id
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Chat session not found or access denied"
                ).model_dump()
            )

        messages = await chat.get_messages(chat_id, limit=limit)

        return SuccessResponse(
            data={
                "session": ChatSession(**session).model_dump(),
                "messages": messages
            },
            message="Chat session retrieved successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get chat session", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve chat session"
            ).model_dump()
        )


@router.delete(
    "/sessions/{chat_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="chat_delete_session",
    summary="Delete chat session",
    description="Delete a chat session permanently"
)
async def delete_chat_session(
    chat_id: str,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Delete a chat session"""
    from api.services import chat

    try:
        user_id = current_user.get("user_id") if isinstance(current_user, dict) else current_user.user_id
        role = current_user.get("role") if isinstance(current_user, dict) else getattr(current_user, "role", None)

        deleted = await chat.delete_session(
            chat_id,
            user_id=user_id,
            role=role
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Chat session not found or access denied"
                ).model_dump()
            )

        return SuccessResponse(
            data={"status": "deleted", "chat_id": chat_id},
            message="Chat session deleted successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to delete chat session", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to delete chat session"
            ).model_dump()
        )


@router.patch(
    "/sessions/{chat_id}/model",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="chat_update_session_model",
    summary="Update session model",
    description="Update the model for a chat session (subject to team model policy)"
)
@require_perm_team("chat.use")
async def update_session_model(
    chat_id: str,
    model: str = Query(..., description="Model ID to use for this session"),
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Update the model for a chat session"""
    from api.services import chat
    from audit_logger import get_audit_logger, AuditAction
    from telemetry import track_metric, TelemetryMetric
    from api.services.team_model_policy import get_policy_service

    try:
        user_id = current_user.get("user_id") if isinstance(current_user, dict) else current_user.user_id

        # Verify session exists and user has access
        session = await chat.get_session(chat_id, user_id=user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Chat session not found"
                ).model_dump()
            )

        # Enforce team model policy
        team_id = session.get("team_id")
        if team_id:
            policy_service = get_policy_service()
            if not policy_service.is_model_allowed(team_id, model):
                try:
                    audit_logger = get_audit_logger()
                    audit_logger.log(
                        user_id=user_id,
                        action=AuditAction.MODEL_POLICY_VIOLATED,
                        resource="chat_session",
                        resource_id=chat_id,
                        details={"model": model, "team_id": team_id}
                    )
                except Exception as audit_error:
                    logger.warning(f"Audit logging failed: {audit_error}")

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ErrorResponse(
                        error_code=ErrorCode.FORBIDDEN,
                        message=f"Model '{model}' is not allowed by team policy",
                        details={"model": model, "team_id": team_id}
                    ).model_dump()
                )

        # Update model
        updated_session = await chat.update_session_model(chat_id, model)

        # Telemetry
        track_metric(TelemetryMetric.MODEL_SESSION_UPDATED)

        # Audit log
        try:
            audit_logger = get_audit_logger()
            audit_logger.log(
                user_id=user_id,
                action=AuditAction.SESSION_MODEL_UPDATED,
                resource="chat_session",
                resource_id=chat_id,
                details={"model": model, "previous_model": session.get("model")}
            )
        except Exception as audit_error:
            logger.warning(f"Audit logging failed: {audit_error}")

        return SuccessResponse(
            data=updated_session,
            message="Session model updated successfully"
        )

    except HTTPException:
        raise

    except ValueError as e:
        logger.error(f"ValueError updating session model", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code=ErrorCode.NOT_FOUND,
                message="Chat session not found"
            ).model_dump()
        )

    except Exception as e:
        logger.error(f"Failed to update session model", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update session model"
            ).model_dump()
        )


@router.patch(
    "/sessions/{chat_id}/rename",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="chat_rename_session",
    summary="Rename session",
    description="Update the title of a chat session"
)
@require_perm_team("chat.use")
async def rename_session(
    chat_id: str,
    title: str = Query(..., description="New title for the session"),
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Rename a chat session"""
    from api.services import chat

    try:
        user_id = current_user.get("user_id") if isinstance(current_user, dict) else current_user.user_id

        session = await chat.get_session(chat_id, user_id=user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Chat session not found"
                ).model_dump()
            )

        updated_session = await chat.update_session_title(chat_id, title)
        return SuccessResponse(
            data=updated_session,
            message="Session renamed successfully"
        )

    except HTTPException:
        raise

    except ValueError as e:
        logger.error(f"ValueError renaming session", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code=ErrorCode.NOT_FOUND,
                message="Chat session not found"
            ).model_dump()
        )

    except Exception as e:
        logger.error(f"Failed to rename session", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to rename session"
            ).model_dump()
        )


@router.patch(
    "/sessions/{chat_id}/archive",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="chat_archive_session",
    summary="Archive/unarchive session",
    description="Archive or unarchive a chat session"
)
@require_perm_team("chat.use")
async def archive_session(
    chat_id: str,
    archived: bool = Query(..., description="True to archive, False to unarchive"),
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Archive or unarchive a chat session"""
    from api.services import chat

    try:
        user_id = current_user.get("user_id") if isinstance(current_user, dict) else current_user.user_id

        session = await chat.get_session(chat_id, user_id=user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Chat session not found"
                ).model_dump()
            )

        updated_session = await chat.set_session_archived(chat_id, archived)
        return SuccessResponse(
            data=updated_session,
            message=f"Session {'archived' if archived else 'unarchived'} successfully"
        )

    except HTTPException:
        raise

    except ValueError as e:
        logger.error(f"ValueError archiving session", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code=ErrorCode.NOT_FOUND,
                message="Chat session not found"
            ).model_dump()
        )

    except Exception as e:
        logger.error(f"Failed to archive session", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to archive session"
            ).model_dump()
        )


@router.post(
    "/sessions/{chat_id}/token-count",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="chat_get_token_count",
    summary="Get token count",
    description="Get token count for a chat session (computed on-demand)"
)
async def get_token_count(
    chat_id: str,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Get token count for a chat session"""
    from api.services import chat

    try:
        user_id = current_user.get("user_id") if isinstance(current_user, dict) else current_user.user_id

        session = await chat.get_session(chat_id, user_id=user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Chat session not found"
                ).model_dump()
            )

        result = await chat.get_token_count(chat_id)
        return SuccessResponse(
            data=result,
            message="Token count retrieved successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get token count", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve token count"
            ).model_dump()
        )


@router.get(
    "/sessions/{chat_id}/token-count",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="chat_get_token_count_cached",
    summary="Get token count (cached)",
    description="Get token count for a chat session (GET variant with 30s cache)"
)
async def get_token_count_cached(
    chat_id: str,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Get token count for a chat session (GET variant with 30s cache)"""
    from api.services import chat
    import time

    # In-memory cache
    _token_count_cache: Dict[str, Dict] = {}
    _TOKEN_COUNT_CACHE_TTL = 30

    try:
        user_id = current_user.get("user_id") if isinstance(current_user, dict) else current_user.user_id

        session = await chat.get_session(chat_id, user_id=user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Chat session not found"
                ).model_dump()
            )

        # Check cache
        now = time.time()
        cached_entry = _token_count_cache.get(chat_id)

        if cached_entry and (now - cached_entry["timestamp"]) < _TOKEN_COUNT_CACHE_TTL:
            return SuccessResponse(
                data={**cached_entry["data"], "cached": True},
                message="Token count retrieved from cache"
            )

        # Cache miss - compute fresh count
        result = await chat.get_token_count(chat_id)

        # Add to cache
        token_data = {
            "session_id": chat_id,
            "total_tokens": result.get("total_tokens", 0),
            "max_tokens": result.get("max_tokens", 128000),
            "percentage": (result.get("total_tokens", 0) / result.get("max_tokens", 128000)) * 100 if result.get("max_tokens") else 0,
            "cached": False
        }

        _token_count_cache[chat_id] = {
            "data": token_data,
            "timestamp": now
        }

        return SuccessResponse(
            data=token_data,
            message="Token count computed successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get token count", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve token count"
            ).model_dump()
        )


# MARK: - Model Preferences (Phase 2: Intelligent Routing)

@router.get(
    "/sessions/{chat_id}/model-preferences",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="chat_get_model_preferences",
    summary="Get model preferences",
    description="Get model selection preferences for a chat session (intelligent vs manual mode)"
)
async def get_model_preferences(
    chat_id: str,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Get model selection preferences for a chat session"""
    from api.chat_memory import get_memory

    try:
        user_id = current_user.get("user_id") if isinstance(current_user, dict) else current_user.user_id

        # Verify session exists and user has access
        memory = get_memory()
        session = memory.get_session(chat_id, user_id=user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Chat session not found"
                ).model_dump()
            )

        # Get model preferences
        prefs = memory.get_model_preferences(chat_id)

        return SuccessResponse(
            data={
                "selected_mode": prefs["selected_mode"],
                "selected_model_id": prefs["selected_model_id"]
            },
            message="Model preferences retrieved successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get model preferences", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve model preferences"
            ).model_dump()
        )


# Pydantic model for model preferences update
class ModelPreferencesUpdate(BaseModel):
    """Model preferences update request"""
    selected_mode: str = Field(..., description="Model selection mode: 'intelligent' or 'manual'")
    selected_model_id: Optional[str] = Field(None, description="Specific model ID (required for manual mode)")


@router.put(
    "/sessions/{chat_id}/model-preferences",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="chat_update_model_preferences",
    summary="Update model preferences",
    description="Update model selection preferences for a chat session (intelligent routing vs manual selection)"
)
async def update_model_preferences(
    chat_id: str,
    body: ModelPreferencesUpdate,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Update model selection preferences for a chat session"""
    from api.chat_memory import get_memory
    from pydantic import Field

    try:
        user_id = current_user.get("user_id") if isinstance(current_user, dict) else current_user.user_id

        # Verify session exists and user has access
        memory = get_memory()
        session = memory.get_session(chat_id, user_id=user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Chat session not found"
                ).model_dump()
            )

        # Validate selected_mode
        if body.selected_mode not in ["intelligent", "manual"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="selected_mode must be 'intelligent' or 'manual'",
                    details={"field": "selected_mode", "value": body.selected_mode}
                ).model_dump()
            )

        # Update preferences
        memory.update_model_preferences(
            session_id=chat_id,
            selected_mode=body.selected_mode,
            selected_model_id=body.selected_model_id
        )

        return SuccessResponse(
            data={
                "status": "updated",
                "chat_id": chat_id,
                "selected_mode": body.selected_mode,
                "selected_model_id": body.selected_model_id
            },
            message="Model preferences updated successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to update model preferences", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update model preferences"
            ).model_dump()
        )
