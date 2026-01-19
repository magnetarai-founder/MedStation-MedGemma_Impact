"""
Kanban Boards Routes

Provides CRUD operations for kanban boards within projects.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth_middleware import get_current_user
from api.services import kanban_service as kb
from api.routes.schemas import SuccessResponse
from api.errors import http_400, http_404, http_500

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/kanban", tags=["kanban-boards"])


class BoardCreate(BaseModel):
    project_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=200)


class BoardItem(BaseModel):
    board_id: str
    project_id: str
    name: str
    created_at: str


@router.get(
    "/projects/{project_id}/boards",
    response_model=SuccessResponse[List[BoardItem]],
    status_code=status.HTTP_200_OK,
    name="list_kanban_boards",
    summary="List boards",
    description="List all kanban boards in a project"
)
async def list_boards(
    project_id: str,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[List[BoardItem]]:
    """List all boards in a project"""
    try:
        boards = [BoardItem(**b) for b in kb.list_boards(project_id)]
        return SuccessResponse(
            data=boards,
            message=f"Retrieved {len(boards)} board(s)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list boards for project {project_id}", exc_info=True)
        raise http_500("Failed to retrieve boards")


@router.post(
    "/boards",
    response_model=SuccessResponse[BoardItem],
    status_code=status.HTTP_201_CREATED,
    name="create_kanban_board",
    summary="Create board",
    description="Create a new kanban board in a project"
)
async def create_board(
    body: BoardCreate,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[BoardItem]:
    """Create a new kanban board"""
    try:
        b = kb.create_board(body.project_id, body.name)
        return SuccessResponse(
            data=BoardItem(**b),
            message=f"Board '{body.name}' created successfully"
        )

    except ValueError as e:
        # ValueError includes "project not found" and validation errors
        if "not found" in str(e).lower():
            raise http_404(str(e))
        raise http_400(str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to create board", exc_info=True)
        raise http_500("Failed to create board")

