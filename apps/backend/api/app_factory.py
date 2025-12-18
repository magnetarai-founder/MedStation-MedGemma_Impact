"""
FastAPI application factory for ElohimOS.

Creates and configures the FastAPI application with all middleware,
routers, and startup/shutdown logic.
"""

import asyncio
import logging
import os
import signal
import uuid as uuid_lib
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path

from fastapi import FastAPI, Request

logger = logging.getLogger(__name__)

# Request ID context for structured logging
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def cleanup_sessions():
    """Clean up all active sessions and close database connections"""
    # Import sessions dict from main.state module
    from api.main.state import sessions

    logger.info("Cleaning up sessions...")
    try:
        # Clean up session engines
        # Use list() to avoid RuntimeError if sessions dict is modified during iteration
        for session_id, session in list(sessions.items()):
            if 'engine' in session:
                try:
                    session['engine'].close()
                    logger.debug(f"Closed engine for session {session_id}")
                except Exception as e:
                    logger.error(f"Error closing engine for session {session_id}: {e}")

        logger.info("Session cleanup complete")
    except Exception as e:
        logger.error(f"Error during session cleanup: {e}")


def handle_shutdown_signal(signum, frame):
    """Handle SIGTERM/SIGINT for graceful shutdown"""
    sig_name = signal.Signals(signum).name
    logger.warning(f"Received {sig_name} - initiating graceful shutdown...")
    cleanup_sessions()
    logger.info("Graceful shutdown complete")
    # Exit cleanly
    os._exit(0)


async def cleanup_old_temp_files():
    """Background task to clean up old temporary files"""
    from datetime import datetime, timedelta

    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour

            api_dir = Path(__file__).parent
            cutoff_time = datetime.now() - timedelta(hours=24)  # Delete files older than 24 hours

            for temp_dir in [api_dir / "temp_uploads", api_dir / "temp_exports"]:
                if temp_dir.exists():
                    for file_path in temp_dir.glob("*"):
                        if file_path.is_file():
                            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                            if file_mtime < cutoff_time:
                                file_path.unlink()
                                logger.debug(f"Cleaned up old temp file: {file_path.name}")
        except Exception as e:
            logger.error(f"Temp file cleanup error: {e}")


