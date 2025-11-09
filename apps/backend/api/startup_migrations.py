#!/usr/bin/env python3
"""
Startup Migrations Runner for ElohimOS

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
        try:
            from .config_paths import PATHS
        except ImportError:
            from config_paths import PATHS

        # Import migrations
        try:
            from .migrations import phase0_user_db as phase0_migration
            from .migrations import phase1_workflows_user_id as phase1_migration
            from .migrations import phase2_permissions_rbac as phase2_migration
            from .migrations import phase25_rbac_hardening as phase25_migration
            from .migrations import phase3_team_mode as phase3_migration
            from .migrations import phase35_workflow_type as phase35_migration
        except ImportError:
            from migrations import phase0_user_db as phase0_migration
            from migrations import phase1_workflows_user_id as phase1_migration
            from migrations import phase2_permissions_rbac as phase2_migration
            from migrations import phase25_rbac_hardening as phase25_migration
            from migrations import phase3_team_mode as phase3_migration
            from migrations import phase35_workflow_type as phase35_migration

        # ===== Phase 0: Database Architecture Consolidation =====
        app_db = PATHS.app_db
        legacy_users_db = PATHS.data_dir / "users.db"  # Legacy location

        if not phase0_migration.check_migration_applied(app_db):
            migrations_ran.append("Phase 0: Database Architecture Consolidation")
            logger.info("Running Phase 0 migration: Database Architecture Consolidation")
            success = phase0_migration.migrate_phase0_user_db(app_db, legacy_users_db)

            if not success:
                raise Exception("Phase 0 migration failed - see logs above")

            logger.info("✓ Phase 0 migration completed successfully")

        # ===== Phase 1: Workflow User Isolation =====
        workflows_db = PATHS.data_dir / "workflows.db"  # Canonical location

        if not phase1_migration.check_migration_applied(app_db):
            migrations_ran.append("Phase 1: Workflow User Isolation")
            logger.info("Running Phase 1 migration: Workflow User Isolation")
            success = phase1_migration.migrate_phase1_workflows_user_id(app_db, workflows_db)

            if not success:
                raise Exception("Phase 1 migration failed - see logs above")

            logger.info("✓ Phase 1 migration completed successfully")

        # ===== Phase 2: Salesforce-style RBAC =====
        if not phase2_migration.check_migration_applied(app_db):
            migrations_ran.append("Phase 2: Salesforce-style RBAC")
            logger.info("Running Phase 2 migration: Salesforce-style RBAC")
            success = phase2_migration.migrate_phase2_permissions_rbac(app_db)

            if not success:
                raise Exception("Phase 2 migration failed - see logs above")

            logger.info("✓ Phase 2 migration completed successfully")

        # ===== Phase 2.5: RBAC Hardening =====
        if not phase25_migration.check_migration_applied(app_db):
            migrations_ran.append("Phase 2.5: RBAC Hardening")
            logger.info("Running Phase 2.5 migration: RBAC Hardening & Developer UX")
            success = phase25_migration.migrate_phase25_rbac_hardening(app_db)

            if not success:
                raise Exception("Phase 2.5 migration failed - see logs above")

            logger.info("✓ Phase 2.5 migration completed successfully")

        # ===== Phase 3: Team Mode =====
        if not phase3_migration.check_migration_applied(app_db):
            migrations_ran.append("Phase 3: Team Mode")
            logger.info("Running Phase 3 migration: Team Mode")
            success = phase3_migration.migrate_phase3_team_mode(app_db)

            if not success:
                raise Exception("Phase 3 migration failed - see logs above")

            logger.info("✓ Phase 3 migration completed successfully")

        # ===== Phase 3.5: Workflow Type Column =====
        if not phase35_migration.check_migration_applied(app_db):
            migrations_ran.append("Phase 3.5: Workflow Type Column")
            logger.info("Running Phase 3.5 migration: Workflow Type Column")
            success = phase35_migration.migrate_phase35_workflow_type(app_db, workflows_db)

            if not success:
                raise Exception("Phase 3.5 migration failed - see logs above")

            logger.info("✓ Phase 3.5 migration completed successfully")

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
