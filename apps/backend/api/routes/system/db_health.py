"""
Database Health Endpoint

Returns database path and table counts for admin monitoring.
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter()

try:
    from api.config_paths import PATHS
    # Use founder rights dependency from admin_service
    from api.admin_service import require_founder_rights
except ImportError:
    from config_paths import PATHS
    from admin_service import require_founder_rights


@router.get("/db-health")
async def get_db_health(user: dict = Depends(require_founder_rights)) -> Dict[str, Any]:
    """
    Get database health information (Founder Rights only)

    Returns:
    - Database file path
    - Table counts for key tables including Kanban workspace
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

        return {
            "status": "healthy",
            "database_path": db_path,
            "database_exists": Path(db_path).exists(),
            "database_size_mb": round(Path(db_path).stat().st_size / (1024 * 1024), 2) if Path(db_path).exists() else 0,
            "table_counts": table_counts
        }

    except Exception as e:
        logger.error(f"Failed to get database health: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "database_path": str(PATHS.app_db),
            "database_exists": False,
            "table_counts": {}
        }
