"""
Kanban Columns Routes

Provides CRUD operations for columns within kanban boards.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth_middleware import get_current_user
from api.services import kanban_service as kb
from api.routes.schemas import SuccessResponse
from api.errors import http_400, http_404, http_500

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/kanban", tags=["kanban-columns"])


class ColumnCreate(BaseModel):
    board_id: str
    name: str = Field(min_length=1, max_length=120)
    position: Optional[float] = None


class ColumnUpdate(BaseModel):
    name: Optional[str] = None
    position: Optional[float] = None


class ColumnItem(BaseModel):
    column_id: str
    board_id: str
    name: str
    position: float


@router.get(
    "/boards/{board_id}/columns",
    response_model=SuccessResponse[List[ColumnItem]],
    status_code=status.HTTP_200_OK,
    name="list_board_columns",
    summary="List columns",
    description="List all columns in a kanban board"
)
async def list_columns(
    board_id: str,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[List[ColumnItem]]:
    """List all columns in a board"""
    try:
        columns = [ColumnItem(**c) for c in kb.list_columns(board_id)]
        return SuccessResponse(
            data=columns,
            message=f"Retrieved {len(columns)} column(s)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list columns for board {board_id}", exc_info=True)
        raise http_500("Failed to retrieve columns")


@router.post(
    "/columns",
    response_model=SuccessResponse[ColumnItem],
    status_code=status.HTTP_201_CREATED,
    name="create_board_column",
    summary="Create column",
    description="Create a new column in a kanban board"
)
async def create_column(
    body: ColumnCreate,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[ColumnItem]:
    """Create a new column in a board"""
    try:
        c = kb.create_column(body.board_id, body.name, body.position)
        return SuccessResponse(
            data=ColumnItem(**c),
            message=f"Column '{body.name}' created successfully"
        )

    except ValueError as e:
        if "not found" in str(e).lower():
            raise http_404(str(e), resource="column")
        raise http_400(str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to create column", exc_info=True)
        raise http_500("Failed to create column")


@router.patch(
    "/columns/{column_id}",
    response_model=SuccessResponse[ColumnItem],
    status_code=status.HTTP_200_OK,
    name="update_board_column",
    summary="Update column",
    description="Update column name or position (partial updates supported)"
)
async def update_column(
    column_id: str,
    body: ColumnUpdate,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[ColumnItem]:
    """Update column name or position"""
    try:
        c = kb.update_column(column_id, body.name, body.position)
        return SuccessResponse(
            data=ColumnItem(**c),
            message="Column updated successfully"
        )

    except ValueError as e:
        raise http_404(str(e), resource="column")

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to update column {column_id}", exc_info=True)
        raise http_500("Failed to update column")

