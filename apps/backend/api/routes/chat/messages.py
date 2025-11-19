"""
Chat Messages Routes - Message operations, search, analytics
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user
from api.permission_engine import require_perm_team

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/sessions/{chat_id}/messages", name="chat_send_message")
@require_perm_team("chat.use")
async def send_message_endpoint(
    request: Request,
    chat_id: str,
    current_user: dict = Depends(get_current_user),
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
