"""
Workflow Storage Base

Shared database connection and path management for workflow storage.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def get_db_path(db_path: Optional[str] = None) -> Path:
    """
    Get the database path for workflow storage.

    Args:
        db_path: Optional explicit path, otherwise uses config

    Returns:
        Path to the workflows database
    """
    if db_path is not None:
        return Path(db_path)

    try:
        from api.config_paths import get_config_paths
    except ImportError:
        from config_paths import get_config_paths

    paths = get_config_paths()
    return Path(paths.data_dir) / "workflows.db"


def get_connection(db_path: Path) -> sqlite3.Connection:
    """
    Get a database connection with row factory.

    Args:
        db_path: Path to the database

    Returns:
        SQLite connection with Row factory
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
