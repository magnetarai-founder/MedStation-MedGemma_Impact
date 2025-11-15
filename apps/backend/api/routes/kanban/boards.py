from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth_middleware import get_current_user
from api.services import kanban_service as kb


router = APIRouter(prefix="/api/v1/kanban", tags=["kanban-boards"], dependencies=[Depends(get_current_user)])


class BoardCreate(BaseModel):
    project_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=200)


class BoardItem(BaseModel):
    board_id: str
    project_id: str
    name: str
    created_at: str


@router.get("/projects/{project_id}/boards", response_model=List[BoardItem])
async def list_boards(project_id: str):
    return [BoardItem(**b) for b in kb.list_boards(project_id)]


@router.post("/boards", response_model=BoardItem)
async def create_board(body: BoardCreate):
    try:
        b = kb.create_board(body.project_id, body.name)
        return BoardItem(**b)
    except ValueError as e:
        # ValueError includes "project not found" and validation errors
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create board: {str(e)}")

