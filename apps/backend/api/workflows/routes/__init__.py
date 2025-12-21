"""
Workflow Routes Module

Sub-routers for all workflow API endpoints.
"""

from .workflows import router as workflows_router
from .work_items import router as work_items_router
from .queue import router as queue_router
from .monitoring import router as monitoring_router
from .starring import router as starring_router
from .templates import router as templates_router
from .analytics import router as analytics_router
from .health import router as health_router

__all__ = [
    "workflows_router",
    "work_items_router",
    "queue_router",
    "monitoring_router",
    "starring_router",
    "templates_router",
    "analytics_router",
    "health_router",
]