async def vacuum_databases():
    """
    Background task to VACUUM SQLite databases weekly

    Runs weekly to:
    - Defragment database files
    - Reclaim deleted space
    - Rebuild indexes
    - Reduce file size

    Critical for long-running offline deployments
    """
    import sqlite3

    def _vacuum_db(db_path: Path, db_name: str):
        """Helper to VACUUM a single database"""
        with sqlite3.connect(str(db_path)) as conn:
            conn.isolation_level = None  # Autocommit mode required for VACUUM
            conn.execute("VACUUM")
            conn.execute("ANALYZE")  # Update query planner statistics
        logger.info(f"✅ VACUUMed {db_name} database")

    while True:
        try:
            # Run once per week
            await asyncio.sleep(7 * 24 * 3600)  # 7 days

            logger.info("Starting weekly database VACUUM maintenance...")

            # VACUUM auth database
            try:
                from auth_middleware import auth_service
                await asyncio.to_thread(lambda: _vacuum_db(auth_service.db_path, "auth"))
            except Exception as e:
                logger.error(f"Failed to VACUUM auth database: {e}")

            # VACUUM data engine database
            try:
                from data_engine import get_data_engine
                engine = get_data_engine()
                if engine and engine.db_path:
                    await asyncio.to_thread(lambda: _vacuum_db(engine.db_path, "data"))
            except Exception as e:
                logger.error(f"Failed to VACUUM data engine: {e}")

            # VACUUM P2P codes database
            try:
                from p2p_mesh_service import CODES_DB_PATH
                if CODES_DB_PATH.exists():
                    await asyncio.to_thread(lambda: _vacuum_db(CODES_DB_PATH, "p2p_codes"))
            except Exception as e:
                logger.error(f"Failed to VACUUM P2P codes: {e}")

            logger.info("✅ Database VACUUM maintenance completed")

        except Exception as e:
            logger.error(f"Database VACUUM error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown logic for the FastAPI application.
    """
    # ===== STARTUP =====
    print("Starting MagnetarStudio API...")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    logger.info("Registered SIGTERM/SIGINT handlers for graceful shutdown")

    # Create necessary directories
    api_dir = Path(__file__).parent
    (api_dir / "temp_uploads").mkdir(exist_ok=True)
    (api_dir / "temp_exports").mkdir(exist_ok=True)

    # Run startup initialization
    from api.startup import (
        run_startup_migrations,
        initialize_ollama,
        initialize_metal4,
        run_health_checks
    )

    await run_startup_migrations()
    await initialize_ollama()
    initialize_metal4()
    await run_health_checks()

    # Register routers
    from api.router_registry import register_routers
    services_loaded, services_failed = register_routers(app)

    # Initialize additional services (non-router services)
    # Prometheus Metrics API (Phase 5.2: Monitoring & Observability)
    try:
        from prometheus_metrics import get_prometheus_exporter
        prometheus_exporter = get_prometheus_exporter()
        services_loaded.append("Prometheus Metrics")
    except ImportError as e:
        logger.warning(f"Could not import prometheus_metrics: {e}")
        prometheus_exporter = None

    # Health Diagnostics (Phase 5.4: Comprehensive health checks)
    try:
        from health_diagnostics import get_health_diagnostics
        health_diagnostics = get_health_diagnostics()
        services_loaded.append("Health Diagnostics")
    except ImportError as e:
        logger.warning(f"Could not import health_diagnostics: {e}")
        health_diagnostics = None

    # Log summary of loaded services
    if services_loaded:
        logger.info(f"✓ Services: {', '.join(services_loaded)}")
    if services_failed:
        logger.warning(f"✗ Failed: {', '.join(services_failed)}")

    # Start background maintenance tasks
    cleanup_task = asyncio.create_task(cleanup_old_temp_files())
    vacuum_task = asyncio.create_task(vacuum_databases())
    logger.info("Started background maintenance tasks (cleanup + VACUUM)")

    yield

    # ===== SHUTDOWN =====
    print("Shutting down...")
    cleanup_task.cancel()
    vacuum_task.cancel()

    # Stop background jobs
    try:
        from api.background_jobs import get_job_manager
        job_manager = get_job_manager()
        await job_manager.stop()
    except Exception as e:
        logger.warning(f"Error stopping background jobs: {e}")

    # Close all database connection pools (Sprint 1 - RACE-04)
    try:
        from api.db_pool import close_all_pools
        close_all_pools()
        logger.info("Database connection pools closed")
    except Exception as e:
        logger.warning(f"Error closing connection pools: {e}")

    # Close password breach checker session (MED-02)
    try:
        from api.password_breach_checker import cleanup_breach_checker
        await cleanup_breach_checker()
        logger.info("Password breach checker session closed")
    except Exception as e:
        logger.warning(f"Error closing breach checker: {e}")

    cleanup_sessions()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application for ElohimOS.

    This factory function encapsulates:
    - App instantiation
    - Middleware registration (CORS, rate limiting, error handlers)
    - Request ID tracking middleware
    - Router registration via router_registry
    - Startup/shutdown hooks

    Returns:
        Configured FastAPI application instance
    """
    # Create FastAPI app with lifespan context
    app = FastAPI(
        title="MagnetarStudio API",
        description="""
## MagnetarStudio - Offline-First AI Operating System

MagnetarStudio is a secure, privacy-first AI platform designed for mission-critical operations
in disconnected environments.

### Core Features
* **Local AI Inference** - Ollama integration with Metal 4 GPU acceleration
* **Agent Orchestrator** - Integrated Aider + Continue + Codex for AI coding
* **Secure Data Processing** - SQL engine with AES-256-GCM encryption
* **P2P Mesh Networking** - Offline device-to-device collaboration
* **RBAC Permissions** - Salesforce-style role-based access control
* **Zero-Trust Security** - End-to-end encryption, audit logging, panic mode

### Authentication
All endpoints require JWT authentication via `Authorization: Bearer <token>` header.
Get your token via `/api/v1/auth/login`.

### Rate Limiting
Global limit: 100 requests/minute. Endpoint-specific limits documented below.
        """,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",  # Swagger UI at /api/docs
        redoc_url="/api/redoc",  # ReDoc at /api/redoc
        openapi_url="/api/openapi.json",  # OpenAPI schema
        contact={
            "name": "ElohimOS Support",
            "url": "https://github.com/yourusername/elohimos",
        },
        license_info={
            "name": "Proprietary",
            "url": "https://elohimos.local/license",
        },
    )

    # Configure middleware
    from api.middleware import (
        configure_cors,
        configure_rate_limiting,
        register_error_handlers
    )
    from api.middleware.security_headers import add_security_headers
    import os

    # Security headers (MED-04 fix - add OWASP recommended headers)
    add_security_headers(app)

    # CRITICAL-02 FIX: Removed SanitizationMiddleware
    # It provided FALSE SECURITY - could not actually modify immutable requests
    # Input validation is handled by Pydantic models at the endpoint level
    # See CRITICAL_BUGS_FOUND.md for details

    configure_cors(app)
    limiter = configure_rate_limiting(app)
    register_error_handlers(app)

    # Middleware to add request ID to all requests
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        """Add unique request ID for tracing and structured logging"""
        request_id = request.headers.get("X-Request-ID", str(uuid_lib.uuid4()))
        request_id_ctx.set(request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    return app


# Create app instance for uvicorn
app = create_app()
