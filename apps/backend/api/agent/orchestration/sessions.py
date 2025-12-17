"""
Agent Sessions Service (Phase C)

High-level operations for managing stateful agent workspace sessions.
Provides CRUD operations and session lifecycle management.
"""

import uuid
import logging
from datetime import datetime, UTC
from typing import Optional, Dict, Any, List

try:
    from api.agent.orchestration.models import AgentSession
    from api.agent.orchestration import session_storage
    from api.audit_logger import AuditAction, audit_log_sync
    from api.metrics import get_metrics
except ImportError:
    from .models import AgentSession
    from . import session_storage
    try:
        from ...audit_logger import AuditAction, audit_log_sync
        from ...metrics import get_metrics
    except ImportError:
        # Fallback for test environments
        AuditAction = None
        audit_log_sync = lambda *args, **kwargs: None
        get_metrics = lambda: None

logger = logging.getLogger(__name__)
metrics = get_metrics() if get_metrics() else None


def create_agent_session(
    user_id: str,
    repo_root: str,
    attached_work_item_id: Optional[str] = None
) -> AgentSession:
    """
    Create a new agent workspace session.

    Args:
        user_id: User ID (session owner)
        repo_root: Repository root path for workspace
        attached_work_item_id: Optional workflow work item ID to attach

    Returns:
        Created AgentSession object

    Example:
        >>> session = create_agent_session("user_123", "/path/to/repo")
        >>> print(session.id)
        session_a1b2c3d4
    """
    session_id = f"session_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC)

    session = AgentSession(
        id=session_id,
        user_id=user_id,
        repo_root=repo_root,
        created_at=now,
        last_activity_at=now,
        status="active",
        current_plan=None,
        attached_work_item_id=attached_work_item_id,
    )

    session_storage.create_session(session)

    logger.info(
        f"Created agent session {session_id} for user {user_id}",
        extra={"session_id": session_id, "user_id": user_id, "repo_root": repo_root}
    )

    # Audit log
    if AuditAction:
        audit_log_sync(
            user_id=user_id,
            action=AuditAction.AGENT_SESSION_CREATED,
            resource="agent_session",
            resource_id=session_id,
            details={
                "repo_root": repo_root,
                "attached_work_item_id": attached_work_item_id,
                "status": "active"
            }
        )

    # Metrics
    if metrics:
        metrics.record("agent.sessions.created", 0, error=False)

    return session


def get_agent_session(session_id: str) -> Optional[AgentSession]:
    """
    Get session by ID.

    Args:
        session_id: Session identifier

    Returns:
        AgentSession if found, None otherwise

    Example:
        >>> session = get_agent_session("session_a1b2c3d4")
        >>> if session:
        ...     print(session.user_id)
    """
    return session_storage.get_session(session_id)


def list_agent_sessions_for_user(
    user_id: str,
    active_only: bool = False
) -> List[AgentSession]:
    """
    List all sessions for a user.

    Args:
        user_id: User identifier
        active_only: If True, only return active sessions

    Returns:
        List of AgentSession objects, ordered by last_activity_at DESC

    Example:
        >>> sessions = list_agent_sessions_for_user("user_123")
        >>> active_sessions = list_agent_sessions_for_user("user_123", active_only=True)
    """
    status_filter = "active" if active_only else None
    return session_storage.list_sessions_for_user(user_id, status_filter)


def update_session_plan(session_id: str, plan_payload: Dict[str, Any]) -> None:
    """
    Update session's current plan and touch last_activity_at.

    Args:
        session_id: Session identifier
        plan_payload: Plan data (typically PlanResponse.model_dump())

    Side Effects:
        - Updates session.current_plan
        - Updates session.last_activity_at to current UTC time

    Example:
        >>> plan_response = generate_plan_logic(...)
        >>> update_session_plan("session_a1b2c3d4", plan_response.model_dump())
    """
    try:
        session_storage.update_session(
            session_id,
            {
                "current_plan": plan_payload,
                "last_activity_at": datetime.now(UTC),
            },
        )
        logger.info(f"Updated plan for session {session_id}")

        # Get session to retrieve user_id for audit
        session = session_storage.get_session(session_id)
        if session and AuditAction:
            num_steps = len(plan_payload.get("steps", [])) if isinstance(plan_payload, dict) else 0
            audit_log_sync(
                user_id=session.user_id,
                action=AuditAction.AGENT_SESSION_PLAN_UPDATED,
                resource="agent_session",
                resource_id=session_id,
                details={"num_steps": num_steps}
            )
    except Exception as e:
        # Graceful degradation - log but don't fail
        logger.warning(f"Failed to update session plan for {session_id}: {e}")
        if metrics:
            metrics.record("agent.sessions.errors", 0, error=True)


