"""
FastAPI application factory for MedStation.

Creates and configures the FastAPI application with middleware,
routers, and startup/shutdown logic.
"""

import asyncio
import logging
import os
import signal
import uuid as uuid_lib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Request, Response

logger = logging.getLogger(__name__)

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def cleanup_sessions() -> None:
    """Clean up all active sessions and close database connections"""
    from api.core.state import sessions

    logger.info("Cleaning up sessions...")
    try:
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


def handle_shutdown_signal(signum: int, frame) -> None:
    """Handle SIGTERM/SIGINT for graceful shutdown"""
    sig_name = signal.Signals(signum).name
    logger.warning(f"Received {sig_name} - initiating graceful shutdown...")
    cleanup_sessions()
    logger.info("Graceful shutdown complete")
    os._exit(0)


async def cleanup_old_temp_files() -> None:
    """Background task to clean up old temporary files"""
    from datetime import datetime, timedelta

    while True:
        try:
            await asyncio.sleep(3600)

            api_dir = Path(__file__).parent
            cutoff_time = datetime.now() - timedelta(hours=24)

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    logger.info("Starting MedStation API...")

    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    logger.info("Registered SIGTERM/SIGINT handlers for graceful shutdown")

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

    # Enable connection pool metrics
    try:
        from api.db.pool import enable_pool_metrics
        enable_pool_metrics()
        logger.info("Connection pool metrics enabled")
    except Exception as e:
        logger.warning(f"Could not enable pool metrics: {e}")

    # Register routers
    from api.router_registry import register_routers
    services_loaded, services_failed = register_routers(app)

    if services_loaded:
        logger.info(f"Services: {', '.join(services_loaded)}")
    if services_failed:
        logger.warning(f"Failed: {', '.join(services_failed)}")

    # Start background maintenance
    cleanup_task = asyncio.create_task(cleanup_old_temp_files())
    logger.info("Started background maintenance tasks")

    yield

    # SHUTDOWN
    logger.info("Shutting down...")
    cleanup_task.cancel()

    # Close database connection pools
    try:
        from api.db_pool import close_all_pools
        close_all_pools()
        logger.info("Database connection pools closed")
    except Exception as e:
        logger.warning(f"Error closing connection pools: {e}")

    cleanup_sessions()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application for MedStation.
    """
    app = FastAPI(
        title="MedStation API",
        description="""
## MedStation - Medical AI Assistant

MedStation is a privacy-first medical AI platform powered by MedGemma.

### Core Features
* **Local AI Inference** - MedGemma 4B via Ollama with Metal GPU acceleration
* **5-Step Agentic Workflow** - Symptom analysis, triage, differential Dx, risk stratification, recommendations
* **9-Category Safety Guard** - Emergency escalation, red flags, drug interactions, bias detection
* **FHIR R4 Export** - Healthcare interoperability
* **SHA-256 Audit Trail** - Privacy-preserving logging

### Authentication
All endpoints require JWT authentication via `Authorization: Bearer <token>` header.
Get your token via `/api/v1/auth/login`.
        """,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        license_info={
            "name": "CC BY 4.0",
            "url": "https://creativecommons.org/licenses/by/4.0/",
        },
    )

    # Configure middleware
    from api.middleware import (
        configure_cors,
        configure_rate_limiting,
        register_error_handlers
    )
    from api.middleware.security_headers import add_security_headers

    add_security_headers(app)
    configure_cors(app)
    limiter = configure_rate_limiting(app)
    register_error_handlers(app)

    # Observability middleware
    try:
        from api.observability_middleware import add_observability_middleware
        add_observability_middleware(app)
        logger.info("Observability middleware enabled")
    except Exception as e:
        logger.warning(f"Could not enable observability middleware: {e}")

    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid_lib.uuid4()))
        request_id_ctx.set(request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Health endpoint
    @app.get("/health")
    @app.get("/api/health")
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint"""
        return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}

    return app


app = create_app()
