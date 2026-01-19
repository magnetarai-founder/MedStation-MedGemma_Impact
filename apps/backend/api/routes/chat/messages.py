"""
Chat Messages Routes - Message operations, search, analytics

Provides endpoints for managing chat messages:
- Get messages for a session
- Send messages (streaming responses)
- Semantic search across conversations
- Session and global analytics

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException, Request, Depends, Query, status, Body
from fastapi.responses import StreamingResponse

from api.auth_middleware import get_current_user, User
from api.utils import get_user_id, get_user_role
from api.permission_engine import require_perm_team
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from api.errors import http_404, http_500
from api.schemas.chat_models import SendMessageRequest

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["chat-messages"]
)


@router.get(
    "/sessions/{chat_id}/messages",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="chat_get_messages",
    summary="Get messages",
    description="Get messages for a chat session with pagination"
)
@require_perm_team("chat.use")
async def get_messages(
    chat_id: str,
    limit: Optional[int] = Query(None, description="Maximum number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip (for pagination)"),
    team_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Get messages for a session with pagination support"""
    from api.services import chat as chat_service
    from api.services.chat.core.messages import count_messages

    try:
        user_id = get_user_id(current_user)
        role = get_user_role(current_user)

        # Verify session exists and user has access
        session = await chat_service.get_session(
            chat_id,
            user_id=user_id,
            role=role,
            team_id=team_id
        )

        if not session:
            raise http_404("Chat session not found or access denied", resource="session")

        # Load messages with pagination
        messages = await chat_service.get_messages(chat_id, limit=limit, offset=offset)

        # Get total count for pagination info
        total_count = await count_messages(chat_id)
        has_more = (offset + len(messages)) < total_count if limit else False

        return SuccessResponse(
            data={
                "messages": messages,
                "total": len(messages),
                "total_count": total_count,
                "offset": offset,
                "has_more": has_more,
                "session_id": chat_id
            },
            message=f"Retrieved {len(messages)} message(s)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to load messages", exc_info=True)
        raise http_500("Failed to retrieve messages")


@router.post(
    "/sessions/{chat_id}/messages",
    status_code=status.HTTP_201_CREATED,
    name="chat_send_message",
    summary="Send message (streaming)",
    description="Send a message and receive streaming AI response (Server-Sent Events)"
)
@require_perm_team("chat.use")
async def send_message(
    chat_id: str,
    body: SendMessageRequest = Body(...),
    current_user: User = Depends(get_current_user),
    team_id: Optional[str] = None
) -> StreamingResponse:
    """Send a message and get streaming response"""
    from api.services import chat as chat_service

    try:
        user_id = get_user_id(current_user)
        role = get_user_role(current_user)

        # Verify session exists
        session = await chat_service.get_session(
            chat_id,
            user_id=user_id,
            role=role,
            team_id=team_id
        )

        if not session:
            raise http_404("Chat session not found or access denied", resource="session")

        # Use model from body or session default
        model = body.model or session.get("model", "qwen2.5-coder:7b-instruct")

        # Stream response using service layer
        return StreamingResponse(
            chat_service.send_message_stream(
                chat_id=chat_id,
                content=body.content,
                user_id=user_id,
                role=role,
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
        logger.error(f"Failed to send message", exc_info=True)
        raise http_500("Failed to send message")


@router.get(
    "/search",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="chat_semantic_search",
    summary="Semantic search",
    description="Search across conversations using semantic similarity"
)
@require_perm_team("chat.use")
async def semantic_search(
    query: str = Query(..., min_length=3, description="Search query (minimum 3 characters)"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    team_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Search across conversations using semantic similarity"""
    from api.services import chat

    try:
        user_id = get_user_id(current_user)
        result = await chat.semantic_search(query, limit, user_id, team_id)

        return SuccessResponse(
            data=result,
            message=f"Found {result.get('total', 0)} matching message(s)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to search", exc_info=True)
        raise http_500("Failed to perform semantic search")


@router.get(
    "/analytics",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="chat_get_analytics",
    summary="Get analytics",
    description="Get analytics for a session or global analytics (scoped to user/team)"
)
@require_perm_team("chat.use")
async def get_analytics(
    session_id: Optional[str] = Query(None, description="Specific session ID (omit for global analytics)"),
    team_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Get analytics for a session or scoped analytics"""
    from api.services import chat

    try:
        user_id = get_user_id(current_user)
        analytics = await chat.get_analytics(session_id, user_id, team_id)

        return SuccessResponse(
            data=analytics,
            message="Analytics retrieved successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get analytics", exc_info=True)
        raise http_500("Failed to retrieve analytics")


@router.get(
    "/sessions/{chat_id}/analytics",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="chat_get_session_analytics",
    summary="Get session analytics",
    description="Get detailed analytics for a specific chat session"
)
@require_perm_team("chat.use")
async def get_session_analytics(
    chat_id: str,
    team_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Get detailed analytics for a specific session"""
    from api.services import chat

    try:
        user_id = get_user_id(current_user)
        role = get_user_role(current_user)

        # Verify session access
        session = await chat.get_session(chat_id, user_id, role, team_id)
        if not session:
            raise http_404("Chat session not found or access denied", resource="session")

        # Get analytics
        analytics = await chat.get_session_analytics(chat_id)

        return SuccessResponse(
            data={
                "session_id": chat_id,
                "title": session.get("title"),
                "stats": analytics.get("stats"),
                "topics": analytics.get("topics"),
                "team_id": team_id
            },
            message="Session analytics retrieved successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get session analytics", exc_info=True)
        raise http_500("Failed to retrieve session analytics")
