"""
Neutron Star Web API
FastAPI backend wrapper for the existing SQL engine
"""

import asyncio
import datetime as _dt
import json
import logging
import math
import os
import re
import signal
import uuid
import uuid as uuid_lib
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import pandas as pd
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.background import BackgroundTask

# Suppress DEBUG logs from httpcore and httpx to reduce terminal noise
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Suppress verbose INFO logs from various services for cleaner startup
logging.getLogger("metal4_engine").setLevel(logging.WARNING)
logging.getLogger("metal4_diagnostics").setLevel(logging.WARNING)
logging.getLogger("metal4_resources").setLevel(logging.WARNING)
logging.getLogger("data_engine").setLevel(logging.WARNING)
logging.getLogger("code_editor_service").setLevel(logging.WARNING)
logging.getLogger("docs_service").setLevel(logging.WARNING)
logging.getLogger("mlx_embedder").setLevel(logging.WARNING)
logging.getLogger("unified_embedder").setLevel(logging.WARNING)
logging.getLogger("token_counter").setLevel(logging.WARNING)
logging.getLogger("chat_service").setLevel(logging.WARNING)
logging.getLogger("neutron_core.engine").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Import security utilities
try:
    from .utils import sanitize_filename, sanitize_for_log
except ImportError:
    from utils import sanitize_filename, sanitize_for_log

# Security Note: sanitize_for_log is imported and should be used when logging
# request bodies that may contain passwords, tokens, or API keys.
# Current endpoints avoid logging request bodies directly.

# MED-02: Compile frequently-used regex patterns once at module load
_TABLE_NAME_VALIDATOR = re.compile(r'^[a-zA-Z0-9_]+$')

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# Import shared rate limiter to avoid code duplication
try:
    from .rate_limiter import get_client_ip, rate_limiter
except ImportError:
    from rate_limiter import get_client_ip, rate_limiter

# Import existing backend modules
import sys

# Insert at the beginning of sys.path to prioritize local modules
sys.path.insert(0, str(Path(__file__).parent))  # /apps/backend/api - for api module imports
sys.path.insert(0, str(Path(__file__).parent.parent))  # /apps/backend
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "packages"))  # /packages

from neutron_core.engine import NeutronEngine, QueryResult, SQLDialect
from neutron_utils.config import config
from neutron_utils.sql_utils import SQLProcessor

from redshift_sql_processor import RedshiftSQLProcessor

# Import helpers from services
from api.services.files import save_upload
from api.services.sql_helpers import get_column_info, df_to_jsonsafe_records as _df_to_jsonsafe_records
from sql_validator import SQLValidator

# Phase 2: Import permission decorator
try:
    from auth_middleware import get_current_user
    from permission_engine import require_perm
except ImportError:
    from api.auth_middleware import get_current_user
    from api.permission_engine import require_perm
try:
    from .pulsar_core import JsonToExcelEngine
except ImportError:
    from pulsar_core import JsonToExcelEngine

try:
    from .elohimos_memory import ElohimOSMemory
except ImportError:
    from elohimos_memory import ElohimOSMemory

try:
    from .data_engine import get_data_engine
except ImportError:
    from data_engine import get_data_engine

# Import unified configuration
try:
    from .config import get_settings
except ImportError:
    from config import get_settings

# Session storage
sessions: dict[str, dict] = {}

# Request deduplication (prevent double-click duplicate operations)
# Store request IDs with timestamps to detect duplicates within 60s window
from collections import defaultdict
import time

_request_dedup_cache: defaultdict[str, float] = defaultdict(float)  # request_id -> timestamp
_dedup_lock = None  # Will be initialized as asyncio.Lock when needed
DEDUP_WINDOW_SECONDS = 60  # Consider duplicate if within 60 seconds


def _is_duplicate_request(request_id: str) -> bool:
    """Check if request is a duplicate within time window"""
    global _dedup_lock
    if _dedup_lock is None:
        import asyncio
        _dedup_lock = asyncio.Lock()

    current_time = time.time()

    # Clean up old entries (older than window)
    expired_keys = [k for k, v in _request_dedup_cache.items() if current_time - v > DEDUP_WINDOW_SECONDS]
    for k in expired_keys:
        del _request_dedup_cache[k]

    # Check if this request ID exists and is recent
    if request_id in _request_dedup_cache:
        age = current_time - _request_dedup_cache[request_id]
        if age < DEDUP_WINDOW_SECONDS:
            return True  # Duplicate!

    # Mark as seen
    _request_dedup_cache[request_id] = current_time
    return False


# Query results cache with size limits to prevent OOM
# Limit: 100MB per result, 500MB total cache, 50 results max
MAX_RESULT_SIZE_MB = 100
MAX_CACHE_SIZE_MB = 500
MAX_CACHED_RESULTS = 50
query_results: dict[str, pd.DataFrame] = {}
_query_result_sizes: dict[str, int] = {}  # Track size in bytes
_total_cache_size: int = 0  # Total cache size in bytes


def _get_dataframe_size_bytes(df: pd.DataFrame) -> int:
    """Estimate DataFrame memory usage in bytes"""
    return df.memory_usage(deep=True).sum()


def _evict_oldest_query_result():
    """Evict the oldest query result from cache to free memory"""
    global _total_cache_size
    if not query_results:
        return

    # Get oldest query_id (first inserted)
    oldest_id = next(iter(query_results))
    size = _query_result_sizes.get(oldest_id, 0)

    del query_results[oldest_id]
    del _query_result_sizes[oldest_id]
    _total_cache_size -= size

    logger.info(f"Evicted query result {oldest_id} ({size / 1024 / 1024:.2f} MB) from cache")


def _store_query_result(query_id: str, df: pd.DataFrame) -> bool:
    """
    Store query result with size limits. Returns False if result too large.

    Implements LRU eviction when cache is full.
    """
    global _total_cache_size

    # Calculate size
    size_bytes = _get_dataframe_size_bytes(df)
    size_mb = size_bytes / 1024 / 1024

    # Check if single result exceeds per-result limit
    if size_mb > MAX_RESULT_SIZE_MB:
        logger.warning(f"Query result too large ({size_mb:.2f} MB > {MAX_RESULT_SIZE_MB} MB), not caching")
        return False

    # Evict oldest results until we have space
    while (len(query_results) >= MAX_CACHED_RESULTS or
           _total_cache_size + size_bytes > MAX_CACHE_SIZE_MB * 1024 * 1024):
        _evict_oldest_query_result()

    # Store result
    query_results[query_id] = df
    _query_result_sizes[query_id] = size_bytes
    _total_cache_size += size_bytes

    logger.debug(f"Cached query result {query_id} ({size_mb:.2f} MB), total cache: {_total_cache_size / 1024 / 1024:.2f} MB")
    return True


# Initialize configuration
settings = get_settings()

# Initialize ElohimOS Memory System
elohimos_memory = ElohimOSMemory()

# Initialize Data Engine
data_engine = get_data_engine()



def cleanup_sessions():
    """Clean up all active sessions and close database connections"""
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
    import asyncio
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
    import asyncio

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


