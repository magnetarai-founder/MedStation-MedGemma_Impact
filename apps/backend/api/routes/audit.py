"""
Audit logging routes - Client-side audit events
"""

import logging
from fastapi import APIRouter, Request, Depends, Body, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user
from audit_logger import get_audit_logger, AuditEntry, AuditAction
from telemetry import track_metric, TelemetryMetric

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


@router.post("/log", name="audit_log_event")
async def log_audit_event(
    request: Request,
    body: AuditLogRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Log an audit event from client-side

    Non-blocking best-effort logging
    """
    try:
        audit_logger = get_audit_logger()

        # Get client IP
        client_ip = request.client.host if request.client else None

        # Log the event
        audit_logger.log(
            user_id=current_user["user_id"],
            action=body.action,
            resource_id=body.resource_id,
            ip_address=client_ip,
            details=body.details
        )

        # Track telemetry for specific events (non-blocking)
        if body.action == AuditAction.TOKEN_NEAR_LIMIT_WARNING:
            track_metric(TelemetryMetric.TOKEN_NEAR_LIMIT_WARNING)
        elif body.action == AuditAction.SUMMARIZE_CONTEXT_INVOKED:
            track_metric(TelemetryMetric.SUMMARIZE_CONTEXT_INVOKED)

        return {"status": "logged"}

    except Exception as e:
        # Non-blocking - log warning and return success anyway
        logger.warning(f"Audit logging failed: {e}")
        return {"status": "failed", "error": str(e)}


@router.get("/sessions/{session_id}", name="audit_get_session_logs")
async def get_session_audit_logs(
    session_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    Get audit logs for a specific chat session

    Returns events in reverse chronological order (newest first).
    Users can only see their own session logs unless they're admin/founder.
    """
    try:
        audit_logger = get_audit_logger()

        # Fetch logs filtered by resource_id (session_id)
        logs = audit_logger.get_logs(
            resource_id=session_id,
            limit=limit,
            offset=offset
        )

        # Filter to current user's logs unless admin/founder
        user_role = current_user.get("role", "user")
        if user_role not in ["admin", "founder"]:
            logs = [log for log in logs if log.user_id == current_user["user_id"]]

        # Convert to dict for JSON serialization
        return {
            "session_id": session_id,
            "logs": [log.model_dump() for log in logs],
            "count": len(logs),
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Failed to fetch session audit logs: {e}")
        return {
            "session_id": session_id,
            "logs": [],
            "count": 0,
            "error": str(e)
        }
