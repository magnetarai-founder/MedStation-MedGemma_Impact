from __future__ import annotations

from typing import List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user
from api.services import kanban_service as kb


router = APIRouter(prefix="/api/v1/kanban", tags=["kanban-tasks"], dependencies=[Depends(get_current_user)])


class TaskCreate(BaseModel):
    board_id: str
    column_id: str
    title: str = Field(min_length=1)
    description: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    tags: Optional[List[str]] = None
    position: Optional[float] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    tags: Optional[List[str]] = None
    column_id: Optional[str] = None
    position: Optional[float] = None
    before_task_id: Optional[str] = None
    after_task_id: Optional[str] = None


class TaskItem(BaseModel):
    task_id: str
    board_id: str
    column_id: str
    title: str
    description: Optional[str]
    status: Optional[str]
    assignee_id: Optional[str]
    priority: Optional[str]
    due_date: Optional[str]
    tags: List[str]
    position: float
    created_at: str
    updated_at: str


@router.get("/boards/{board_id}/tasks", response_model=List[TaskItem])
async def list_tasks(board_id: str, column_id: Optional[str] = Query(None)):
    tasks = kb.list_tasks(board_id, column_id)
    return [TaskItem(**t) for t in tasks]


@router.post("/tasks", response_model=TaskItem)
async def create_task(body: TaskCreate):
    try:
        t = kb.create_task(
            body.board_id,
            body.column_id,
            body.title,
            description=body.description,
            status=body.status,
            assignee_id=body.assignee_id,
            priority=body.priority,
            due_date=body.due_date,
            tags=body.tags,
            position=body.position,
        )
        return TaskItem(**t)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create task: {str(e)}")


@router.patch("/tasks/{task_id}", response_model=TaskItem)
async def update_task(task_id: str, body: TaskUpdate):
    try:
        # Move semantics if column_id or neighbor hints present
        if body.column_id is not None or body.before_task_id or body.after_task_id:
            # If column change is not set, fetch current column and keep it
            new_col = body.column_id
            if new_col is None:
                # Fetch by running a minimal update (no-op) to get current state
                current = kb.update_task(task_id)  # returns current state with tags as list
                new_col = current.get("column_id")
            moved = kb.move_task(
                task_id,
                new_col,  # type: ignore
                before_task_id=body.before_task_id,
                after_task_id=body.after_task_id,
            )
            # Apply other updates after move
            fields: dict[str, Any] = {}
            for k in [
                "title",
                "description",
                "status",
                "assignee_id",
                "priority",
                "due_date",
                "tags",
            ]:
                v = getattr(body, k)
                if v is not None:
                    fields[k] = v
            if fields:
                updated = kb.update_task(task_id, **fields)
                return TaskItem(**updated)
            return TaskItem(**moved)

        updated = kb.update_task(
            task_id,
            title=body.title,
            description=body.description,
            status=body.status,
            assignee_id=body.assignee_id,
            priority=body.priority,
            due_date=body.due_date,
            tags=body.tags,
            column_id=body.column_id,
            position=body.position,
        )
        return TaskItem(**updated)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update task: {str(e)}")

