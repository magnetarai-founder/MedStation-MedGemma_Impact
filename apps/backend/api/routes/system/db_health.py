"""
Database Health Routes

Returns database path and table counts for admin monitoring.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
import sqlite3
import logging
from pathlib import Path

from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

from api.config_paths import PATHS
from api.admin_service import require_founder_rights

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/system",
    tags=["system"]
)


@router.get(
    "/db-health",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="get_database_health",
    summary="Get database health",
    description="Get database health information including path, size, and table counts (founder-only)"
)
async def get_db_health(
    user: dict = Depends(require_founder_rights)
) -> SuccessResponse[Dict[str, Any]]:
    """
    Get database health information

    Security:
    - Requires founder rights

    Returns database path, size, and table counts for monitoring.
    Falls back to partial info on errors (non-critical).
    """
    try:
        db_path = str(PATHS.app_db)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get counts for all major tables
        table_counts = {}

        # Core tables
        for table in ['users', 'teams', 'team_members', 'workflows']:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                table_counts[table] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                table_counts[table] = 0

        # Kanban tables
        kanban_tables = ['kanban_projects', 'kanban_boards', 'kanban_columns', 'kanban_tasks', 'kanban_comments', 'kanban_wiki']
        for table in kanban_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                table_counts[table] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                table_counts[table] = 0

        conn.close()

        data = {
            "status": "healthy",
            "database_path": db_path,
            "database_exists": Path(db_path).exists(),
            "database_size_mb": round(Path(db_path).stat().st_size / (1024 * 1024), 2) if Path(db_path).exists() else 0,
            "table_counts": table_counts
        }

        return SuccessResponse(
            data=data,
            message="Database health retrieved successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get database health", exc_info=True)
        # Return partial health info even on error (non-critical monitoring endpoint)
        partial_data = {
            "status": "error",
            "database_path": str(PATHS.app_db),
            "database_exists": False,
            "table_counts": {},
            "partial": True
        }
        return SuccessResponse(
            data=partial_data,
            message="Partial database health retrieved (error occurred)"
        )
