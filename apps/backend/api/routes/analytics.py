"""
Analytics API Routes - Sprint 6 Theme A

Provides analytics data for the dashboard and exports.
"""

import logging
from typing import Optional, Literal
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import Response

try:
    from api.auth_middleware import get_current_user
    from api.permission_engine import require_perm
except ImportError:
    from auth_middleware import get_current_user
    from permission_engine import require_perm

from api.services.analytics import get_analytics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/usage", name="analytics_get_usage")
async def get_usage_analytics(
    request: Request,
    range: Literal["7d", "30d", "90d"] = "7d",
    team_id: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Get usage analytics summary

    Args:
        range: Time range (7d, 30d, or 90d)
        team_id: Filter by team (optional)
        user_id: Filter by user (optional)

    Returns:
        Analytics summary with model usage, trends, and top users/teams

    Permissions:
        - Requires 'analytics.view' permission (founder/admin only)
        - Non-admins can only view their own analytics (user_id filter enforced)
    """
    # Check permissions
    await require_perm("analytics.view", current_user)

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

        return {
            "range": range,
            "days": days,
            "filters": {
                "team_id": team_id,
                "user_id": user_id
            },
            "data": summary
        }

    except Exception as e:
        logger.error(f"Failed to get usage analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export", name="analytics_export")
async def export_analytics(
    request: Request,
    format: Literal["json", "csv"] = "json",
    range: Literal["7d", "30d", "90d"] = "30d",
    team_id: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Export analytics data

    Args:
        format: Export format (json or csv)
        range: Time range (7d, 30d, or 90d)
        team_id: Filter by team (optional)
        user_id: Filter by user (optional)

    Returns:
        Downloadable file with analytics data

    Permissions:
        - Requires 'analytics.view' permission
        - Non-admins restricted to own data
    """
    # Check permissions
    await require_perm("analytics.view", current_user)

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

    except Exception as e:
        logger.error(f"Failed to export analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
