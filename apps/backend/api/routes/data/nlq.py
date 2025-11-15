"""
Natural Language Query (NLQ) Routes

POST /api/v1/data/nlq - Convert natural language to SQL and execute
GET  /api/v1/data/nlq/recent - Get recent NL→SQL analyses
"""

import logging
import sqlite3
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth_middleware import get_current_user, User
from api.services.nlq_service import get_nlq_service
from api.utils import sanitize_for_log
from api.config_paths import PATHS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/data", tags=["data-nlq"])


class NLQRequest(BaseModel):
    """Natural language query request"""
    question: str = Field(..., min_length=3, max_length=500, description="Natural language question")
    dataset_id: Optional[str] = Field(None, description="Target dataset ID")
    session_id: Optional[str] = Field(None, description="Session ID for context")
    model: Optional[str] = Field(None, description="LLM model to use (defaults to qwen2.5:7b-instruct)")


class NLQResponse(BaseModel):
    """Natural language query response"""
    sql: Optional[str] = None
    results: Optional[list] = None
    row_count: Optional[int] = None
    columns: Optional[list] = None
    summary: Optional[str] = None
    warnings: Optional[list] = None
    metadata: Optional[dict] = None
    error: Optional[str] = None
    details: Optional[str] = None
    suggestion: Optional[str] = None


@router.post("/nlq", response_model=NLQResponse)
async def natural_language_query(
    request: NLQRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Convert natural language question to SQL and execute

    Examples:
    - "Show me all rows where revenue > 1000"
    - "What's the average price by region?"
    - "Find the top 10 customers by sales"

    Returns:
    - Generated SQL query (editable)
    - Query results
    - Natural language summary
    - Execution metadata
    """

    # Log request (sanitized)
    logger.info(
        "NLQ request",
        extra={
            "user_id": current_user.user_id,
            "question_length": len(request.question),
            "dataset_id": request.dataset_id,
            "session_id": request.session_id,
            "model": request.model
        }
    )

    # Log sanitized question (no secrets)
    safe_question = sanitize_for_log(request.question)
    logger.debug(f"NLQ question: {safe_question}")

    # Process query
    nlq_service = get_nlq_service()

    try:
        result = await nlq_service.process_nlq(
            question=request.question,
            dataset_id=request.dataset_id,
            session_id=request.session_id,
            model=request.model,
            user_id=current_user.user_id
        )

        # Log result metadata
        if "error" not in result:
            logger.info(
                "NLQ success",
                extra={
                    "row_count": result.get("row_count", 0),
                    "execution_time_ms": result.get("metadata", {}).get("execution_time_ms", 0),
                    "warnings": len(result.get("warnings", []))
                }
            )
        else:
            logger.warning(
                "NLQ failed",
                extra={
                    "error": result.get("error"),
                    "details": result.get("details")
                }
            )

        return NLQResponse(**result)

    except Exception as e:
        logger.error(f"NLQ processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to process natural language query",
                "details": str(e),
                "suggestion": "Please try again or rephrase your question"
            }
        )


class NLQHistoryItem(BaseModel):
    """NLQ history item"""
    id: str
    question: str
    sql: str
    summary: Optional[str]
    created_at: str


@router.get("/nlq/recent", response_model=List[NLQHistoryItem])
async def nlq_recent(
    limit: int = 20,
    current_user: User = Depends(get_current_user)
):
    """
    Get recent NL→SQL analyses for current user

    Args:
        limit: Maximum number of items to return (1-50, default 20)

    Returns:
        List of recent NLQ history items ordered by created_at DESC
    """
    # Clamp limit
    limit = max(1, min(limit, 50))

    items: List[NLQHistoryItem] = []
    try:
        with sqlite3.connect(str(PATHS.app_db)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT id, question, sql, summary, created_at FROM nlq_history "
                "WHERE user_id = ? ORDER BY datetime(created_at) DESC LIMIT ?",
                (current_user.user_id, limit)
            )
            rows = cur.fetchall()
            for r in rows:
                items.append(NLQHistoryItem(
                    id=r["id"],
                    question=r["question"],
                    sql=r["sql"],
                    summary=r["summary"],
                    created_at=r["created_at"],
                ))
    except Exception as e:
        # Return empty list on error; logs elsewhere if desired
        logger.warning(f"Failed to fetch NLQ history: {e}")
        return []

    return items