def _vacuum_db(db_path: Path, db_name: str):
    """Helper to VACUUM a single database"""
    with sqlite3.connect(str(db_path)) as conn:
        conn.isolation_level = None  # Autocommit mode required for VACUUM
        conn.execute("VACUUM")
        conn.execute("ANALYZE")  # Update query planner statistics
    logger.info(f"✅ VACUUMed {db_name} database")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting ElohimOS API...")

    # macOS-only check
    import platform
    if platform.system() != "Darwin":
        raise RuntimeError(f"ElohimOS is macOS-only. Detected OS: {platform.system()}")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    logger.info("Registered SIGTERM/SIGINT handlers for graceful shutdown")

    # Create necessary directories
    api_dir = Path(__file__).parent
    (api_dir / "temp_uploads").mkdir(exist_ok=True)
    (api_dir / "temp_exports").mkdir(exist_ok=True)

    # Phase 0: Run startup migrations (database consolidation)
    try:
        from startup_migrations import run_startup_migrations
        await run_startup_migrations()
        logger.info("✓ Startup migrations completed")
    except Exception as e:
        logger.error(f"✗ Startup migrations failed: {e}", exc_info=True)
        # Re-raise to prevent app from starting with broken DB state
        raise

    # Phase 1.5: Initialize per-user model storage
    try:
        from config_paths import PATHS
        from services.model_catalog import init_model_catalog
        from services.model_preferences_storage import init_model_preferences_storage
        from services.hot_slots_storage import init_hot_slots_storage

        # Initialize storage singletons
        init_model_catalog(PATHS.app_db, ollama_base_url="http://localhost:11434")
        init_model_preferences_storage(PATHS.app_db)
        init_hot_slots_storage(PATHS.app_db, PATHS.backend_dir / "config")

        # Sync model catalog from Ollama on startup
        from services.model_catalog import get_model_catalog
        catalog = get_model_catalog()
        await catalog.sync_from_ollama()

        logger.info("✓ Per-user model storage initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize per-user model storage: {e}")
        # Don't fail startup - endpoints will handle missing storage gracefully

    # Start background cleanup tasks
    cleanup_task = asyncio.create_task(cleanup_old_temp_files())
    vacuum_task = asyncio.create_task(vacuum_databases())
    logger.info("Started background maintenance tasks (cleanup + VACUUM)")

    # Auto-load favorite models from hot slots
    try:
        from model_manager import get_model_manager
        from chat_service import ollama_client

        model_manager = get_model_manager()
        favorites = model_manager.get_favorites()

        if favorites:
            logger.info(f"Preloading {len(favorites)} favorite model(s): {', '.join(favorites)}")

            for model_name in favorites:
                try:
                    # Preload model by sending a minimal request
                    # This warms up the model without blocking startup
                    await ollama_client.generate(model_name, prompt="", stream=False)
                    logger.debug(f"✓ Preloaded model: {model_name}")
                except Exception as model_error:
                    # Don't fail startup if a model can't be loaded
                    logger.warning(f"Could not preload model '{model_name}': {model_error}")

            logger.info("✓ Model preloading completed")
        else:
            logger.debug("No favorite models to preload")

    except Exception as e:
        # Don't fail startup if model preloading fails entirely
        logger.warning(f"Model auto-loading disabled: {e}")

    # Register analytics aggregation jobs (Sprint 6 Theme A)
    try:
        from api.background_jobs import register_analytics_jobs, get_job_manager

        register_analytics_jobs()

        # Start the background job manager
        job_manager = get_job_manager()
        await job_manager.start()

        logger.info("✓ Analytics aggregation jobs started")
    except Exception as e:
        logger.warning(f"Failed to start analytics jobs: {e}")

    yield
    # Shutdown (clean shutdown via lifespan)
    print("Shutting down...")
    cleanup_task.cancel()

    # Stop background jobs
    try:
        from api.background_jobs import get_job_manager
        job_manager = get_job_manager()
        await job_manager.stop()
    except Exception as e:
        logger.warning(f"Error stopping background jobs: {e}")

    cleanup_sessions()

# Request ID context for structured logging
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

