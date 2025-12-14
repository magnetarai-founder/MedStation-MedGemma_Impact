"""
Analytics API Routes

Provides analytics data for the dashboard and exports.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Optional, Literal, Dict, Any
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import Response

try:
    from api.auth_middleware import get_current_user
    from api.permission_engine import require_perm
except ImportError:
    from auth_middleware import get_current_user
    from permission_engine import require_perm

from api.services.analytics import get_analytics_service
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get(
    "/usage",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="analytics_get_usage",
    summary="Get usage analytics",
    description="Get usage analytics summary with model usage, trends, and top users/teams (requires analytics.view permission)"
)
async def get_usage_analytics(
    request: Request,
    range: Literal["7d", "30d", "90d"] = "7d",
    team_id: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """
    Get usage analytics summary

    Security:
    - Requires 'analytics.view' permission (founder/admin only)
    - Non-admins can only view their own analytics (user_id filter enforced)
    """
    # Check permissions (require_perm is a decorator, not async)
    require_perm("analytics.view")(lambda: None)()

    # Parse range to days
    range_map = {
        "7d": 7,
        "30d": 30,
        "90d": 90
    }
    days = range_map.get(range, 7)

    # Non-founders/admins can only view their own data
    if current_user.get("role") not in ["founder", "admin"]:
        user_id = current_user["user_id"]
        logger.info(f"Non-admin user {user_id} requesting analytics (restricted to own data)")

    try:
        analytics = get_analytics_service()
        summary = analytics.get_usage_summary(
            days=days,
            team_id=team_id,
            user_id=user_id
        )

        return SuccessResponse(
            data={
                "range": range,
                "days": days,
                "filters": {
                    "team_id": team_id,
                    "user_id": user_id
                },
                "data": summary
            },
            message=f"Retrieved usage analytics for {range}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get usage analytics", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve usage analytics"
            ).model_dump()
        )


@router.get(
    "/export",
    status_code=status.HTTP_200_OK,
    name="analytics_export",
    summary="Export analytics data",
    description="Export analytics data as downloadable file (JSON or CSV, requires analytics.view permission)"
)
async def export_analytics(
    request: Request,
    format: Literal["json", "csv"] = "json",
    range: Literal["7d", "30d", "90d"] = "30d",
    team_id: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Export analytics data as downloadable file

    Returns raw Response with file content (not wrapped in SuccessResponse).

    Security:
    - Requires 'analytics.view' permission
    - Non-admins restricted to own data
    """
    # Check permissions (require_perm is a decorator, not async)
    require_perm("analytics.view")(lambda: None)()

    # Parse range to days
    range_map = {
        "7d": 7,
        "30d": 30,
        "90d": 90
    }
    days = range_map.get(range, 30)

    # Non-founders/admins can only export their own data
    if current_user.get("role") not in ["founder", "admin"]:
        user_id = current_user["user_id"]

    try:
        analytics = get_analytics_service()
        export_data = analytics.export_data(
            format=format,
            days=days,
            team_id=team_id,
            user_id=user_id
        )

        return Response(
            content=export_data["data"],
            media_type=export_data["content_type"],
            headers={
                "Content-Disposition": f"attachment; filename=\"{export_data['filename']}\""
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to export analytics", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to export analytics data"
            ).model_dump()
        )
