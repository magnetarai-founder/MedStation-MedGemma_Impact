from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth_middleware import get_current_user
from api.services import kanban_service as kb


router = APIRouter(prefix="/api/v1/kanban", tags=["kanban-projects"], dependencies=[Depends(get_current_user)])


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None


class ProjectItem(BaseModel):
    project_id: str
    name: str
    description: Optional[str]
    created_at: str


@router.get("/projects", response_model=List[ProjectItem])
async def list_projects():
    return [ProjectItem(**p) for p in kb.list_projects()]


@router.post("/projects", response_model=ProjectItem)
async def create_project(body: ProjectCreate):
    try:
        proj = kb.create_project(body.name, body.description)
        return ProjectItem(**proj)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create project: {str(e)}")

