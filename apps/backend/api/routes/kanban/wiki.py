"""
Kanban Wiki Routes

Provides CRUD operations for wiki pages within kanban projects.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth_middleware import get_current_user
from api.services import kanban_service as kb
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/kanban", tags=["kanban-wiki"])


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


@router.get(
    "/projects/{project_id}/wiki",
    response_model=SuccessResponse[List[WikiItem]],
    status_code=status.HTTP_200_OK,
    name="list_wiki_pages",
    summary="List wiki pages",
    description="List all wiki pages in a kanban project"
)
async def list_wiki(
    project_id: str,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[List[WikiItem]]:
    """List all wiki pages in a project"""
    try:
        pages = [WikiItem(**p) for p in kb.list_wiki_pages(project_id)]
        return SuccessResponse(
            data=pages,
            message=f"Retrieved {len(pages)} wiki page(s)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to list wiki pages for project {project_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve wiki pages"
            ).model_dump()
        )


@router.post(
    "/wiki",
    response_model=SuccessResponse[WikiItem],
    status_code=status.HTTP_201_CREATED,
    name="create_wiki_page",
    summary="Create wiki page",
    description="Create a new wiki page in a kanban project"
)
async def create_wiki(
    body: WikiCreate,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[WikiItem]:
    """Create a new wiki page"""
    try:
        p = kb.create_wiki_page(body.project_id, body.title, body.content)
        return SuccessResponse(
            data=WikiItem(**p),
            message=f"Wiki page '{body.title}' created successfully"
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
        logger.error(f"Failed to create wiki page", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to create wiki page"
            ).model_dump()
        )


@router.patch(
    "/wiki/{page_id}",
    response_model=SuccessResponse[WikiItem],
    status_code=status.HTTP_200_OK,
    name="update_wiki_page",
    summary="Update wiki page",
    description="Update wiki page title or content (partial updates supported)"
)
async def update_wiki(
    page_id: str,
    body: WikiUpdate,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[WikiItem]:
    """Update wiki page title or content"""
    try:
        p = kb.update_wiki_page(page_id, title=body.title, content=body.content)
        return SuccessResponse(
            data=WikiItem(**p),
            message="Wiki page updated successfully"
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
        logger.error(f"Failed to update wiki page {page_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update wiki page"
            ).model_dump()
        )


@router.delete(
    "/wiki/{page_id}",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="delete_wiki_page",
    summary="Delete wiki page",
    description="Delete a wiki page by ID"
)
async def delete_wiki(
    page_id: str,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """Delete a wiki page"""
    try:
        kb.delete_wiki_page(page_id)
        return SuccessResponse(
            data={"page_id": page_id},
            message="Wiki page deleted successfully"
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
        logger.error(f"Failed to delete wiki page {page_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to delete wiki page"
            ).model_dump()
        )