def touch_session(session_id: str) -> None:
    """
    Update session's last_activity_at to current time.

    Used to track session usage without modifying plan or other fields.

    Args:
        session_id: Session identifier

    Example:
        >>> touch_session("session_a1b2c3d4")  # Mark session as recently active
    """
    try:
        session_storage.update_session(
            session_id,
            {
                "last_activity_at": datetime.now(UTC),
            },
        )
        logger.debug(f"Touched session {session_id}")
    except Exception as e:
        # Graceful degradation - log but don't fail
        logger.warning(f"Failed to touch session {session_id}: {e}")


def complete_session(session_id: str) -> None:
    """
    Mark session as completed.

    Args:
        session_id: Session identifier

    Side Effects:
        - Sets session.status to "completed"
        - Updates session.last_activity_at

    Example:
        >>> complete_session("session_a1b2c3d4")
    """
    session_storage.update_session(
        session_id,
        {
            "status": "completed",
            "last_activity_at": datetime.now(UTC),
        },
    )
    logger.info(f"Completed session {session_id}")


def close_session(session_id: str) -> None:
    """
    Archive a session (soft delete).

    Alias for archive_session for backwards compatibility.

    Args:
        session_id: Session identifier

    Side Effects:
        - Sets session.status to "archived"
        - Updates session.last_activity_at

    Example:
        >>> close_session("session_a1b2c3d4")
    """
    # Get session before closing for audit
    session = session_storage.get_session(session_id)

    session_storage.archive_session(session_id)

    if session and AuditAction:
        audit_log_sync(
            user_id=session.user_id,
            action=AuditAction.AGENT_SESSION_CLOSED,
            resource="agent_session",
            resource_id=session_id,
            details={"final_status": "archived"}
        )

    if metrics:
        metrics.record("agent.sessions.closed", 0, error=False)


def reactivate_session(session_id: str) -> None:
    """
    Reactivate an archived or completed session.

    Args:
        session_id: Session identifier

    Side Effects:
        - Sets session.status to "active"
        - Updates session.last_activity_at

    Example:
        >>> reactivate_session("session_a1b2c3d4")
    """
    session_storage.update_session(
        session_id,
        {
            "status": "active",
            "last_activity_at": datetime.now(UTC),
        },
    )
    logger.info(f"Reactivated session {session_id}")


def attach_work_item(session_id: str, work_item_id: str) -> None:
    """
    Attach a workflow work item to a session.

    Args:
        session_id: Session identifier
        work_item_id: Workflow work item ID to attach

    Side Effects:
        - Sets session.attached_work_item_id
        - Updates session.last_activity_at

    Example:
        >>> attach_work_item("session_a1b2c3d4", "work_item_xyz")
    """
    session_storage.update_session(
        session_id,
        {
            "attached_work_item_id": work_item_id,
            "last_activity_at": datetime.now(UTC),
        },
    )
    logger.info(f"Attached work item {work_item_id} to session {session_id}")


def detach_work_item(session_id: str) -> None:
    """
    Detach work item from session.

    Args:
        session_id: Session identifier

    Side Effects:
        - Sets session.attached_work_item_id to None
        - Updates session.last_activity_at

    Example:
        >>> detach_work_item("session_a1b2c3d4")
    """
    session_storage.update_session(
        session_id,
        {
            "attached_work_item_id": None,
            "last_activity_at": datetime.now(UTC),
        },
    )
    logger.info(f"Detached work item from session {session_id}")
