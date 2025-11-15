from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth_middleware import get_current_user
from api.services import kanban_service as kb


router = APIRouter(prefix="/api/v1/kanban", tags=["kanban-columns"], dependencies=[Depends(get_current_user)])


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


@router.get("/boards/{board_id}/columns", response_model=List[ColumnItem])
async def list_columns(board_id: str):
    return [ColumnItem(**c) for c in kb.list_columns(board_id)]


@router.post("/columns", response_model=ColumnItem)
async def create_column(body: ColumnCreate):
    try:
        c = kb.create_column(body.board_id, body.name, body.position)
        return ColumnItem(**c)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create column: {str(e)}")


@router.patch("/columns/{column_id}", response_model=ColumnItem)
async def update_column(column_id: str, body: ColumnUpdate):
    try:
        c = kb.update_column(column_id, body.name, body.position)
        return ColumnItem(**c)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update column: {str(e)}")

