"""
Workflow Service Dependencies

Shared dependencies, helpers, and service initialization.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Import core dependencies
from api.permission_engine import require_perm, require_perm_team
from api.auth_middleware import get_current_user
from api.services.team import is_team_member
from api.rate_limiter import rate_limiter, get_client_ip
from api.utils import get_user_id

from .models import (
    Workflow, WorkItem, Stage, WorkItemStatus, WorkItemPriority,
    StageType, AssignmentType, WorkflowTriggerType, WorkflowType,
    CreateWorkItemRequest, ClaimWorkItemRequest, CompleteStageRequest,
    CreateWorkflowRequest, StageTransition,
)
from api.workflow_orchestrator import WorkflowOrchestrator
from api.workflow_storage import WorkflowStorage
from api.services.workflow_analytics import WorkflowAnalytics
from api.workflow_p2p_sync import init_workflow_sync, get_workflow_sync

# Initialize storage and orchestrator (singletons)
storage = WorkflowStorage()
orchestrator = WorkflowOrchestrator(storage=storage)
analytics = WorkflowAnalytics(db_path=storage.db_path)

# P2P sync (will be initialized when P2P service starts)
workflow_sync = None


def setup_p2p_sync(peer_id: str) -> None:
    """Setup P2P sync when P2P service is ready"""
    global workflow_sync
    if not workflow_sync:
        workflow_sync = init_workflow_sync(orchestrator, storage, peer_id)
        logger.info(f"🔄 Workflow P2P sync initialized for peer {peer_id}")


def get_user_team_id(user_id: str) -> Optional[str]:
    """
    Get user's primary team ID for visibility checks.

    Returns first team if user has multiple teams.
    Most users are in one team, so this is a reasonable default.
    """
    from api.services.team.members import get_user_teams

    user_teams = get_user_teams(user_id)
    return user_teams[0]['id'] if user_teams else None


__all__ = [
    # Services
    "storage",
    "orchestrator",
    "analytics",
    "workflow_sync",
    "setup_p2p_sync",
    # Helpers
    "get_user_id",
    "get_user_team_id",
    # Decorators
    "require_perm",
    "require_perm_team",
    # Auth
    "get_current_user",
    "is_team_member",
    # Rate limiting
    "rate_limiter",
    "get_client_ip",
    # Models
    "Workflow",
    "WorkItem",
    "Stage",
    "WorkItemStatus",
    "WorkItemPriority",
    "StageType",
    "AssignmentType",
    "WorkflowTriggerType",
    "WorkflowType",
    "CreateWorkItemRequest",
    "ClaimWorkItemRequest",
    "CompleteStageRequest",
    "CreateWorkflowRequest",
    "StageTransition",
]
