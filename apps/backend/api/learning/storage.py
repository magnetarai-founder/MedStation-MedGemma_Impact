"""
Learning System - Storage Layer

SQLite database operations for the learning system:
- Database connection management
- Table creation and schema migrations
- Generic query helpers

Extracted from learning_system.py during Phase 6.3c modularization.
"""

import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def get_default_db_path() -> Path:
    """Get the default database path for the learning system."""
    try:
        from api.config_paths import get_config_paths
    except ImportError:
        from config_paths import get_config_paths

    paths = get_config_paths()
    return paths.data_dir / "learning.db"


def create_connection(db_path: Path) -> sqlite3.Connection:
    """
    Create a SQLite connection for the learning system.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        SQLite connection with Row factory enabled
    """
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def setup_database(conn: sqlite3.Connection) -> None:
    """
    Create and migrate learning system tables.

    Creates tables for:
    - success_patterns: Success/failure tracking
    - user_preferences: Learned user preferences
    - coding_styles: Detected coding styles
    - project_contexts: Project-specific context
    - recommendations: Recommendation log
    - learning_feedback: User feedback and satisfaction

    Args:
        conn: SQLite database connection
    """
    # Success tracking
    conn.execute("""
        CREATE TABLE IF NOT EXISTS success_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_hash TEXT UNIQUE,
            pattern_type TEXT,  -- command, workflow, tool_combo
            pattern_data TEXT,  -- JSON
            success_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            total_count INTEGER DEFAULT 0,
            avg_time REAL,
            last_seen DATETIME,
            confidence REAL
        )
    """)

    # Add total_count column if it doesn't exist (migration)
    try:
        conn.execute("ALTER TABLE success_patterns ADD COLUMN total_count INTEGER DEFAULT 0")
        conn.execute("UPDATE success_patterns SET total_count = success_count + failure_count")
    except sqlite3.OperationalError:
        # Column already exists
        pass

    # User preferences
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            preference TEXT,
            positive_signals INTEGER DEFAULT 0,
            negative_signals INTEGER DEFAULT 0,
            confidence REAL,
            last_observed DATETIME,
            UNIQUE(category, preference)
        )
    """)

    # Coding style patterns
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coding_styles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            language TEXT,
            file_pattern TEXT,
            style_data TEXT,  -- JSON with style rules
            sample_count INTEGER DEFAULT 0,
            confidence REAL,
            last_updated DATETIME
        )
    """)

    # Project contexts
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_contexts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_path TEXT UNIQUE,
            project_type TEXT,
            project_data TEXT,  -- JSON with full context
            activity_count INTEGER DEFAULT 0,
            last_active DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Recommendations log
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recommendation_type TEXT,
            action TEXT,
            reason TEXT,
            confidence REAL,
            was_accepted BOOLEAN,
            feedback TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Learning feedback
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command TEXT,
            tool_used TEXT,
            execution_time REAL,
            success BOOLEAN,
            user_satisfaction INTEGER,  -- 1-5 scale, NULL if not provided
            context_data TEXT,  -- JSON
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    logger.debug("Learning system database initialized")
