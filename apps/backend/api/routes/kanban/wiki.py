from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user
from api.services import kanban_service as kb


router = APIRouter(prefix="/api/v1/kanban", tags=["kanban-wiki"], dependencies=[Depends(get_current_user)])


class WikiCreate(BaseModel):
    project_id: str
    title: str = Field(min_length=1, max_length=200)
    content: Optional[str] = None


class WikiUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class WikiItem(BaseModel):
    page_id: str
    project_id: str
    title: str
    content: Optional[str]
    created_at: str
    updated_at: str


@router.get("/projects/{project_id}/wiki", response_model=List[WikiItem])
async def list_wiki(project_id: str):
    return [WikiItem(**p) for p in kb.list_wiki_pages(project_id)]


@router.post("/wiki", response_model=WikiItem)
async def create_wiki(body: WikiCreate):
    try:
        p = kb.create_wiki_page(body.project_id, body.title, body.content)
        return WikiItem(**p)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create wiki page: {str(e)}")


@router.patch("/wiki/{page_id}", response_model=WikiItem)
async def update_wiki(page_id: str, body: WikiUpdate):
    try:
        p = kb.update_wiki_page(page_id, title=body.title, content=body.content)
        return WikiItem(**p)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update wiki page: {str(e)}")


@router.delete("/wiki/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wiki(page_id: str):
    try:
        kb.delete_wiki_page(page_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete wiki page: {str(e)}")

