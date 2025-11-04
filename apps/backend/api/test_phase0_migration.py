#!/usr/bin/env python3
"""
Test script for Phase 0 migration

Run this to test the migration without starting the full server.
"""

import sys
import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_migration():
    """Test Phase 0 migration"""
    try:
        logger.info("=" * 60)
        logger.info("Testing Phase 0 Migration")
        logger.info("=" * 60)

        # Import startup migrations
        from startup_migrations import run_startup_migrations

        # Run migrations
        await run_startup_migrations()

        logger.info("=" * 60)
        logger.info("✓ Migration test completed successfully")
        logger.info("=" * 60)

        # Verify the migration
        from config_paths import PATHS
        import sqlite3

        app_db = PATHS.app_db
        if not app_db.exists():
            logger.error(f"✗ app_db does not exist at {app_db}")
            return False

        logger.info(f"\nVerifying {app_db}...")
        conn = sqlite3.connect(str(app_db))
        cursor = conn.cursor()

        # Check users table
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        logger.info(f"  Users table: {user_count} users")

        # Check user_profiles table
        cursor.execute("SELECT COUNT(*) FROM user_profiles")
        profile_count = cursor.fetchone()[0]
        logger.info(f"  User_profiles table: {profile_count} profiles")

        # Check sessions table
        cursor.execute("SELECT COUNT(*) FROM sessions")
        session_count = cursor.fetchone()[0]
        logger.info(f"  Sessions table: {session_count} sessions")

        # Check migrations table
        cursor.execute("SELECT * FROM migrations")
        migrations = cursor.fetchall()
        logger.info(f"  Migrations applied: {len(migrations)}")
        for migration in migrations:
            logger.info(f"    - {migration[0]} (applied: {migration[1]})")

        # Check schema
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        logger.info(f"  Users columns: {', '.join(columns)}")

        if 'role' not in columns:
            logger.error("  ✗ 'role' column missing from users table!")
            return False

        if 'job_role' not in columns:
            logger.warning("  ⚠ 'job_role' column missing from users table (optional)")

        conn.close()

        logger.info("\n✓ All checks passed!")
        return True

    except Exception as e:
        logger.error(f"✗ Migration test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(test_migration())
    sys.exit(0 if success else 1)