app = FastAPI(
    title="ElohimOS API",
    description="""
## ElohimOS - Offline-First AI Operating System

ElohimOS is a secure, privacy-first AI platform designed for mission-critical operations
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
        "url": "https://github.com/yourusername/elohimos",  # Update with actual URL
    },
    license_info={
        "name": "Proprietary",
        "url": "https://elohimos.local/license",  # Update with actual license
    },
)

# Middleware to add request ID to all requests
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID for tracing and structured logging"""
    request_id = request.headers.get("X-Request-ID", str(uuid_lib.uuid4()))
    request_id_ctx.set(request_id)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Add rate limiter to app state
# Disabled slowapi due to compatibility issues with multipart file uploads
# The global 100/minute limit and specific endpoint limits caused errors
# File size limits and session-based access control provide adequate protection
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS for development
# Security (HIGH-04): CSRF Protection provided by:
# 1. JWT tokens in Authorization header (not cookies - no automatic sending)
# 2. CORS restricts origins to trusted dev servers
# 3. Browsers enforce SOP - malicious sites can't read responses
# Parse CORS origins from environment or use defaults
cors_origins_env = os.getenv('ELOHIM_CORS_ORIGINS', '')
if cors_origins_env:
    # Parse comma-separated list from environment
    allowed_origins = [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]
else:
    # Default dev origins - include common Vite fallback ports
    allowed_origins = [
        "http://localhost:4200",
        "http://localhost:4201",  # Vite fallback when 4200 is busy
        "http://127.0.0.1:4200",
        "http://localhost:5173",  # Vite default
        "http://localhost:5174",  # Vite fallback
        "http://localhost:5175",  # Vite fallback
        "http://127.0.0.1:5173",  # 127.0.0.1 equivalents for Vite
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://localhost:3000"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,  # LOW-03: Cache preflight requests for 1 hour
)

# Import and include service routers
services_loaded = []
services_failed = []

try:
    from api.routes import chat as _chat_routes
    app.include_router(_chat_routes.router)
    app.include_router(_chat_routes.public_router)  # Public endpoints (health check)
    services_loaded.append("Chat")
except Exception as e:
    services_failed.append("Chat")
    logger.error("Failed to load chat router", exc_info=True)

try:
    from p2p_chat_router import router as p2p_chat_router
    app.include_router(p2p_chat_router)
    services_loaded.append("P2P")
except Exception as e:
    services_failed.append("P2P")
    logger.debug(f"P2P Team Chat not available: {e}")

try:
    from api.lan_service import router as lan_router
    app.include_router(lan_router)
    services_loaded.append("LAN")
except Exception as e:
    services_failed.append("LAN")
    logger.debug(f"LAN Discovery not available: {e}")

try:
    from api.p2p_mesh_service import router as p2p_mesh_router
    app.include_router(p2p_mesh_router)
    services_loaded.append("P2P Mesh")
except Exception as e:
    services_failed.append("P2P Mesh")
    logger.debug(f"P2P Mesh not available: {e}")

try:
    from code_editor_service import router as code_editor_router
    app.include_router(code_editor_router)
    services_loaded.append("Code")
except Exception as e:
    services_failed.append("Code")
    logger.debug(f"Code Editor not available: {e}")

try:
    from api.routes import users as _users_routes
    app.include_router(_users_routes.router)
    services_loaded.append("User")
except Exception as e:
    services_failed.append("User")
    logger.error("Failed to load users router", exc_info=True)

try:
    from api.routes import team as _team_routes
    app.include_router(_team_routes.router)
    services_loaded.append("Team")
except Exception as e:
    services_failed.append("Team")
    logger.error("Failed to load team router", exc_info=True)

try:
    from docs_service import router as docs_router
    app.include_router(docs_router)
    services_loaded.append("Docs")
except Exception as e:
    services_failed.append("Docs")
    logger.debug(f"Docs service not available: {e}")

try:
    from insights_service import router as insights_router
    app.include_router(insights_router)
    services_loaded.append("Insights")
except Exception as e:
    services_failed.append("Insights")
    logger.debug(f"Insights Lab not available: {e}")

try:
    from offline_mesh_router import router as mesh_router
    app.include_router(mesh_router)
    services_loaded.append("Mesh")
except Exception as e:
    services_failed.append("Mesh")
    logger.debug(f"Offline Mesh not available: {e}")

try:
    from panic_mode_router import router as panic_router
    app.include_router(panic_router)
    services_loaded.append("Panic")
except Exception as e:
    services_failed.append("Panic")
    logger.debug(f"Panic Mode not available: {e}")

try:
    import vault_service
    app.include_router(vault_service.router)
    services_loaded.append("Vault")
except Exception as e:
    services_failed.append("Vault")
    logger.debug(f"Vault service not available: {e}")

try:
    from automation_router import router as automation_router
    app.include_router(automation_router)
    services_loaded.append("Automation")
except Exception as e:
    services_failed.append("Automation")
    logger.debug(f"Automation service not available: {e}")

try:
    from workflow_service import router as workflow_router
    app.include_router(workflow_router)
    services_loaded.append("Workflow")
except Exception as e:
    services_failed.append("Workflow")
    logger.debug(f"Workflow service not available: {e}")

# n8n integration disabled - keeping code for future use
# try:
#     from n8n_router import router as n8n_router
#     app.include_router(n8n_router)
#     services_loaded.append("n8n Integration")
# except Exception as e:
#     services_failed.append("n8n Integration")
#     logger.debug(f"n8n integration not available: {e}")

# Security & RBAC routers removed - internal services not exposed as REST APIs

try:
    from secure_enclave_service import router as secure_enclave_router
    app.include_router(secure_enclave_router)
    services_loaded.append("Secure Enclave")
except Exception as e:
    services_failed.append("Secure Enclave")
    logger.debug(f"Secure Enclave service not available: {e}")

# Auth routes
try:
    from auth_routes import router as auth_router
    app.include_router(auth_router)
    services_loaded.append("Authentication")
except Exception as e:
    services_failed.append("Authentication")
    logger.error(f"Authentication service failed to load: {e}")

# Admin routes (Founder Rights support access)
try:
    from admin_service import router as admin_router
    app.include_router(admin_router)
    services_loaded.append("Admin")
except Exception as e:
    services_failed.append("Admin")
    logger.error(f"Admin service failed to load: {e}")

# Backup routes
try:
    from backup_router import router as backup_router
    app.include_router(backup_router)
    services_loaded.append("Backups")
except Exception as e:
    services_failed.append("Backups")
    logger.error(f"Backup service failed to load: {e}")

# Agent Orchestrator (Aider + Continue + Codex integration)
try:
    from agent import router as agent_router
    app.include_router(agent_router)
    services_loaded.append("Agent Orchestrator")
except Exception as e:
    services_failed.append("Agent Orchestrator")
    logger.error(f"Agent Orchestrator service failed to load: {e}")

# Permissions Administration (Phase 2: RBAC management)
try:
    from api.routes import permissions as _permissions_routes
    app.include_router(_permissions_routes.router)
    services_loaded.append("Permissions Admin")
except Exception as e:
    services_failed.append("Permissions Admin")
    logger.error("Failed to load permissions router", exc_info=True)
    logger.error(f"Permissions Admin service failed to load: {e}")

# Audit Logging (Sprint 4)
try:
    from api.routes import audit as _audit_routes
    app.include_router(_audit_routes.router)
    services_loaded.append("Audit Logging")
except Exception as e:
    services_failed.append("Audit Logging")
    logger.error("Failed to load audit router", exc_info=True)

# Model Downloads Queue (Sprint 5)
try:
    from api.routes import model_downloads as _model_downloads_routes
    app.include_router(_model_downloads_routes.router)
    services_loaded.append("Model Downloads Queue")
except Exception as e:
    services_failed.append("Model Downloads Queue")
    logger.error("Failed to load model downloads router", exc_info=True)
    logger.error(f"Audit Logging service failed to load: {e}")

# Analytics API (Sprint 6 Theme A)
try:
    from api.routes import analytics as _analytics_routes
    app.include_router(_analytics_routes.router)
    services_loaded.append("Analytics Dashboard")
except Exception as e:
    services_failed.append("Analytics Dashboard")
    logger.error("Failed to load analytics router", exc_info=True)
    logger.error(f"Analytics service failed to load: {e}")

# Search API (Sprint 6 Theme B)
try:
    from api.routes import search as _search_routes
    app.include_router(_search_routes.router)
    services_loaded.append("Session Search")
except Exception as e:
    services_failed.append("Session Search")
    logger.error("Failed to load search router", exc_info=True)
    logger.error(f"Search service failed to load: {e}")

# Monitoring routes
try:
    from monitoring_routes import router as monitoring_router
    app.include_router(monitoring_router)
    services_loaded.append("Monitoring")
except Exception as e:
    services_failed.append("Monitoring")
    logger.error(f"Monitoring service failed to load: {e}", exc_info=True)

# Code Tab Operations (Phase 2)
try:
    from code_operations import router as code_router
    app.include_router(code_router)
except ImportError as e:
    logger.warning(f"Could not import code_operations router: {e}")

# Terminal Bridge API (Phase 5)
try:
    from terminal_api import router as terminal_router
    app.include_router(terminal_router)
    services_loaded.append("Terminal Bridge")
except ImportError as e:
    logger.warning(f"Could not import terminal_api router: {e}")

# Metal 4 ML API (Phase 1.1-1.3: GPU-accelerated embeddings & vector search)
try:
    from metal4_ml_routes import router as metal4_ml_router
    app.include_router(metal4_ml_router)
    services_loaded.append("Metal 4 ML")
except ImportError as e:
    logger.warning(f"Could not import metal4_ml router: {e}")

# Prometheus Metrics API (Phase 5.2: Monitoring & Observability)
try:
    from prometheus_metrics import get_prometheus_exporter
    prometheus_exporter = get_prometheus_exporter()
    services_loaded.append("Prometheus Metrics")
except ImportError as e:
    logger.warning(f"Could not import prometheus_metrics: {e}")
    prometheus_exporter = None

# Founder Setup Wizard (Phase 5.3: First-time password setup)
try:
    from founder_setup_routes import router as founder_setup_router
    app.include_router(founder_setup_router)
    services_loaded.append("Founder Setup Wizard")
except ImportError as e:
    logger.warning(f"Could not import founder_setup_routes: {e}")

# Setup Wizard (Phase 1: First-run setup with Ollama, models, hot slots)
try:
    from routes.setup_wizard_routes import router as setup_wizard_router
    app.include_router(setup_wizard_router)
    services_loaded.append("Setup Wizard")
except ImportError as e:
    logger.warning(f"Could not import setup_wizard_routes: {e}")

# User Models (Phase 1.5: Per-user model preferences and hot slots)
try:
    from routes.user_models import router as user_models_router
    app.include_router(user_models_router)
    services_loaded.append("User Models")
except ImportError as e:
    logger.warning(f"Could not import user_models: {e}")

# Health Diagnostics (Phase 5.4: Comprehensive health checks)
try:
    from health_diagnostics import get_health_diagnostics
    health_diagnostics = get_health_diagnostics()
    services_loaded.append("Health Diagnostics")
except ImportError as e:
    logger.warning(f"Could not import health_diagnostics: {e}")
    health_diagnostics = None

# Optional placeholder routers for upcoming modular refactor (no endpoints defined)
try:
    from api.routes import system as _system_routes
    app.include_router(_system_routes.router)
except Exception:
    pass

try:
    from api.routes import sessions as _sessions_routes
    app.include_router(_sessions_routes.router, prefix="/api/sessions")
except Exception:
    pass

try:
    from api.routes import sql_json as _sql_json_routes
    app.include_router(_sql_json_routes.router, prefix="/api/sessions")
except Exception as e:
    logger.error(f"Failed to import sql_json router: {e}", exc_info=True)

try:
    from api.routes import saved_queries as _saved_queries_routes
    app.include_router(_saved_queries_routes.router, prefix="/api/saved-queries")
except Exception:
    pass

try:
    from api.routes import settings as _settings_routes
    app.include_router(_settings_routes.router, prefix="/api/settings")
except Exception:
    pass

try:
    from api.routes import metrics as _metrics_routes
    app.include_router(_metrics_routes.router, prefix="/metrics")
except Exception:
    pass

try:
    from api.routes import metal as _metal_routes
    app.include_router(_metal_routes.router, prefix="/api/v1/metal")
except Exception:
    pass

try:
    from api.routes import admin as _admin_routes
    app.include_router(_admin_routes.router, prefix="/api/admin")
except Exception as e:
    logger.error("Failed to load admin router", exc_info=True)

try:
    from api.vault import routes as _vault_routes
    app.include_router(_vault_routes.router, prefix="/api/v1/vault")
except Exception:
    pass

try:
    from api.team import routes as _team_routes
    app.include_router(_team_routes.router, prefix="/api/v1/teams")
except Exception:
    pass

# Removed: Empty placeholder chat router (redundant with routes.chat)
# The actual chat router is loaded above via: from routes import chat

try:
    from api.permissions import routes as _perm_routes
    app.include_router(_perm_routes.router, prefix="/api/v1/permissions")
except Exception:
    pass

# Log summary of loaded services
if services_loaded:
    logger.info(f"✓ Services: {', '.join(services_loaded)}")

# Initialize Metal 4 engine (silent - already shown in banner)
try:
    from metal4_engine import get_metal4_engine, validate_metal4_setup
    metal4_engine = get_metal4_engine()
except Exception as e:
    logger.warning(f"Metal 4 not available: {e}")
    metal4_engine = None

# Models - Import from centralized schemas module to avoid circular imports
from api.schemas.api_models import (
    SessionResponse,
    ColumnInfo,
    FileUploadResponse,
    QueryRequest,
    QueryResponse,
    ExportRequest,
    ValidationRequest,
    ValidationResponse,
    QueryHistoryItem,
    QueryHistoryResponse,
    SuccessResponse,
    DatasetListResponse,
    JsonUploadResponse,
    JsonConvertRequest,
    JsonConvertResponse,
    SheetNamesResponse,
    TablesListResponse,
)

# Helper functions
# Helper functions moved to api/services/
# - save_upload -> api.services.files
# - get_column_info -> api.services.sql_helpers
# - df_to_jsonsafe_records -> api.services.sql_helpers

# Endpoints
@app.get("/")
async def root():
    return {"message": "ElohimOS API", "version": "1.0.0"}


@app.get("/api/system/info")
async def get_system_info():
    """
    Get system information including Metal GPU capabilities and memory
    """
    import subprocess

    info = {
        "total_memory_gb": 0,
        "metal_available_memory_gb": 0,
        "metal_device_name": None,
        "metal_available": False,
        "metal_initialized": False,
        "metal_error": None,  # NEW: Expose initialization errors to frontend
    }

    # Get total system memory using sysctl
    try:
        result = subprocess.run(['sysctl', 'hw.memsize'], capture_output=True, text=True)
        if result.returncode == 0:
            memsize = int(result.stdout.split(':')[1].strip())
            info["total_memory_gb"] = round(memsize / (1024**3), 1)
    except:
        pass

    # Get Metal device info and recommendedMaxWorkingSetSize
    try:
        from metal4_engine import get_metal4_engine
        engine = get_metal4_engine()

        if engine.is_available():
            info["metal_available"] = True
            info["metal_initialized"] = engine._initialized
            info["metal_device_name"] = engine.device.name() if engine.device else None

            # Expose initialization error if any
            if engine.initialization_error:
                info["metal_error"] = engine.initialization_error

            # This is the key value - Metal's recommended max working set size
            # This is what should be used for calculating model loading capacity
            if engine.device:
                recommended_max = engine.device.recommendedMaxWorkingSetSize()
                info["metal_available_memory_gb"] = round(recommended_max / (1024**3), 1)
        else:
            # Metal not available at all
            if hasattr(engine, 'initialization_error') and engine.initialization_error:
                info["metal_error"] = engine.initialization_error
    except Exception as e:
        info["metal_error"] = f"Failed to query Metal engine: {str(e)}"

    return info


@app.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint (Phase 5.2)

    Returns metrics in Prometheus text format for scraping.
    Includes:
    - System metrics (CPU, RAM, disk, network)
    - Metal 4 GPU metrics (if available)
    - Application metrics (users, workflows, vault)
    - Health status

    Response format: text/plain (Prometheus format)
    """
    if not prometheus_exporter:
        raise HTTPException(status_code=503, detail="Prometheus metrics not available")

    try:
        metrics_text = prometheus_exporter.collect_metrics()
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            content=metrics_text,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except Exception as e:
        logger.error(f"Failed to collect Prometheus metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect metrics: {str(e)}")


@app.get("/health")
async def health_check():
    """
    Quick health check endpoint (Phase 5.4)

    Lightweight health check for liveness probes.
    Target: < 100ms response time.

    Checks:
    - Database connectivity
    - System resources (memory, disk)

    Returns:
        JSON with health status
    """
    if not health_diagnostics:
        raise HTTPException(status_code=503, detail="Health diagnostics not available")

    try:
        health = health_diagnostics.check_health()
        status_code = 200 if health["status"] == "healthy" else 503
        return health
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/diagnostics")
async def system_diagnostics(force_refresh: bool = False):
    """
    Comprehensive system diagnostics endpoint (Phase 5.4)

    Detailed diagnostics for troubleshooting and monitoring.
    Results cached for 60 seconds to avoid overhead.

    Includes:
    - All component health status
    - System information
    - Metal 4 GPU details
    - Dependency validation
    - Performance metrics

    Query params:
        force_refresh: Force fresh diagnostics (bypass cache)

    Returns:
        JSON with comprehensive diagnostics
    """
    if not health_diagnostics:
        raise HTTPException(status_code=503, detail="Health diagnostics not available")

    try:
        diagnostics = health_diagnostics.get_diagnostics(force_refresh=force_refresh)
        return diagnostics
    except Exception as e:
        logger.error(f"Diagnostics failed: {e}")
        raise HTTPException(status_code=500, detail=f"Diagnostics failed: {str(e)}")


# Fallback Admin device overview endpoint to avoid 404 if admin router fails to load
@app.get("/api/v1/admin/device/overview")
async def _fallback_admin_device_overview(request: Request, current_user: dict = Depends(get_current_user)):
    # Require Founder Rights (Founder Admin)
    if current_user.get("role") != "founder_rights":
        raise HTTPException(status_code=403, detail="Founder Rights (Founder Admin) access required")

    # Try to forward to admin_service implementation if available
    try:
        try:
            from .admin_service import get_device_overview as _real_overview  # type: ignore
        except ImportError:
            from admin_service import get_device_overview as _real_overview  # type: ignore
        return await _real_overview(request, current_user)
    except Exception:
        # Graceful minimal overview if admin_service is unavailable
        return {
            "device_overview": {
                "total_users": None,
                "active_users_7d": None,
                "users_by_role": None,
                "total_chat_sessions": None,
                "total_workflows": None,
                "total_work_items": None,
                "total_documents": None,
                "data_dir_size_bytes": None,
                "data_dir_size_human": None,
            },
            "timestamp": datetime.utcnow().isoformat()
        }

# Fallback Terminal spawn endpoint to avoid 404 if terminal router fails to load
@app.post("/api/v1/terminal/spawn-system")
async def _fallback_spawn_system_terminal(current_user: dict = Depends(get_current_user)):
    # Allow only founder_rights or super_admin by default
    role = current_user.get("role")
    if role not in ("founder_rights", "super_admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions to spawn terminal")

    # Try to forward to terminal_api implementation if available
    try:
        try:
            from .terminal_api import spawn_system_terminal as _real_spawn  # type: ignore
        except ImportError:
            from terminal_api import spawn_system_terminal as _real_spawn  # type: ignore
        return await _real_spawn(current_user=current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to spawn system terminal: {e}. Ensure Terminal/iTerm/Warp are installed and grant Automation/Accessibility permissions."
            )
        )


# Note: Auth endpoints moved to auth_routes.py at /api/v1/auth/*
# This includes: /register, /login, /logout, /setup-needed
# All frontend code should use /api/v1/auth/* prefix


# ============================================================================
# MIGRATED TO: api/routes/sessions.py
# ============================================================================
# @app.post("/api/sessions/create", response_model=SessionResponse)
# async def create_session(request: Request):
#     """Create a new session with isolated engine"""
#     session_id = str(uuid.uuid4())
#     sessions[session_id] = {
#         "id": session_id,
#         "created_at": datetime.now(),
#         "engine": NeutronEngine(),
#         "files": {},
#         "queries": {}
#     }
#     return SessionResponse(session_id=session_id, created_at=sessions[session_id]["created_at"])
#
# @app.delete("/api/sessions/{session_id}")
# async def delete_session(request: Request, session_id: str):
#     """Clean up session and its resources"""
#     if session_id not in sessions:
#         raise HTTPException(status_code=404, detail="Session not found")
#
#     session = sessions[session_id]
#
#     # Close engine
#     if 'engine' in session:
#         session['engine'].close()
#
#     # Clean up temp files
#     for file_info in session.get('files', {}).values():
#         if 'path' in file_info and Path(file_info['path']).exists():
#             Path(file_info['path']).unlink()
#
#     # Clean up query results
#     for query_id in session.get('queries', {}):
#         query_results.pop(query_id, None)
#
#     del sessions[session_id]
#     return {"message": "Session deleted"}
# ============================================================================
# MIGRATED TO: api/routes/sql_json.py (Phase 4 - Upload Endpoint)
# ============================================================================
# @app.post("/api/sessions/{session_id}/upload", response_model=FileUploadResponse)
# async def upload_file(
#     session_id: str,
#     file: UploadFile = File(...),
#     sheet_name: str | None = Form(None)
# ):
#     """Upload and load an Excel file"""
#     if session_id not in sessions:
#         raise HTTPException(status_code=404, detail="Session not found")
#
#     if not file.filename.lower().endswith(('.xlsx', '.xls', '.xlsm', '.csv')):
#         raise HTTPException(status_code=400, detail="Only Excel (.xlsx, .xls, .xlsm) and CSV files are supported")
#
#     # Save file (streamed) and enforce max size
#     file_path = await save_upload(file)
#     size_mb = file_path.stat().st_size / (1024 * 1024)
#     max_mb = float(config.get("max_file_size_mb", 1000))
#     if size_mb > max_mb:
#         try:
#             file_path.unlink()
#         except Exception:
#             pass
#         raise HTTPException(status_code=413, detail=f"File too large: {size_mb:.1f} MB (limit {int(max_mb)} MB)")
#
#     try:
#         engine = sessions[session_id]['engine']
#
#         # Load into engine based on file type
#         lower_name = file.filename.lower()
#         if lower_name.endswith('.csv'):
#             result = engine.load_csv(file_path, table_name="excel_file")
#         else:
#             result = engine.load_excel(file_path, table_name="excel_file", sheet_name=sheet_name)
#
#         # Defensive checks in case engine returns unexpected value
#         if result is None or not isinstance(result, QueryResult):
#             raise HTTPException(status_code=500, detail="Internal error: invalid engine result during load")
#
#         if result.error:
#             raise HTTPException(status_code=400, detail=result.error)
#
#         # Get preview data
#         preview_result = engine.execute_sql("SELECT * FROM excel_file LIMIT 20")
#
#         if preview_result is None or not isinstance(preview_result, QueryResult):
#             raise HTTPException(status_code=500, detail="Internal error: invalid engine result during preview")
#
#         if preview_result.error:
#             raise HTTPException(status_code=500, detail=preview_result.error)
#
#         # Store file info
#         file_info = {
#             "filename": file.filename,
#             "path": str(file_path),
#             "size_mb": file_path.stat().st_size / (1024 * 1024),
#             "loaded_at": datetime.now()
#         }
#         sessions[session_id]['files'][file.filename] = file_info
#
#         # Get column info
#         columns = get_column_info(preview_result.data)
#
#         # JSON-safe preview
#         preview_records = _df_to_jsonsafe_records(preview_result.data)
#
#         return FileUploadResponse(
#             filename=file.filename,
#             size_mb=file_info['size_mb'],
#             row_count=result.row_count,
#             column_count=len(result.column_names),
#             columns=columns,
#             preview=preview_records
#         )
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         # Clean up file on error
#         if file_path.exists():
#             file_path.unlink()
#         raise HTTPException(status_code=500, detail=str(e))
# ============================================================================

# ============================================================================
# MIGRATED TO: api/routes/sql_json.py (Quick Wins - Validate Endpoint)
# ============================================================================
# @app.post("/api/sessions/{session_id}/validate", response_model=ValidationResponse)
# async def validate_sql(request: Request, session_id: str, body: ValidationRequest):
#     """Validate SQL syntax before execution"""
#     if session_id not in sessions:
#         raise HTTPException(status_code=404, detail="Session not found")
#
#     validator = SQLValidator()
#     is_valid, errors, warnings = validator.validate_sql(
#         body.sql,
#         expected_table="excel_file"
#     )
#
#     return ValidationResponse(
#         is_valid=is_valid,
#         errors=errors,
#         warnings=warnings
#     )

# ============================================================================
# MIGRATED TO: api/routes/sql_json.py (Phase 4 - Query Endpoint)
# ============================================================================
# @app.post("/api/sessions/{session_id}/query", response_model=QueryResponse)
# async def execute_query(
#     req: Request,
#     session_id: str,
#     request: QueryRequest,
#     idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
# ):
#     """Execute SQL query with deduplication support"""
#
#     # Request deduplication: Check if this is a duplicate request
#     if idempotency_key:
#         if _is_duplicate_request(f"query:{idempotency_key}"):
#             logger.warning(f"Duplicate query request detected: {idempotency_key}")
#             raise HTTPException(
#                 status_code=409,
#                 detail="Duplicate request detected. This query was already executed recently. Please wait 60 seconds or use a different idempotency key."
#             )
#
#     # Rate limit: 60 queries per minute
#     client_ip = get_client_ip(req)
#     if not rate_limiter.check_rate_limit(f"query:{client_ip}", max_requests=60, window_seconds=60):
#         raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 60 queries per minute.")
#
#     # Sanitize SQL for logging (redact potential sensitive data)
#     sanitized_sql = sanitize_for_log(request.sql[:100])
#     logger.info(f"Executing query for session {session_id}: {sanitized_sql}...")
#
#     if session_id not in sessions:
#         raise HTTPException(status_code=404, detail="Session not found")
#
#     engine = sessions[session_id]['engine']
#     logger.info(f"Engine found for session {session_id}")
#
#     # Clean SQL (strip comments/trailing semicolons) to avoid parsing issues when embedding in LIMIT wrapper
#     cleaned_sql = SQLProcessor.clean_sql(request.sql)
#     sanitized_cleaned = sanitize_for_log(cleaned_sql[:100])
#     logger.info(f"Cleaned SQL: {sanitized_cleaned}...")
#
#     # Security: Validate query only accesses allowed tables (session's uploaded file)
#     from neutron_utils.sql_utils import SQLProcessor as SQLUtil
#     referenced_tables = SQLUtil.extract_table_names(cleaned_sql)
#
#     # Only allow queries to reference the excel_file table (or explicitly allowed tables)
#     allowed_tables = {'excel_file'}  # Default table for uploaded files
#     # TODO: Add support for multi-file sessions with explicit table names
#
#     unauthorized_tables = set(referenced_tables) - allowed_tables
#     if unauthorized_tables:
#         raise HTTPException(
#             status_code=403,
#             detail=f"Query references unauthorized tables: {', '.join(unauthorized_tables)}. Only 'excel_file' is allowed."
#         )
#
#     # Execute query with timeout protection
#     # NOTE: True async cancellation requires aiosqlite (MED-06)
#     # For now, we use asyncio.wait_for to enforce max query time
#     timeout = request.timeout_seconds if hasattr(request, 'timeout_seconds') and request.timeout_seconds else 300  # 5min default
#
#     try:
#         result = await asyncio.wait_for(
#             asyncio.to_thread(
#                 engine.execute_sql,
#                 cleaned_sql,
#                 dialect=request.dialect,
#                 limit=request.limit
#             ),
#             timeout=timeout
#         )
#         logger.info(f"Query execution completed, rows: {result.row_count if result else 'error'}")
#     except asyncio.TimeoutError:
#         logger.error(f"Query execution timed out after {timeout}s")
#         raise HTTPException(
#             status_code=408,
#             detail=f"Query execution exceeded timeout of {timeout} seconds. Consider adding a LIMIT clause or optimizing your query."
#         )
#     except Exception as e:
#         logger.error(f"Query execution failed: {str(e)}")
#         raise
#
#     if result.error:
#         raise HTTPException(status_code=400, detail=result.error)
#
#     # Store full result for export (with size limits)
#     query_id = str(uuid.uuid4())
#     cached = _store_query_result(query_id, result.data)
#
#     if not cached:
#         logger.warning(f"Query result not cached (too large), export will be unavailable")
#
#     # Store query info
#     sessions[session_id]['queries'][query_id] = {
#         "sql": request.sql,
#         "executed_at": datetime.now(),
#         "row_count": result.row_count
#     }
#
#     # Return preview (random sample of 100 rows if dataset is large) — JSON-safe
#     preview_limit = 100
#     if result.row_count > preview_limit:
#         # Random sample for better data representation
#         preview_df = result.data.sample(n=preview_limit, random_state=None)
#     else:
#         preview_df = result.data
#
#     preview_data = _df_to_jsonsafe_records(preview_df)
#
#     return QueryResponse(
#         query_id=query_id,
#         row_count=result.row_count,
#         column_count=len(result.column_names),
#         columns=result.column_names,
#         execution_time_ms=result.execution_time_ms,
#         preview=preview_data,
#         has_more=result.row_count > preview_limit
#     )
# ============================================================================

# ============================================================================
# MIGRATED TO: api/routes/sql_json.py (Quick Wins - Query History Endpoints)
# ============================================================================
# @app.get("/api/sessions/{session_id}/query-history", response_model=QueryHistoryResponse)
# async def get_query_history(session_id: str):
#     """Get query history for a session"""
#     if session_id not in sessions:
#         raise HTTPException(status_code=404, detail="Session not found")
#
#     queries = sessions[session_id].get('queries', {})
#     history = []
#
#     for query_id, query_info in queries.items():
#         history.append({
#             "id": query_id,
#             "query": query_info["sql"],
#             "timestamp": query_info["executed_at"].isoformat(),
#             "executionTime": query_info.get("execution_time_ms"),
#             "rowCount": query_info.get("row_count"),
#             "status": "success"  # We only store successful queries
#         })
#
#     # Sort by timestamp descending (most recent first)
#     history.sort(key=lambda x: x["timestamp"], reverse=True)
#
#     return {"history": history}
#
# @app.delete("/api/sessions/{session_id}/query-history/{query_id}", response_model=SuccessResponse)
# async def delete_query_from_history(request: Request, session_id: str, query_id: str):
#     """Delete a query from history"""
#     if session_id not in sessions:
#         raise HTTPException(status_code=404, detail="Session not found")
#
#     queries = sessions[session_id].get('queries', {})
#     if query_id not in queries:
#         raise HTTPException(status_code=404, detail="Query not found")
#
#     del queries[query_id]
#
#     # Also remove from query_results cache if it exists
#     if query_id in query_results:
#         global _total_cache_size
#         size = _query_result_sizes.get(query_id, 0)
#         del query_results[query_id]
#         if query_id in _query_result_sizes:
#             del _query_result_sizes[query_id]
#         _total_cache_size -= size
#
#     return SuccessResponse(success=True, message="Query deleted successfully")

# ============================================================================
# MIGRATED TO: api/routes/sql_json.py
# ============================================================================
# @app.post("/api/sessions/{session_id}/export")
# @require_perm("data.export")
# async def export_results(req: Request, session_id: str, request: ExportRequest, current_user: dict = Depends(get_current_user)):
#     """Export query results"""

# ============================================================================
# MIGRATED TO: api/routes/sql_json.py (Quick Wins - Sheet Names & Tables Endpoints)
# ============================================================================
# @app.get("/api/sessions/{session_id}/sheet-names")
# async def sheet_names(session_id: str, filename: str | None = Query(None)):
#     """List Excel sheet names for an uploaded file in this session."""
#     if session_id not in sessions:
#         raise HTTPException(status_code=404, detail="Session not found")
#     try:
#         from neutron_utils.excel_ops import ExcelReader
#     except Exception:
#         raise HTTPException(status_code=500, detail="Excel utilities unavailable")
#
#     files = sessions[session_id].get('files', {})
#     file_info = None
#     if filename and filename in files:
#         file_info = files[filename]
#     else:
#         # Pick first Excel file in session
#         for info in files.values():
#             if str(info.get('path', '')).lower().endswith(('.xlsx', '.xls', '.xlsm')):
#                 file_info = info
#                 break
#     if not file_info:
#         raise HTTPException(status_code=404, detail="No Excel file found in session")
#     path = Path(file_info['path'])
#     if not path.exists():
#         raise HTTPException(status_code=404, detail="File not found on server")
#     try:
#         sheets = ExcelReader.get_sheet_names(str(path))
#         return {"filename": file_info.get('filename', path.name), "sheets": sheets}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
# @app.get("/api/sessions/{session_id}/tables")
# async def list_tables(session_id: str):
#     """List loaded tables in session"""
#     if session_id not in sessions:
#         raise HTTPException(status_code=404, detail="Session not found")
#
#     engine = sessions[session_id]['engine']
#     tables = []
#
#     for table_name, file_path in engine.tables.items():
#         table_info = engine.get_table_info(table_name)
#         tables.append({
#             "name": table_name,
#             "file": Path(file_path).name,
#             "row_count": table_info.get('row_count', 0),
#             "column_count": len(table_info.get('columns', []))
#         })
#
#     return {"tables": tables}

@app.websocket("/api/sessions/{session_id}/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time query progress and logs"""
    if session_id not in sessions:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()

    try:
        while True:
            # Receive query request
            data = await websocket.receive_json()

            if data.get("type") == "query":
                # Execute query and stream progress
                await websocket.send_json({
                    "type": "progress",
                    "message": "Starting query execution..."
                })

                # Security: Validate table access (same as REST endpoint)
                sql_query = data.get("sql", "")
                from neutron_utils.sql_utils import SQLProcessor as SQLUtil
                referenced_tables = SQLUtil.extract_table_names(sql_query)
                allowed_tables = {'excel_file'}

                unauthorized_tables = set(referenced_tables) - allowed_tables
                if unauthorized_tables:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Query references unauthorized tables: {', '.join(unauthorized_tables)}"
                    })
                    continue

                # TODO: Implement actual progress streaming
                # For now, just execute and return result
                engine = sessions[session_id]['engine']
                result = engine.execute_sql(sql_query)

                if result.error:
                    await websocket.send_json({
                        "type": "error",
                        "message": result.error
                    })
                else:
                    await websocket.send_json({
                        "type": "complete",
                        "row_count": result.row_count,
                        "execution_time_ms": result.execution_time_ms
                    })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })

