"""
Workflow Health Check Endpoint

Service health and diagnostics.
"""

from typing import Any, Dict
from fastapi import APIRouter
import logging

from ..dependencies import orchestrator, storage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint with storage path info

    Returns:
        - status: Service health status
        - active_workflows: Count of active workflows in memory
        - active_work_items: Count of active work items in memory
        - storage_path: Path to workflow database (for ops diagnostics)
        - db_readable: Whether database is accessible
    """
    # Check if database is readable
    db_readable = False
    try:
        db_readable = storage.db_path.exists() and storage.db_path.is_file()
    except Exception:
        pass

    return {
        "status": "healthy",
        "active_workflows": len(orchestrator.workflows),
        "active_work_items": len(orchestrator.active_work_items),
        "storage_path": str(storage.db_path),
        "db_readable": db_readable,
    }


__all__ = ["router"]
