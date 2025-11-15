from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth_middleware import get_current_user
from api.services import kanban_service as kb


router = APIRouter(prefix="/api/v1/kanban", tags=["kanban-comments"], dependencies=[Depends(get_current_user)])


class CommentCreate(BaseModel):
  task_id: str
  content: str = Field(min_length=1)


class CommentItem(BaseModel):
  comment_id: str
  task_id: str
  user_id: str
  content: str
  created_at: str


@router.get("/tasks/{task_id}/comments", response_model=List[CommentItem])
async def list_comments(task_id: str):
  return [CommentItem(**c) for c in kb.list_comments(task_id)]


@router.post("/comments", response_model=CommentItem)
async def create_comment(body: CommentCreate, current_user: dict = Depends(get_current_user)):
  try:
    c = kb.create_comment(body.task_id, current_user["user_id"], body.content)
    return CommentItem(**c)
  except ValueError as e:
    if "not found" in str(e).lower():
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
  except Exception as e:
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create comment: {str(e)}")

