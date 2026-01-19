"""
Kanban Projects Routes

Provides CRUD operations for kanban projects.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth_middleware import get_current_user
from api.services import kanban_service as kb
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/kanban", tags=["kanban-projects"])


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None


class ProjectItem(BaseModel):
    project_id: str
    name: str
    description: Optional[str]
    created_at: str


@router.get(
    "/projects",
    response_model=SuccessResponse[List[ProjectItem]],
    status_code=status.HTTP_200_OK,
    name="list_kanban_projects",
    summary="List projects",
    description="List all kanban projects"
)
async def list_projects(
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[List[ProjectItem]]:
    """List all kanban projects"""
    try:
        projects = [ProjectItem(**p) for p in kb.list_projects()]
        return SuccessResponse(
            data=projects,
            message=f"Retrieved {len(projects)} project(s)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list projects", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve projects"
            ).model_dump()
        )


@router.post(
    "/projects",
    response_model=SuccessResponse[ProjectItem],
    status_code=status.HTTP_201_CREATED,
    name="create_kanban_project",
    summary="Create project",
    description="Create a new kanban project"
)
async def create_project(
    body: ProjectCreate,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[ProjectItem]:
    """Create a new kanban project"""
    try:
        proj = kb.create_project(body.name, body.description)
        return SuccessResponse(
            data=ProjectItem(**proj),
            message=f"Project '{body.name}' created successfully"
        )

    except ValueError as e:
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
        logger.error(f"Failed to create project", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to create project"
            ).model_dump()
        )

