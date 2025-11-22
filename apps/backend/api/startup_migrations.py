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
            from .migrations import phase1_5_per_user_models as phase1_5_migration
            from .migrations import phase1b_password_reset as phase1b_migration
            from .migrations import phase2_permissions_rbac as phase2_migration
            from .migrations import phase25_rbac_hardening as phase25_migration
            from .migrations import phase3_team_mode as phase3_migration
            from .migrations import phase35_workflow_type as phase35_migration
            from .migrations import phase4_performance_indexes as phase4_migration
            # Sprint 6 analytics migrations
            from .migrations import phase6_analytics as phase6_analytics_migration
            from .migrations import phase6_model_kpis as phase6_kpis_migration
            # Phase B: Kanban workspace
            from .migrations import phaseB_kanban as phaseB_kanban_migration
            # Auth migrations (AUTH-P1)
            from .migrations.auth import run_auth_migrations
        except ImportError:
            from migrations import phase0_user_db as phase0_migration
            from migrations import phase1_workflows_user_id as phase1_migration
            from migrations import phase1_5_per_user_models as phase1_5_migration
            from migrations import phase1b_password_reset as phase1b_migration
            from migrations import phase2_permissions_rbac as phase2_migration
            from migrations import phase25_rbac_hardening as phase25_migration
            from migrations import phase3_team_mode as phase3_migration
            from migrations import phase35_workflow_type as phase35_migration
            from migrations import phase4_performance_indexes as phase4_migration
            # Sprint 6 analytics migrations
            from migrations import phase6_analytics as phase6_analytics_migration
            from migrations import phase6_model_kpis as phase6_kpis_migration
            # Phase B: Kanban workspace
            from migrations import phaseB_kanban as phaseB_kanban_migration
            # Auth migrations (AUTH-P1)
            from migrations.auth import run_auth_migrations

        # ===== AUTH: Consolidated Auth Schema (AUTH-P1 + AUTH-P2) =====
        # Run auth migrations FIRST - ensures auth schema is always in place
        # before other migrations that depend on it
        app_db = PATHS.app_db
        import sqlite3
        try:
            conn = sqlite3.connect(str(app_db))

            # AUTH-P1: Run auth migrations
            run_auth_migrations(conn)

            # AUTH-P2: Bootstrap Founder user in dev mode
            try:
                from .auth_bootstrap import ensure_dev_founder_user
            except ImportError:
                from auth_bootstrap import ensure_dev_founder_user

            ensure_dev_founder_user(conn)

            # AUTH-P6: Ensure device identity exists
            try:
                from .device_identity import ensure_device_identity
            except ImportError:
                from device_identity import ensure_device_identity

            device_id = ensure_device_identity(conn)
            logger.info(f"Device identity confirmed: {device_id}")

            conn.close()
            # Note: Auth migrations track their own completion state
            # Only log if migrations actually ran (auth runner logs this internally)
        except Exception as e:
            logger.error(f"Auth migrations failed: {e}", exc_info=True)
            raise

        # ===== Phase 0: Database Architecture Consolidation =====
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

        # ===== Phase 1.5: Per-User Model Preferences =====
        # Use data directory for legacy hot_slots/config files if present
        # Some environments may not define backend_dir on PATHS
        try:
            config_dir = PATHS.data_dir
        except AttributeError:
            config_dir = Path('.')

        if not phase1_5_migration.check_migration_applied(app_db):
            migrations_ran.append("Phase 1.5: Per-User Model Preferences")
            logger.info("Running Phase 1.5 migration: Per-User Model Preferences")
            success = phase1_5_migration.migrate_phase1_5_per_user_models(app_db, config_dir)

            if not success:
                raise Exception("Phase 1.5 migration failed - see logs above")

            logger.info("✓ Phase 1.5 migration completed successfully")

        # ===== Phase 1B: Password Reset Support =====
        if phase1b_migration.run_migration(app_db):
            migrations_ran.append("Phase 1B: Password Reset Support")

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

        # ===== Phase 4: Performance Optimization (Indexes) =====
        if not phase4_migration.check_migration_applied(app_db):
            migrations_ran.append("Phase 4: Performance Optimization (Indexes)")
            logger.info("Running Phase 4 migration: Performance Optimization")
            success = phase4_migration.migrate_phase4_performance_indexes(app_db)

            if not success:
                raise Exception("Phase 4 migration failed - see logs above")

            logger.info("✓ Phase 4 migration completed successfully")

        # ===== Phase 6: Analytics Schema =====
        # Phase 6: Analytics Schema
        if not phase6_analytics_migration.check_migration_applied(str(app_db)):
            migrations_ran.append("Phase 6: Analytics Schema")
            logger.info("Running Phase 6 migration: Analytics Schema")
            phase6_analytics_migration.migrate(str(app_db))

            logger.info("✓ Phase 6 analytics migration completed successfully")

        # ===== Phase 6.1: Model KPIs Extension =====
        # Phase 6.1: Model KPIs Extension
        if not phase6_kpis_migration.check_migration_applied(str(app_db)):
            migrations_ran.append("Phase 6.1: Model KPIs Extension")
            logger.info("Running Phase 6.1 migration: Model KPIs Extension")
            phase6_kpis_migration.migrate(str(app_db))

            logger.info("✓ Phase 6.1 model KPIs migration completed successfully")

        # ===== Phase B: Kanban Workspace =====
        try:
            # Simple migration without state tracking (table check inside migrate())
            phaseB_kanban_migration.migrate(str(app_db))
            migrations_ran.append("Phase B: Kanban Workspace")
        except Exception as e:
            # If migration already applied, this is fine
            if "already applied" not in str(e).lower():
                logger.error(f"Phase B migration failed: {e}")

        # ===== AUTH-P3: Session Cleanup =====
        # Clean up expired sessions on startup (housekeeping)
        try:
            from api.auth_middleware import AuthService
            auth_service = AuthService(db_path=app_db)
            auth_service.cleanup_expired_sessions()
        except Exception as e:
            # Non-fatal: log but don't block startup
            logger.warning(f"Session cleanup failed (non-fatal): {e}")

        # ===== AGENT-PHASE-2: Seed Global Workflow Templates =====
        # Seed high-quality global templates (idempotent)
        try:
            from api.workflow_seed_templates import seed_global_workflow_templates
            from api.workflow_storage import WorkflowStorage

            storage = WorkflowStorage()  # Uses default workflows.db
            seed_global_workflow_templates(storage)
        except Exception as e:
            # Non-fatal: log but don't block startup
            logger.warning(f"Workflow template seeding failed (non-fatal): {e}")

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
