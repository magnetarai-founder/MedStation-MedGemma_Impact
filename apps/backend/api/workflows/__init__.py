"""
Workflows Module

Workflow orchestration with P2P sync capabilities.

This module has been refactored from workflow_service.py (1,021 lines) into:
- dependencies.py: Shared services, helpers, and model imports
- routes/workflows.py: Workflow CRUD endpoints
- routes/work_items.py: Work Item CRUD and action endpoints
- routes/queue.py: Queue operations
- routes/monitoring.py: SLA and monitoring endpoints
- routes/starring.py: Starring functionality
- routes/templates.py: Workflow template operations
- routes/analytics.py: Analytics endpoints
- routes/health.py: Health check endpoint
"""

from fastapi import APIRouter, Depends

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user

from .dependencies import (
    storage,
    orchestrator,
    analytics,
    workflow_sync,
    setup_p2p_sync,
    get_user_team_id,
)
from .routes import (
    workflows_router,
    work_items_router,
    queue_router,
    monitoring_router,
    starring_router,
    templates_router,
    analytics_router,
    health_router,
)

# Create combined router with all routes
router = APIRouter(
    prefix="/api/v1/workflow",
    tags=["workflow"],
    dependencies=[Depends(get_current_user)]
)

# Include all sub-routers
router.include_router(workflows_router)
router.include_router(work_items_router)
router.include_router(queue_router)
router.include_router(monitoring_router)
router.include_router(starring_router)
router.include_router(templates_router)
router.include_router(analytics_router)
router.include_router(health_router)

# Re-export core modules
from api.workflows import enums, models, p2p_sync, seed_templates

__all__ = [
    "router",
    "storage",
    "orchestrator",
    "analytics",
    "workflow_sync",
    "setup_p2p_sync",
    "get_user_team_id",
    # Core modules
    "enums",
    "models",
    "p2p_sync",
    "seed_templates",
]
