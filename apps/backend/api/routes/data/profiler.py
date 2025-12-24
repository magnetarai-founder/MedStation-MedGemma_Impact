"""
Pattern Discovery Routes

Analyze datasets to discover patterns, correlations, and insights.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

try:
    from api.auth_middleware import get_current_user, User
except ImportError:
    from api.auth_middleware import get_current_user, User
from api.services.data_profiler import get_data_profiler
from api.utils import sanitize_for_log
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="Either dataset_id or session_id must be provided"
            ).model_dump()
        )

    if request.session_id and not request.table_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="table_name is required when using session_id"
            ).model_dump()
        )

    # Log request (sanitized)
    logger.info(
        "Pattern discovery request",
        extra={
            "user_id": current_user.user_id,
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
        # Internal error
        logger.error(f"Pattern discovery processing error", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to analyze dataset"
            ).model_dump()
        )
