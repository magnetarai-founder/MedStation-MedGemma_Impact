#!/usr/bin/env python3
"""
Phase 5 Migration: Team Model Policies

Adds team_model_policies table for controlling which models teams can use.

Sprint 5 Theme A: Team-Level Model Policies
"""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def run_migration(db_path: Path) -> bool:
    """
    Apply Phase 5 team model policies migration

    Args:
        db_path: Path to SQLite database

    Returns:
        True if migration successful
    """
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        logger.info("Running Phase 5 migration: Team Model Policies")

        # Create team_model_policies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_model_policies (
                team_id TEXT PRIMARY KEY,
                allowed_models TEXT NOT NULL,
                default_model TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
            )
        """)

        # Create index on team_id for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_team_model_policies_team_id
            ON team_model_policies(team_id)
        """)

        conn.commit()
        conn.close()

        logger.info("Phase 5 migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Phase 5 migration failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # Test migration
    from config_paths import get_data_dir
    data_dir = get_data_dir()
    db_path = data_dir / "elohim.db"

    logging.basicConfig(level=logging.INFO)
    success = run_migration(db_path)

    if success:
        print("✅ Phase 5 migration completed")
    else:
        print("❌ Phase 5 migration failed")
