"""
Audit Logging Routes

Client-side audit event logging for security and compliance.
Provides endpoints for logging and retrieving audit events.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from api.auth_middleware import get_current_user, User
from api.utils import get_user_id, get_user_role
from api.audit_logger import get_audit_logger, AuditEntry, AuditAction
from api.telemetry import track_metric, TelemetryMetric
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/audit",
    tags=["audit"]
)


class AuditLogRequest(BaseModel):
    """Client-side audit log request"""
    action: str
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@router.post(
    "/log",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="audit_log_event",
    summary="Log audit event",
    description="Log a client-side audit event (non-blocking best-effort)"
)
async def log_audit_event(
    body: AuditLogRequest,
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Log an audit event from client-side

    Non-blocking best-effort logging
    """
    user_id = get_user_id(current_user)

    try:
        audit_logger = get_audit_logger()

        # Log the event
        audit_logger.log(
            user_id=user_id,
            action=body.action,
            resource_id=body.resource_id,
            ip_address=None,  # Could add from request if needed
            details=body.details
        )

        # Track telemetry for specific events (non-blocking)
        if body.action == AuditAction.TOKEN_NEAR_LIMIT_WARNING:
            track_metric(TelemetryMetric.TOKEN_NEAR_LIMIT_WARNING)
        elif body.action == AuditAction.SUMMARIZE_CONTEXT_INVOKED:
            track_metric(TelemetryMetric.SUMMARIZE_CONTEXT_INVOKED)

        return SuccessResponse(
            data={"status": "logged"},
            message="Audit event logged"
        )

    except Exception as e:
        # Non-blocking - log warning and return success anyway
        logger.warning(f"Audit logging failed: {e}")
        return SuccessResponse(
            data={"status": "failed"},
            message="Audit logging failed (non-critical)"
        )


@router.get(
    "/sessions/{session_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="audit_get_session_logs",
    summary="Get session audit logs",
    description="Get audit logs for a specific chat session (newest first, filtered by user role)"
)
async def get_session_audit_logs(
    session_id: str,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Get audit logs for a specific chat session

    Returns events in reverse chronological order (newest first).
    Users can only see their own session logs unless they're admin/founder.
    """
    user_id = get_user_id(current_user)
    user_role = get_user_role(current_user) or "user"

    try:
        audit_logger = get_audit_logger()

        # Fetch logs filtered by resource_id (session_id)
        logs = audit_logger.get_logs(
            resource_id=session_id,
            limit=limit,
            offset=offset
        )

        # Filter to current user's logs unless admin/founder
        if user_role not in ["admin", "founder"]:
            logs = [log for log in logs if log.user_id == user_id]

        # Convert to dict for JSON serialization
        return SuccessResponse(
            data={
                "session_id": session_id,
                "logs": [log.model_dump() for log in logs],
                "count": len(logs),
                "limit": limit,
                "offset": offset
            },
            message=f"Retrieved {len(logs)} audit log(s)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to fetch session audit logs", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve audit logs"
            ).model_dump()
        )
