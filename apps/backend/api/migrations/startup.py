#!/usr/bin/env python3
"""
Startup Migrations Runner for MedStation

Runs database migrations automatically on application startup.
Non-interactive - no user prompts required.

Usage:
    from startup_migrations import run_startup_migrations
    await run_startup_migrations()  # Call during app lifespan startup
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def run_startup_migrations() -> None:
    """
    Run all pending database migrations on application startup

    This function is non-interactive and safe to call on every startup.
    Migrations track their own state and only run once.

    Raises:
        Exception: If a critical migration fails
    """
    try:
        # Track if any migrations actually ran
        migrations_ran = []

        # Import config_paths to get database locations
        from api.config_paths import PATHS

        # Auth migrations only (enterprise migrations stripped for MedStation)
        from api.migrations.auth import run_auth_migrations

        app_db = PATHS.app_db
        import sqlite3
        try:
            conn = sqlite3.connect(str(app_db))

            # Run auth schema migrations
            run_auth_migrations(conn)

            # Bootstrap dev user
            from api.auth_bootstrap import ensure_dev_founder_user
            ensure_dev_founder_user(conn)

            # Ensure device identity
            from api.device_identity import ensure_device_identity
            device_id = ensure_device_identity(conn)
            logger.info(f"Device identity confirmed: {device_id}")

            conn.close()
        except Exception as e:
            logger.error(f"Auth migrations failed: {e}", exc_info=True)
            raise

        # Session cleanup (housekeeping)
        try:
            from api.auth_middleware import AuthService
            auth_service = AuthService(db_path=app_db)
            auth_service.cleanup_expired_sessions()
        except Exception as e:
            logger.warning(f"Session cleanup failed (non-fatal): {e}")

        # Summary output - only show if migrations ran
        if migrations_ran:
            logger.info("=" * 60)
            logger.info(f"✓ Completed {len(migrations_ran)} migration(s)")
            logger.info("=" * 60)
        else:
            logger.info("✓ Startup migrations completed")

    except Exception as e:
        logger.error(f"✗ Startup migrations failed: {e}", exc_info=True)
        raise  # Re-raise to prevent app from starting with broken DB state
