"""
Search Routes

Full-text search over session messages with filtering and ranking.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException, Query, status

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from api.auth_middleware import get_current_user

from api.services.search import get_search_service
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get(
    "/sessions",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="search_sessions",
    summary="Search sessions",
    description="Full-text search over session messages with filtering and ranking"
)
async def search_sessions(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    team_id: Optional[str] = Query(None, description="Filter by team"),
    model: Optional[str] = Query(None, description="Filter by model name"),
    from_date: Optional[str] = Query(None, alias="from", description="Start date (ISO format)"),
    to_date: Optional[str] = Query(None, alias="to", description="End date (ISO format)"),
    min_tokens: Optional[int] = Query(None, description="Minimum tokens"),
    max_tokens: Optional[int] = Query(None, description="Maximum tokens"),
    limit: int = Query(50, le=100, description="Max results"),
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """
    Search sessions by message content

    Returns matching sessions with highlighted snippets, relevance scores,
    and match counts. Results are ranked by relevance.

    Security:
    - Non-admins can only search their own sessions
    - Admins/founders can search team-wide
    """
    try:
        search_service = get_search_service()

        results = search_service.search_sessions(
            query=q,
            user_id=current_user["user_id"],
            user_role=current_user.get("role", "user"),
            team_id=team_id,
            model=model,
            from_date=from_date,
            to_date=to_date,
            min_tokens=min_tokens,
            max_tokens=max_tokens,
            limit=limit
        )

        return SuccessResponse(
            data={
                "query": q,
                "total_results": len(results),
                "results": results
            },
            message=f"Found {len(results)} matching session(s)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Search failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Search operation failed"
            ).model_dump()
        )