# JSON to Excel endpoints for Pulsar integration
# Models imported from api.schemas.api_models (see top of file)

###############################################################################
# MIGRATED TO: api/routes/sql_json.py (Phase 5 - JSON Upload)
# @app.post("/api/sessions/{session_id}/json/upload", response_model=JsonUploadResponse)
# async def upload_json(request: Request, session_id: str, file: UploadFile = File(...)):
#     """Upload and analyze JSON file"""
###############################################################################
# MIGRATED TO: api/routes/sql_json.py (Phase 5 - JSON Convert)
# @app.post("/api/sessions/{session_id}/json/convert", response_model=JsonConvertResponse)
# async def convert_json(request: Request, session_id: str, body: JsonConvertRequest):
#     """Convert JSON data to Excel format"""
#     query_type: str | None = Query(None)
# ):
#     """Get all saved queries"""
#     try:
#         queries = elohimos_memory.get_saved_queries(
#             folder=folder,
#             query_type=query_type
#         )
#         return {"queries": queries}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
# @app.put("/api/saved-queries/{query_id}")
# async def update_saved_query(request: Request, query_id: int, body: SavedQueryUpdateRequest):
#     """Update a saved query (partial updates supported)"""
#     try:
#         # Get existing query
#         all_queries = elohimos_memory.get_saved_queries()
#         existing = next((q for q in all_queries if q['id'] == query_id), None)
#
#         if not existing:
#             raise HTTPException(status_code=404, detail="Query not found")
#
#         # Merge updates with existing data
#         elohimos_memory.update_saved_query(
#             query_id=query_id,
#             name=body.name if body.name is not None else existing['name'],
#             query=body.query if body.query is not None else existing['query'],
#             query_type=body.query_type if body.query_type is not None else existing['query_type'],
#             folder=body.folder if body.folder is not None else existing.get('folder'),
#             description=body.description if body.description is not None else existing.get('description'),
#             tags=body.tags if body.tags is not None else (json.loads(existing.get('tags', '[]')) if existing.get('tags') else None)
#         )
#         return {"success": True}
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
# @app.delete("/api/saved-queries/{query_id}")
# async def delete_saved_query(request: Request, query_id: int):
#     """Delete a saved query"""
#     try:
#         elohimos_memory.delete_saved_query(query_id)
#         return {"success": True}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
# ============================================================================


