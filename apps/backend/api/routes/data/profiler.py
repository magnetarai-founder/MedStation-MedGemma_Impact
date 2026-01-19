"""
Pattern Discovery Routes

Analyze datasets to discover patterns, correlations, and insights.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth_middleware import get_current_user, User
from api.services.data_profiler import get_data_profiler
from api.utils import sanitize_for_log, get_user_id
from api.routes.schemas import SuccessResponse
from api.errors import http_400, http_500

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/data", tags=["data-profiler"])


class PatternDiscoveryRequest(BaseModel):
    """Pattern discovery request"""
    dataset_id: Optional[str] = Field(None, description="Dataset UUID")
    session_id: Optional[str] = Field(None, description="Session UUID")
    table_name: Optional[str] = Field(None, description="Table name (required if using session_id)")
    sample_rows: Optional[int] = Field(None, description="Max rows to analyze (default: 50k)", ge=100, le=200000)


class PatternDiscoveryResponse(BaseModel):
    """Pattern discovery response"""
    columns: dict
    correlations: list
    insights: list
    metadata: dict


@router.post(
    "/discover-patterns",
    response_model=SuccessResponse[PatternDiscoveryResponse],
    status_code=status.HTTP_200_OK,
    name="discover_dataset_patterns",
    summary="Discover patterns",
    description="Analyze dataset to discover patterns, correlations, outliers, and insights"
)
async def discover_patterns(
    request: PatternDiscoveryRequest,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[PatternDiscoveryResponse]:
    """
    Discover patterns in dataset

    Analyzes dataset to provide:
    - Column statistics (numeric, categorical, temporal, text)
    - Outlier detection (z-score > 3)
    - Correlations (Pearson, top 10 pairs)
    - Natural language insights

    Performance:
    - Samples large datasets (50k rows default)
    - 30-second timeout
    - Returns partial results if time limit exceeded
    """

    # Validate inputs
    if not request.dataset_id and not request.session_id:
        raise http_400("Either dataset_id or session_id must be provided")

    if request.session_id and not request.table_name:
        raise http_400("table_name is required when using session_id")

    # Extract user_id from dict (get_current_user returns Dict, not User object)
    user_id = get_user_id(current_user)

    # Log request (sanitized)
    logger.info(
        "Pattern discovery request",
        extra={
            "user_id": user_id,
            "dataset_id": request.dataset_id,
            "session_id": request.session_id,
            "table_name": sanitize_for_log(request.table_name) if request.table_name else None,
            "sample_rows": request.sample_rows
        }
    )

    # Profile dataset
    profiler = get_data_profiler()

    try:
        result = profiler.profile_dataset(
            dataset_id=request.dataset_id,
            session_id=request.session_id,
            table_name=request.table_name,
            sample_rows=request.sample_rows
        )

        # Log result metadata
        logger.info(
            "Pattern discovery success",
            extra={
                "columns_analyzed": len(result.get("columns", {})),
                "correlations_found": len(result.get("correlations", [])),
                "insights_generated": len(result.get("insights", [])),
                "total_time_ms": result.get("metadata", {}).get("total_time_ms", 0)
            }
        )

        response_data = PatternDiscoveryResponse(**result)
        return SuccessResponse(
            data=response_data,
            message=f"Analyzed {len(result.get('columns', {}))} column(s) with {len(result.get('insights', []))} insight(s)"
        )

    except ValueError as e:
        # User error (dataset not found, etc.)
        logger.warning(f"Pattern discovery validation error: {e}")
        raise http_400(str(e))

    except HTTPException:
        raise

    except Exception as e:
        # Internal error
        logger.error(f"Pattern discovery processing error", exc_info=True)
        raise http_500("Failed to analyze dataset")
