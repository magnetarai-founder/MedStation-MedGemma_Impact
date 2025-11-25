"""
Startup database migrations.

Runs consolidation migrations and schema setup on application startup.
"""

import logging
import platform

logger = logging.getLogger(__name__)


async def run_startup_migrations() -> None:
    """
    Run DB migrations or other one-time startup tasks.

    This includes:
    - macOS platform validation
    - Database consolidation migrations
    - Schema setup

    Raises:
        RuntimeError: If not running on macOS (ElohimOS is macOS-only)
        Exception: If migrations fail (prevents app from starting with broken DB state)
    """
    # macOS-only check
    if platform.system() != "Darwin":
        raise RuntimeError(f"ElohimOS is macOS-only. Detected OS: {platform.system()}")

    # Run startup migrations (database consolidation)
    try:
        from startup_migrations import run_startup_migrations as _run_migrations
        await _run_migrations()
        logger.info("✓ Startup migrations completed")
    except ModuleNotFoundError:
        logger.warning("✗ Startup migrations module not found - skipping")
    except Exception as e:
        logger.error(f"✗ Startup migrations failed: {e}", exc_info=True)
        # Re-raise to prevent app from starting with broken DB state
        raise
