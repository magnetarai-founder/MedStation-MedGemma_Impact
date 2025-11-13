"""
Search API Routes - Sprint 6 Theme B

Full-text search over session messages.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException, Query

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user

from api.services.search import get_search_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["Search"])


@router.get("/sessions", name="search_sessions")
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
):
    """
    Search sessions by message content

    Args:
        q: Search query (required)
        team_id: Filter by team (optional)
        model: Filter by model name (optional)
        from_date: Start date filter (optional, ISO format)
        to_date: End date filter (optional, ISO format)
        min_tokens: Minimum token count (optional)
        max_tokens: Maximum token count (optional)
        limit: Max results (default 50, max 100)

    Returns:
        List of matching sessions with:
        - session_id: Session ID
        - title: Session title
        - snippet: Highlighted text snippet
        - ts: Timestamp of matching message
        - model_name: Model used
        - score: Relevance score
        - match_count: Number of matching messages in session

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

        return {
            "query": q,
            "total_results": len(results),
            "results": results
        }

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
