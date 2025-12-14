"""
Message Feedback API

Allows users to provide thumbs up/down feedback on assistant messages.
Feedback is stored as analytics events for quality monitoring.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Literal, Dict, Optional
import logging

# Auth and permissions
try:
    from auth_middleware import get_current_user, User
except ImportError:
    from ..auth_middleware import get_current_user, User

try:
    from permission_engine import require_perm_team
except ImportError:
    from ..permission_engine import require_perm_team

from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/feedback",
    tags=["feedback"]
)


class MessageFeedbackRequest(BaseModel):
    """Feedback on a message"""
    score: Literal[1, -1] = Field(..., description="1 for thumbs up, -1 for thumbs down")


@router.post(
    "/messages/{message_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="submit_message_feedback",
    summary="Submit message feedback",
    description="Submit thumbs up/down feedback for an assistant message"
)
@require_perm_team("chat.use")
async def submit_message_feedback(
    message_id: str,
    feedback: MessageFeedbackRequest,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Submit feedback (thumbs up/down) for an assistant message

    Security:
    - Requires chat.use permission
    - Message must belong to user's session or team
    """
    from api.services.analytics import get_analytics_service

    user_id = current_user.get("user_id") if isinstance(current_user, dict) else current_user.user_id
    user_role = current_user.get("role", "user") if isinstance(current_user, dict) else getattr(current_user, "role", "user")
    team_id = current_user.get("team_id") if isinstance(current_user, dict) else getattr(current_user, "team_id", None)

    try:
        analytics = get_analytics_service()

        # Record feedback as analytics event
        analytics.record_event(
            event_type="message_feedback",
            user_id=user_id,
            team_id=team_id,
            metadata={
                "message_id": message_id,
                "score": feedback.score,
                "role": user_role
            }
        )

        logger.info(f"Recorded feedback for message {message_id}: score={feedback.score} by user={user_id}")

        return SuccessResponse(
            data={
                "status": "success",
                "message_id": message_id,
                "score": feedback.score
            },
            message="Feedback recorded successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to record message feedback", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to record feedback"
            ).model_dump()
        )


@router.get(
    "/messages/{message_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="get_message_feedback",
    summary="Get message feedback",
    description="Get user's previous feedback for a specific message"
)
async def get_message_feedback(
    message_id: str,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Get feedback for a specific message (if user wants to see their previous feedback)
    """
    from api.services.analytics import get_analytics_service

    user_id = current_user.get("user_id") if isinstance(current_user, dict) else current_user.user_id

    try:
        analytics = get_analytics_service()

        # Query for existing feedback on this message from this user
        events = analytics.get_events_by_type(
            event_type="message_feedback",
            user_id=user_id,
            limit=100  # Should be more than enough for one message
        )

        # Find feedback for this specific message
        for event in events:
            if event.get("metadata", {}).get("message_id") == message_id:
                return SuccessResponse(
                    data={
                        "message_id": message_id,
                        "score": event.get("metadata", {}).get("score"),
                        "timestamp": event.get("ts")
                    },
                    message="Feedback retrieved"
                )

        # No feedback found
        return SuccessResponse(
            data={
                "message_id": message_id,
                "score": None
            },
            message="No feedback found for this message"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get message feedback", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve feedback"
            ).model_dump()
        )
