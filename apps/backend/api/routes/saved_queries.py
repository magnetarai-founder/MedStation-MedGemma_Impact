"""
Saved Queries Routes

Provides CRUD operations for saved database queries.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import json
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request, Query, Depends, status
from pydantic import BaseModel

from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

try:
    from api.auth_middleware import get_current_user, User
except ImportError:
    from auth_middleware import get_current_user, User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/saved-queries",
    tags=["saved-queries"]
)

# Import shared elohimos_memory instance from main.py
def get_elohimos_memory():
    from api import main
    return main.elohimos_memory

# Models
class SavedQueryRequest(BaseModel):
    name: str
    query: str
    query_type: str
    folder: str | None = None
    description: str | None = None
    tags: list[str] | None = None

class SavedQueryUpdateRequest(BaseModel):
    name: str | None = None
    query: str | None = None
    query_type: str | None = None
    folder: str | None = None
    description: str | None = None
    tags: list[str] | None = None

@router.post(
    "",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
    name="save_query",
    summary="Save query",
    description="Save a database query for later reuse"
)
async def save_query(
    request: Request,
    body: SavedQueryRequest,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """Save a query for later use"""
    elohimos_memory = get_elohimos_memory()
    try:
        query_id = elohimos_memory.save_query(
            name=body.name,
            query=body.query,
            query_type=body.query_type,
            folder=body.folder,
            description=body.description,
            tags=body.tags
        )
        return SuccessResponse(
            data={"id": query_id},
            message=f"Query '{body.name}' saved successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to save query", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to save query"
            ).model_dump()
        )

@router.get(
    "",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="get_saved_queries",
    summary="Get saved queries",
    description="Get all saved queries with optional filtering by folder and type"
)
async def get_saved_queries(
    folder: str | None = Query(None),
    query_type: str | None = Query(None),
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """Get all saved queries"""
    elohimos_memory = get_elohimos_memory()
    try:
        queries = elohimos_memory.get_saved_queries(
            folder=folder,
            query_type=query_type
        )
        return SuccessResponse(
            data={"queries": queries},
            message=f"Retrieved {len(queries)} saved quer{'y' if len(queries) == 1 else 'ies'}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get saved queries", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve saved queries"
            ).model_dump()
        )

@router.put(
    "/{query_id}",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="update_saved_query",
    summary="Update saved query",
    description="Update a saved query (partial updates supported)"
)
async def update_saved_query(
    request: Request,
    query_id: int,
    body: SavedQueryUpdateRequest,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """Update a saved query (partial updates supported)"""
    elohimos_memory = get_elohimos_memory()
    try:
        # Get existing query
        all_queries = elohimos_memory.get_saved_queries()
        existing = next((q for q in all_queries if q['id'] == query_id), None)

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Query not found"
                ).model_dump()
            )

        # Merge updates with existing data
        elohimos_memory.update_saved_query(
            query_id=query_id,
            name=body.name if body.name is not None else existing['name'],
            query=body.query if body.query is not None else existing['query'],
            query_type=body.query_type if body.query_type is not None else existing['query_type'],
            folder=body.folder if body.folder is not None else existing.get('folder'),
            description=body.description if body.description is not None else existing.get('description'),
            tags=body.tags if body.tags is not None else (json.loads(existing.get('tags', '[]')) if existing.get('tags') else None)
        )

        return SuccessResponse(
            data={"query_id": query_id},
            message="Query updated successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to update query {query_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update query"
            ).model_dump()
        )

@router.delete(
    "/{query_id}",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="delete_saved_query",
    summary="Delete saved query",
    description="Delete a saved query by ID"
)
async def delete_saved_query(
    request: Request,
    query_id: int,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """Delete a saved query"""
    elohimos_memory = get_elohimos_memory()
    try:
        elohimos_memory.delete_saved_query(query_id)
        return SuccessResponse(
            data={"query_id": query_id},
            message="Query deleted successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to delete query {query_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to delete query"
            ).model_dump()
        )
