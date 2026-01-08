"""
Kanban Comments Routes

Provides CRUD operations for task comments in kanban boards.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from api.auth_middleware import get_current_user
try:
    from api.utils import get_user_id
except ImportError:
    from api.utils import get_user_id
from api.services import kanban_service as kb
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/kanban", tags=["kanban-comments"])


class CommentCreate(BaseModel):
  task_id: str
  content: str = Field(min_length=1)


class CommentItem(BaseModel):
  comment_id: str
  task_id: str
  user_id: str
  content: str
  created_at: str


@router.get(
    "/tasks/{task_id}/comments",
    response_model=SuccessResponse[List[CommentItem]],
    status_code=status.HTTP_200_OK,
    name="list_task_comments",
    summary="List comments",
    description="List all comments on a kanban task"
)
async def list_comments(
    task_id: str,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[List[CommentItem]]:
    """List all comments on a task"""
    try:
        comments = [CommentItem(**c) for c in kb.list_comments(task_id)]
        return SuccessResponse(
            data=comments,
            message=f"Retrieved {len(comments)} comment(s)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list comments for task {task_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve comments"
            ).model_dump()
        )


@router.post(
    "/comments",
    response_model=SuccessResponse[CommentItem],
    status_code=status.HTTP_201_CREATED,
    name="create_task_comment",
    summary="Create comment",
    description="Create a new comment on a kanban task"
)
async def create_comment(
    body: CommentCreate,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[CommentItem]:
    """Create a new comment on a task"""
    try:
        c = kb.create_comment(body.task_id, get_user_id(current_user), body.content)
        return SuccessResponse(
            data=CommentItem(**c),
            message="Comment created successfully"
        )

    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=str(e)
                ).model_dump()
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=str(e)
            ).model_dump()
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to create comment", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to create comment"
            ).model_dump()
        )