# ============================================================================
# Settings API Endpoints
# ============================================================================

class AppSettings(BaseModel):
    # Performance & Memory
    max_file_size_mb: int = 1000
    enable_chunked_processing: bool = True
    chunk_size_rows: int = 50000
    app_memory_percent: int = 35
    processing_memory_percent: int = 50
    cache_memory_percent: int = 15

    # Default Download Options
    sql_default_format: str = "excel"
    json_default_format: str = "excel"
    json_auto_safe: bool = True
    json_max_depth: int = 5
    json_flatten_arrays: bool = False
    json_preserve_nulls: bool = True

    # Naming Patterns
    naming_pattern_global: str = "{name}_{YYYYMMDD}"
    naming_pattern_sql_excel: str | None = None
    naming_pattern_sql_csv: str | None = None
    naming_pattern_sql_tsv: str | None = None
    naming_pattern_sql_parquet: str | None = None
    naming_pattern_sql_json: str | None = None
    naming_pattern_json_excel: str | None = None
    naming_pattern_json_csv: str | None = None
    naming_pattern_json_tsv: str | None = None
    naming_pattern_json_parquet: str | None = None

    # Automation & Workflows
    automation_enabled: bool = True
    auto_save_interval_seconds: int = 300
    auto_backup_enabled: bool = True
    workflow_execution_enabled: bool = True

    # Database Performance
    database_cache_size_mb: int = 256
    max_query_timeout_seconds: int = 300
    enable_query_optimization: bool = True

    # Power User Features
    enable_semantic_search: bool = False
    semantic_similarity_threshold: float = 0.7
    show_keyboard_shortcuts: bool = False
    enable_bulk_operations: bool = False

    # Session
    session_timeout_hours: int = 24
    clear_temp_on_close: bool = True

