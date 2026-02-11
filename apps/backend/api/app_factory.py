"""
FastAPI application factory for MedStation.

Minimal medical AI backend: MedGemma inference + Ollama proxy + health check.
"""

import logging
import os
import signal
import uuid as uuid_lib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Dict

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    logger.info("Starting MedStation API...")

    def handle_shutdown(signum, frame):
        sig_name = signal.Signals(signum).name
        logger.warning(f"Received {sig_name} - shutting down")
        os._exit(0)

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    # Register routers
    from api.router_registry import register_routers
    services_loaded, services_failed = register_routers(app)

    if services_loaded:
        logger.info(f"Services: {', '.join(services_loaded)}")
    if services_failed:
        logger.warning(f"Failed: {', '.join(services_failed)}")

    logger.info("MedStation API ready")
    yield
    logger.info("Shutting down MedStation API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application for MedStation."""
    app = FastAPI(
        title="MedStation API",
        description="Privacy-first medical AI backend powered by MedGemma 1.5 4B.",
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

    # CORS — allow localhost origins (local-only app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid_lib.uuid4()))
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
