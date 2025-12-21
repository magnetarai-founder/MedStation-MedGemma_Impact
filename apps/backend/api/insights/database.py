"""
Insights Lab Database Module

Database schema, connection management, and initialization.
"""

import sqlite3
import logging
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict

try:
    from api.config_paths import get_config_paths
except ImportError:
    from config_paths import get_config_paths

logger = logging.getLogger(__name__)

# Storage paths
PATHS = get_config_paths()
INSIGHTS_DIR = PATHS.data_dir / "insights"
RECORDINGS_DIR = INSIGHTS_DIR / "recordings"
INSIGHTS_DB_PATH = INSIGHTS_DIR / "insights.db"

# Ensure directories exist
INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

# Whitelisted columns for SQL UPDATE to prevent injection
RECORDING_UPDATE_COLUMNS = frozenset({"title", "tags", "folder_id"})
TEMPLATE_UPDATE_COLUMNS = frozenset({"name", "description", "system_prompt", "category", "output_format"})

DATABASE_SCHEMA = """
-- Recordings table (voice recording vault)
CREATE TABLE IF NOT EXISTS recordings (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    file_path TEXT NOT NULL,
    duration REAL DEFAULT 0,
    transcript TEXT NOT NULL,
    speaker_segments TEXT,
    user_id TEXT NOT NULL,
    team_id TEXT,
    folder_id TEXT,
    tags TEXT DEFAULT '[]',
    created_at TEXT NOT NULL
);

-- Templates table (formatting blueprints)
CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'GENERAL',
    is_builtin INTEGER DEFAULT 0,
    output_format TEXT DEFAULT 'MARKDOWN',
    created_by TEXT NOT NULL,
    team_id TEXT,
    created_at TEXT NOT NULL
);

-- Formatted outputs table (template-applied results)
CREATE TABLE IF NOT EXISTS formatted_outputs (
    id TEXT PRIMARY KEY,
    recording_id TEXT NOT NULL,
    template_id TEXT NOT NULL,
    template_name TEXT NOT NULL,
    content TEXT NOT NULL,
    format TEXT DEFAULT 'MARKDOWN',
    metadata TEXT,
    generated_at TEXT NOT NULL,
    FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE,
    FOREIGN KEY (template_id) REFERENCES templates(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_recordings_user ON recordings(user_id);
CREATE INDEX IF NOT EXISTS idx_recordings_team ON recordings(team_id);
CREATE INDEX IF NOT EXISTS idx_recordings_created ON recordings(created_at);
CREATE INDEX IF NOT EXISTS idx_templates_category ON templates(category);
CREATE INDEX IF NOT EXISTS idx_templates_builtin ON templates(is_builtin);
CREATE INDEX IF NOT EXISTS idx_outputs_recording ON formatted_outputs(recording_id);
"""


def get_db() -> sqlite3.Connection:
    """Get database connection with row factory"""
    conn = sqlite3.connect(str(INSIGHTS_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def build_safe_update(updates_dict: Dict[str, Any], allowed_columns: frozenset) -> tuple[list, list]:
    """
    Build safe SQL UPDATE clause with whitelist validation.

    Args:
        updates_dict: Dict of column_name -> value pairs
        allowed_columns: Frozenset of allowed column names

    Returns:
        Tuple of (update_clauses, params) for use in SQL query

    Raises:
        ValueError: If any column is not in the whitelist
    """
    clauses = []
    params = []

    for column, value in updates_dict.items():
        if column not in allowed_columns:
            raise ValueError(f"Invalid column for update: {column}")
        clauses.append(f"{column} = ?")
        params.append(value)

    return clauses, params


def init_insights_db():
    """Initialize insights database tables and built-in templates"""
    from .templates import BUILTIN_TEMPLATES

    conn = get_db()
    cursor = conn.cursor()

    # Create tables
    cursor.executescript(DATABASE_SCHEMA)

    # Insert built-in templates
    now = datetime.now(UTC).isoformat()
    for template in BUILTIN_TEMPLATES:
        cursor.execute("""
            INSERT OR IGNORE INTO templates
            (id, name, description, system_prompt, category, is_builtin, output_format, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, 'system', ?)
        """, (
            template["id"],
            template["name"],
            template["description"],
            template["system_prompt"],
            template["category"],
            template["output_format"],
            now
        ))

    conn.commit()
    conn.close()
    logger.info("Insights Lab database initialized")


__all__ = [
    "get_db",
    "init_insights_db",
    "build_safe_update",
    "DATABASE_SCHEMA",
    "INSIGHTS_DIR",
    "RECORDINGS_DIR",
    "INSIGHTS_DB_PATH",
    "RECORDING_UPDATE_COLUMNS",
    "TEMPLATE_UPDATE_COLUMNS",
]