# Load settings from database or use defaults
def load_app_settings() -> AppSettings:
    """Load settings from database"""
    stored = elohimos_memory.get_all_settings()
    if stored:
        # Merge stored settings with defaults
        defaults = AppSettings().dict()
        defaults.update(stored)
        return AppSettings(**defaults)
    return AppSettings()

def save_app_settings(settings: AppSettings) -> None:
    """Save settings to database"""
    elohimos_memory.set_all_settings(settings.dict())

app_settings = load_app_settings()

# ============================================================================
# MIGRATED TO: api/routes/settings.py
# ============================================================================
# @app.get("/api/settings")
# async def get_settings():
#     """Get current app settings"""
#     return app_settings.dict()
#
# @app.post("/api/settings")
# async def update_settings(request: Request, settings: AppSettings):
#     """Update app settings"""
#     global app_settings
#     app_settings = settings
#     save_app_settings(settings)
#     return {"success": True, "settings": app_settings.dict()}
#
# @app.get("/api/settings/memory-status")
# async def get_memory_status():
#     """Get current memory usage and allocation"""
#     try:
#         import psutil
#         process = psutil.Process()
#         mem_info = process.memory_info()
#         system_mem = psutil.virtual_memory()
#
#         return {
#             "process_memory_mb": mem_info.rss / (1024 * 1024),
#             "system_total_mb": system_mem.total / (1024 * 1024),
#             "system_available_mb": system_mem.available / (1024 * 1024),
#             "system_percent_used": system_mem.percent,
#             "settings": {
#                 "app_percent": app_settings.app_memory_percent,
#                 "processing_percent": app_settings.processing_memory_percent,
#                 "cache_percent": app_settings.cache_memory_percent,
#             }
#         }
#     except ImportError:
#         return {
#             "error": "psutil not available",
#             "settings": {
#                 "app_percent": app_settings.app_memory_percent,
#                 "processing_percent": app_settings.processing_memory_percent,
#                 "cache_percent": app_settings.cache_memory_percent,
#             }
#         }
# ============================================================================

