"""
Query history management routes.

Handles viewing and deleting query history for sessions.
"""

from fastapi import APIRouter, HTTPException, status
from api.schemas.api_models import QueryHistoryResponse, SuccessResponse
from api.errors import http_404, http_500
from api.routes.sql_json.utils import (
    get_logger,
    get_sessions,
    get_query_results,
    get_query_result_sizes,
    get_total_cache_size_ref,
    validate_session_exists
)


router = APIRouter(tags=["sessions"])


@router.get(
    "/{session_id}/query-history",
    name="sessions_query_history",
    response_model=QueryHistoryResponse,
    status_code=status.HTTP_200_OK
)
async def get_query_history_router(session_id: str) -> QueryHistoryResponse:
    """Get query history for a session"""
    logger = get_logger()
    sessions = get_sessions()

    try:
        validate_session_exists(session_id, sessions)

        queries = sessions[session_id].get('queries', {})
        history = []

        for query_id, query_info in queries.items():
            history.append({
                "id": query_id,
                "query": query_info["sql"],
                "timestamp": query_info["executed_at"].isoformat(),
                "executionTime": query_info.get("execution_time_ms"),
                "rowCount": query_info.get("row_count"),
                "status": "success"  # We only store successful queries
            })

        # Sort by timestamp descending (most recent first)
        history.sort(key=lambda x: x["timestamp"], reverse=True)

        return QueryHistoryResponse(history=history)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get query history for session {session_id}", exc_info=True)
        raise http_500("Failed to retrieve query history")


@router.delete(
    "/{session_id}/query-history/{query_id}",
    name="sessions_query_history_delete",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK
)
async def delete_query_from_history_router(
    session_id: str,
    query_id: str
) -> SuccessResponse:
    """Delete a query from history"""
    logger = get_logger()
    sessions = get_sessions()
    query_results = get_query_results()
    query_result_sizes = get_query_result_sizes()
    main_module = get_total_cache_size_ref()

    try:
        validate_session_exists(session_id, sessions)

        queries = sessions[session_id].get('queries', {})
        if query_id not in queries:
            raise http_404(f"Query '{query_id}' not found", resource="query")

        del queries[query_id]

        # Also remove from query_results cache if it exists
        if query_id in query_results:
            size = query_result_sizes.get(query_id, 0)
            del query_results[query_id]
            if query_id in query_result_sizes:
                del query_result_sizes[query_id]
            main_module._total_cache_size -= size

        return SuccessResponse(success=True, message="Query deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete query {query_id} from session {session_id}", exc_info=True)
        raise http_500("Failed to delete query from history")
