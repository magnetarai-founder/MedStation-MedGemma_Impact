"""
Kanban Tasks Routes

Provides CRUD operations for tasks within kanban boards.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

from __future__ import annotations

import logging
from typing import List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from api.auth_middleware import get_current_user
from api.services import kanban_service as kb
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/kanban", tags=["kanban-tasks"])


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


@router.get(
    "/boards/{board_id}/tasks",
    response_model=SuccessResponse[List[TaskItem]],
    status_code=status.HTTP_200_OK,
    name="list_board_tasks",
    summary="List tasks",
    description="List all tasks in a kanban board, optionally filtered by column"
)
async def list_tasks(
    board_id: str,
    column_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[List[TaskItem]]:
    """List all tasks in a board, optionally filtered by column"""
    try:
        tasks_data = kb.list_tasks(board_id, column_id)
        tasks = [TaskItem(**t) for t in tasks_data]

        return SuccessResponse(
            data=tasks,
            message=f"Retrieved {len(tasks)} task(s)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list tasks for board {board_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve tasks"
            ).model_dump()
        )


@router.post(
    "/tasks",
    response_model=SuccessResponse[TaskItem],
    status_code=status.HTTP_201_CREATED,
    name="create_board_task",
    summary="Create task",
    description="Create a new task in a kanban board column"
)
async def create_task(
    body: TaskCreate,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[TaskItem]:
    """Create a new task in a board"""
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

        return SuccessResponse(
            data=TaskItem(**t),
            message=f"Task '{body.title}' created successfully"
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
        logger.error(f"Failed to create task", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to create task"
            ).model_dump()
        )


@router.patch(
    "/tasks/{task_id}",
    response_model=SuccessResponse[TaskItem],
    status_code=status.HTTP_200_OK,
    name="update_board_task",
    summary="Update task",
    description="Update task fields or move task to different column/position (partial updates supported)"
)
async def update_task(
    task_id: str,
    body: TaskUpdate,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[TaskItem]:
    """Update task fields or move task (supports drag-and-drop positioning)"""
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
                return SuccessResponse(
                    data=TaskItem(**updated),
                    message="Task updated and moved successfully"
                )
            return SuccessResponse(
                data=TaskItem(**moved),
                message="Task moved successfully"
            )

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

        return SuccessResponse(
            data=TaskItem(**updated),
            message="Task updated successfully"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code=ErrorCode.NOT_FOUND,
                message=str(e)
            ).model_dump()
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to update task {task_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update task"
            ).model_dump()
        )