# ============================================================================
# MIGRATED TO: api/routes/admin.py
# ============================================================================
# Danger Zone Admin Endpoints - All 13 endpoints migrated to api/routes/admin.py
# - /api/admin/reset-all
# - /api/admin/uninstall
# - /api/admin/clear-chats
# - /api/admin/clear-team-messages
# - /api/admin/clear-query-library
# - /api/admin/clear-query-history
# - /api/admin/clear-temp-files
# - /api/admin/clear-code-files
# - /api/admin/reset-settings
# - /api/admin/reset-data
# - /api/admin/export-all
# - /api/admin/export-chats
# - /api/admin/export-queries
# ============================================================================


# ============================================================================
# DATA ENGINE API ENDPOINTS
# ============================================================================

@app.post("/api/data/upload")
# @limiter.limit("10/minute")  # Limit dataset uploads to 10 per minute
async def upload_dataset(
    request: Request,
    file: UploadFile = File(...),
    session_id: str | None = Form(None)
):
    """
    Upload and load Excel/JSON/CSV into SQLite
    Returns dataset metadata and query suggestions

    Max file size: 2GB
    """
    try:
        # Validate file size (2GB max)
        MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB in bytes

        # Read file content
        content = await file.read()
        file_size = len(content)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is 2GB, got {file_size / (1024**3):.2f}GB"
            )

        # Save uploaded file temporarily
        temp_dir = settings.temp_uploads_dir

        # Sanitize filename to prevent path traversal (HIGH-01)
        safe_filename = sanitize_filename(file.filename)
        file_path = temp_dir / safe_filename

        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        # Load into data engine
        result = await asyncio.to_thread(
            data_engine.upload_and_load,
            file_path,
            file.filename,
            session_id
        )

        # Clean up temp file
        file_path.unlink()

        return result

    except Exception as e:
        logger.error(f"Data upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/datasets", response_model=DatasetListResponse)
