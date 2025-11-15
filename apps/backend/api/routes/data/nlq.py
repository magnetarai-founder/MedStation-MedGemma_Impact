"""
Natural Language Query (NLQ) Routes

POST /api/v1/data/nlq - Convert natural language to SQL and execute
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth_middleware import get_current_user, User
from api.services.nlq_service import get_nlq_service
from api.utils import sanitize_for_log

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
            model=request.model
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