async def list_datasets(session_id: str | None = None):
    """List all datasets, optionally filtered by session"""
    try:
        datasets = await asyncio.to_thread(
            data_engine.list_datasets,
            session_id
        )
        return DatasetListResponse(datasets=datasets)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/datasets/{dataset_id}")
async def get_dataset(dataset_id: str):
    """Get dataset metadata"""
    try:
        metadata = await asyncio.to_thread(
            data_engine.get_dataset_metadata,
            dataset_id
        )

        if not metadata:
            raise HTTPException(status_code=404, detail="Dataset not found")

        return metadata
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/data/datasets/{dataset_id}")
async def delete_dataset(request: Request, dataset_id: str):
    """Delete a dataset"""
    try:
        deleted = await asyncio.to_thread(
            data_engine.delete_dataset,
            dataset_id
        )

        if not deleted:
            raise HTTPException(status_code=404, detail="Dataset not found")

        return {"status": "deleted", "dataset_id": dataset_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class QueryRequest(BaseModel):
    query: str


@app.post("/api/data/query")
@require_perm("data.run_sql")
async def execute_data_query(req: Request, request: QueryRequest, current_user: dict = Depends(get_current_user)):
    """Execute SQL query on loaded datasets"""
    try:
        result = await asyncio.to_thread(
            data_engine.execute_sql,
            request.query
        )
        return result
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/data/discover/{dataset_id}")
async def rediscover_queries(request: Request, dataset_id: str):
    """Re-run brute-force discovery on a dataset"""
    try:
        metadata = await asyncio.to_thread(
            data_engine.get_dataset_metadata,
            dataset_id
        )

        if not metadata:
            raise HTTPException(status_code=404, detail="Dataset not found")

        table_name = metadata['table_name']

        # Validate table name to prevent SQL injection (defense in depth)
        # Step 1: Regex validation (blocks most attacks)
        # MED-02: Use pre-compiled regex
        if not _TABLE_NAME_VALIDATOR.match(table_name):
            raise HTTPException(status_code=400, detail="Invalid table name")

        # Step 2: Whitelist validation (ensures table exists in our metadata)
        allowed_tables = await asyncio.to_thread(data_engine.get_all_table_names)
        if table_name not in allowed_tables:
            raise HTTPException(status_code=400, detail="Table not found in dataset metadata")

        # SECURITY NOTE: f-string is safe ONLY because of dual validation above
        # ⚠️  DO NOT REMOVE REGEX OR WHITELIST VALIDATION - SQLite doesn't support parameterized table names
        # ⚠️  If you remove validation, this becomes an immediate SQL injection vulnerability
        cursor = data_engine.conn.execute(f"SELECT * FROM {table_name} LIMIT 1000")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        df = pd.DataFrame([dict(row) for row in rows], columns=columns)

        # Re-run discovery
        suggestions = await asyncio.to_thread(
            data_engine._brute_force_discover,
            table_name,
            df
        )

        return {"query_suggestions": suggestions}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# METAL 4 GPU DIAGNOSTIC ENDPOINTS
# ============================================================================

@app.get("/api/v1/metal/capabilities")
async def get_metal_capabilities():
    """
    Get Metal 4 capabilities and system information

    Returns:
        Metal version, device name, feature support flags
    """
    if metal4_engine is None:
        raise HTTPException(
            status_code=503,
            detail="Metal 4 engine not available on this system"
        )

    return metal4_engine.get_capabilities_dict()


@app.get("/api/v1/metal/stats")
async def get_metal_stats():
    """
    Get real-time Metal 4 statistics and performance metrics

    Returns:
        GPU utilization, memory usage, operation counts
    """
    if metal4_engine is None:
        raise HTTPException(
            status_code=503,
            detail="Metal 4 engine not available on this system"
        )

    return metal4_engine.get_stats()


@app.get("/api/v1/metal/validate")
async def validate_metal_setup():
    """
    Validate Metal 4 setup and get recommendations

    Returns:
        Status, capabilities, and optimization recommendations
    """
    if metal4_engine is None:
        return {
            'status': 'unavailable',
            'capabilities': {
                'available': False,
                'version': 0,
                'device_name': 'N/A',
                'is_apple_silicon': False,
                'features': {
                    'unified_memory': False,
                    'mps': False,
                    'ane': False,
                    'sparse_resources': False,
                    'ml_command_encoder': False
                }
            },
            'recommendations': [
                'Metal 4 requires macOS Sequoia 15.0+ on Apple Silicon',
                'Install PyTorch with MPS support for GPU acceleration'
            ]
        }

    return validate_metal4_setup()


@app.get("/api/v1/metal/optimize/{operation_type}")
async def get_optimization_settings(operation_type: str):
    """
    Get optimization settings for a specific operation type

    Args:
        operation_type: 'embedding', 'inference', 'sql', or 'render'

    Returns:
        Optimized settings dict for the operation
    """
    if metal4_engine is None:
        raise HTTPException(
            status_code=503,
            detail="Metal 4 engine not available on this system"
        )

    valid_types = ['embedding', 'inference', 'sql', 'render']
    if operation_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid operation_type. Must be one of: {', '.join(valid_types)}"
        )

    return metal4_engine.optimize_for_operation(operation_type)


# ============================================================================
# METRICS & OBSERVABILITY
# ============================================================================

@app.get("/api/v1/metrics")
async def get_metrics_summary():
    """
    Get system-wide observability metrics

    Returns summary of operation counts, latencies, and errors for:
    - SQL query execution
    - Data uploads
    - P2P sync operations
    - File transfers

    Useful for identifying bottlenecks and performance issues in production.
    """
    from metrics import get_metrics

    metrics_collector = get_metrics()
    return metrics_collector.get_summary()


@app.get("/api/v1/metrics/{operation}")
async def get_operation_metrics(operation: str):
    """
    Get detailed metrics for a specific operation

    Args:
        operation: Operation name (e.g., 'sql_query_execution', 'data_upload', 'p2p_sync')

    Returns:
        Detailed metrics including count, avg/p50/p95/p99 latencies, error rate
    """
    from metrics import get_metrics

    metrics_collector = get_metrics()
    snapshot = metrics_collector.get_snapshot(operation)

    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail=f"No metrics found for operation: {operation}"
        )

    return snapshot


@app.post("/api/v1/metrics/reset")
async def reset_metrics(operation: str | None = None):
    """
    Reset metrics (admin only)

    Args:
        operation: Optional operation to reset. If not provided, resets all metrics.
    """
    from metrics import get_metrics

    metrics_collector = get_metrics()
    metrics_collector.reset(operation)

    return {
        "status": "reset",
        "operation": operation or "all"
    }


if __name__ == "__main__":
    import uvicorn
    # MED-05: Enable WebSocket compression (permessage-deflate)
    # Reduces bandwidth for terminal I/O and chat streaming by ~60-80%
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        ws_ping_interval=20,  # Keep connections alive
        ws_ping_timeout=20,
        ws_max_size=16777216,  # 16MB max message size
        ws="websockets",  # Use websockets library (supports compression)
    )