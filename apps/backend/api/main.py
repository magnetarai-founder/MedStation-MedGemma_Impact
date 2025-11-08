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
from neutron_utils.json_utils import df_to_jsonsafe_records as _df_to_jsonsafe_records
from neutron_utils.sql_utils import SQLProcessor

from redshift_sql_processor import RedshiftSQLProcessor
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

# Session storage
sessions: dict[str, dict] = {}
query_results: dict[str, pd.DataFrame] = {}

# Initialize ElohimOS Memory System
elohimos_memory = ElohimOSMemory()

# Initialize Data Engine
data_engine = get_data_engine()



def cleanup_sessions():
    """Clean up all active sessions and close database connections"""
    logger.info("Cleaning up sessions...")
    try:
        # Clean up session engines
        for session_id, session in sessions.items():
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

    # Start background cleanup task
    cleanup_task = asyncio.create_task(cleanup_old_temp_files())
    logger.info("Started background temp file cleanup task")

    # Note: Auto-load favorites feature removed - get_favorites() method not implemented
    # Can be re-enabled when ModelManager.get_favorites() is added

    yield
    # Shutdown (clean shutdown via lifespan)
    print("Shutting down...")
    cleanup_task.cancel()
    cleanup_sessions()

# Request ID context for structured logging
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

app = FastAPI(
    title="ElohimOS API",
    description="SQL query engine for Excel files",
    version="1.0.0",
    lifespan=lifespan
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
)

# Import and include service routers
services_loaded = []
services_failed = []

try:
    from chat_service import public_router as chat_public_router
    from chat_service import router as chat_router
    app.include_router(chat_router)
    app.include_router(chat_public_router)  # Public endpoints (health check)
    services_loaded.append("Chat")
except Exception as e:
    services_failed.append("Chat")
    logger.warning(f"Chat service not available: {e}")

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
    from user_service import router as user_router
    app.include_router(user_router)
    services_loaded.append("User")
except Exception as e:
    services_failed.append("User")
    logger.debug(f"User service not available: {e}")

try:
    from team_service import router as team_router
    app.include_router(team_router)
    services_loaded.append("Team")
except Exception as e:
    services_failed.append("Team")
    logger.debug(f"Team service not available: {e}")

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

# Admin routes (God Rights support access)
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
    from permissions_admin import router as permissions_admin_router
    app.include_router(permissions_admin_router)
    services_loaded.append("Permissions Admin")
except Exception as e:
    services_failed.append("Permissions Admin")
    logger.error(f"Permissions Admin service failed to load: {e}")

# Monitoring routes
try:
    from monitoring_routes import router as monitoring_router
    app.include_router(monitoring_router)

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
    services_loaded.append("Monitoring")
except Exception as e:
    services_failed.append("Monitoring")
    logger.error(f"Monitoring service failed to load: {e}")

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

# Models
class SessionResponse(BaseModel):
    session_id: str
    created_at: datetime

class ColumnInfo(BaseModel):
    original_name: str
    clean_name: str
    dtype: str
    non_null_count: int
    null_count: int

class FileUploadResponse(BaseModel):
    filename: str
    size_mb: float
    row_count: int
    column_count: int
    columns: list[ColumnInfo]
    preview: list[dict]

class QueryRequest(BaseModel):
    sql: str
    limit: int | None = 1000
    dialect: SQLDialect = SQLDialect.DUCKDB
    timeout_seconds: int | None = 300

class QueryResponse(BaseModel):
    query_id: str
    row_count: int
    column_count: int
    columns: list[str]
    execution_time_ms: float
    preview: list[dict]
    has_more: bool

class ExportRequest(BaseModel):
    query_id: str
    format: str = Field(default="excel", pattern="^(excel|csv|tsv|parquet|json)$")
    filename: str | None = None

class ValidationRequest(BaseModel):
    sql: str
    dialect: SQLDialect = SQLDialect.DUCKDB

class ValidationResponse(BaseModel):
    is_valid: bool
    errors: list[str]
    warnings: list[str]

class QueryHistoryItem(BaseModel):
    id: str
    query: str
    timestamp: str
    executionTime: float | None = None
    rowCount: int | None = None
    status: str

class QueryHistoryResponse(BaseModel):
    history: list[QueryHistoryItem]

class SuccessResponse(BaseModel):
    success: bool
    message: str | None = None

class DatasetListResponse(BaseModel):
    datasets: list[dict[str, Any]]

# Helper functions
async def save_upload(upload_file: UploadFile) -> Path:
    """Save uploaded file to temp directory"""
    # Get the directory where this script is located
    api_dir = Path(__file__).parent
    temp_dir = api_dir / "temp_uploads"
    temp_dir.mkdir(exist_ok=True)

    # Sanitize filename to prevent path traversal (HIGH-01)
    safe_filename = sanitize_filename(upload_file.filename)
    file_path = temp_dir / f"{uuid.uuid4()}_{safe_filename}"
    # Stream upload to disk in chunks to avoid memory spikes
    chunk_size = 16 * 1024 * 1024  # 16MB
    async with aiofiles.open(file_path, 'wb') as f:
        while True:
            chunk = await upload_file.read(chunk_size)
            if not chunk:
                break
            await f.write(chunk)

    return file_path

def get_column_info(df: pd.DataFrame) -> list[ColumnInfo]:
    """Get column information with clean names"""
    from neutron_utils.sql_utils import ColumnNameCleaner
    cleaner = ColumnNameCleaner()

    columns: list[ColumnInfo] = []
    for col in df.columns:
        # Use the supported cleaner API (instance method `clean`)
        clean_name = cleaner.clean(str(col))
        columns.append(ColumnInfo(
            original_name=str(col),
            clean_name=clean_name,
            dtype=str(df[col].dtype),
            non_null_count=int(df[col].notna().sum()),
            null_count=int(df[col].isna().sum())
        ))
    return columns

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
            info["metal_device_name"] = engine.device.name()

            # This is the key value - Metal's recommended max working set size
            # This is what should be used for calculating model loading capacity
            recommended_max = engine.device.recommendedMaxWorkingSetSize()
            info["metal_available_memory_gb"] = round(recommended_max / (1024**3), 1)
    except:
        pass

    return info

# Fallback Admin device overview endpoint to avoid 404 if admin router fails to load
@app.get("/api/v1/admin/device/overview")
async def _fallback_admin_device_overview(request, current_user: dict = Depends(get_current_user)):
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


@app.post("/api/sessions/create", response_model=SessionResponse)
async def create_session(request: Request):
    """Create a new session with isolated engine"""
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "id": session_id,
        "created_at": datetime.now(),
        "engine": NeutronEngine(),
        "files": {},
        "queries": {}
    }
    return SessionResponse(session_id=session_id, created_at=sessions[session_id]["created_at"])

@app.delete("/api/sessions/{session_id}")
async def delete_session(request: Request, session_id: str):
    """Clean up session and its resources"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    # Close engine
    if 'engine' in session:
        session['engine'].close()

    # Clean up temp files
    for file_info in session.get('files', {}).values():
        if 'path' in file_info and Path(file_info['path']).exists():
            Path(file_info['path']).unlink()

    # Clean up query results
    for query_id in session.get('queries', {}):
        query_results.pop(query_id, None)

    del sessions[session_id]
    return {"message": "Session deleted"}

@app.post("/api/sessions/{session_id}/upload", response_model=FileUploadResponse)
async def upload_file(
    session_id: str,
    file: UploadFile = File(...),
    sheet_name: str | None = Form(None)
):
    """Upload and load an Excel file"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    if not file.filename.lower().endswith(('.xlsx', '.xls', '.xlsm', '.csv')):
        raise HTTPException(status_code=400, detail="Only Excel (.xlsx, .xls, .xlsm) and CSV files are supported")

    # Save file (streamed) and enforce max size
    file_path = await save_upload(file)
    size_mb = file_path.stat().st_size / (1024 * 1024)
    max_mb = float(config.get("max_file_size_mb", 1000))
    if size_mb > max_mb:
        try:
            file_path.unlink()
        except Exception:
            pass
        raise HTTPException(status_code=413, detail=f"File too large: {size_mb:.1f} MB (limit {int(max_mb)} MB)")

    try:
        engine = sessions[session_id]['engine']

        # Load into engine based on file type
        lower_name = file.filename.lower()
        if lower_name.endswith('.csv'):
            result = engine.load_csv(file_path, table_name="excel_file")
        else:
            result = engine.load_excel(file_path, table_name="excel_file", sheet_name=sheet_name)

        # Defensive checks in case engine returns unexpected value
        if result is None or not isinstance(result, QueryResult):
            raise HTTPException(status_code=500, detail="Internal error: invalid engine result during load")

        if result.error:
            raise HTTPException(status_code=400, detail=result.error)

        # Get preview data
        preview_result = engine.execute_sql("SELECT * FROM excel_file LIMIT 20")

        if preview_result is None or not isinstance(preview_result, QueryResult):
            raise HTTPException(status_code=500, detail="Internal error: invalid engine result during preview")

        if preview_result.error:
            raise HTTPException(status_code=500, detail=preview_result.error)

        # Store file info
        file_info = {
            "filename": file.filename,
            "path": str(file_path),
            "size_mb": file_path.stat().st_size / (1024 * 1024),
            "loaded_at": datetime.now()
        }
        sessions[session_id]['files'][file.filename] = file_info

        # Get column info
        columns = get_column_info(preview_result.data)

        # JSON-safe preview
        preview_records = _df_to_jsonsafe_records(preview_result.data)

        return FileUploadResponse(
            filename=file.filename,
            size_mb=file_info['size_mb'],
            row_count=result.row_count,
            column_count=len(result.column_names),
            columns=columns,
            preview=preview_records
        )

    except HTTPException:
        raise
    except Exception as e:
        # Clean up file on error
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_id}/validate", response_model=ValidationResponse)
async def validate_sql(request: Request, session_id: str, body: ValidationRequest):
    """Validate SQL syntax before execution"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    validator = SQLValidator()
    is_valid, errors, warnings = validator.validate_sql(
        body.sql,
        expected_table="excel_file"
    )

    return ValidationResponse(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings
    )

@app.post("/api/sessions/{session_id}/query", response_model=QueryResponse)
async def execute_query(req: Request, session_id: str, request: QueryRequest):
    """Execute SQL query"""
    # Rate limit: 60 queries per minute
    client_ip = get_client_ip(req)
    if not rate_limiter.check_rate_limit(f"query:{client_ip}", max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 60 queries per minute.")

    # Sanitize SQL for logging (redact potential sensitive data)
    sanitized_sql = sanitize_for_log(request.sql[:100])
    logger.info(f"Executing query for session {session_id}: {sanitized_sql}...")

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    engine = sessions[session_id]['engine']
    logger.info(f"Engine found for session {session_id}")

    # Clean SQL (strip comments/trailing semicolons) to avoid parsing issues when embedding in LIMIT wrapper
    cleaned_sql = SQLProcessor.clean_sql(request.sql)
    sanitized_cleaned = sanitize_for_log(cleaned_sql[:100])
    logger.info(f"Cleaned SQL: {sanitized_cleaned}...")

    # Security: Validate query only accesses allowed tables (session's uploaded file)
    from neutron_utils.sql_utils import SQLProcessor as SQLUtil
    referenced_tables = SQLUtil.extract_table_names(cleaned_sql)

    # Only allow queries to reference the excel_file table (or explicitly allowed tables)
    allowed_tables = {'excel_file'}  # Default table for uploaded files
    # TODO: Add support for multi-file sessions with explicit table names

    unauthorized_tables = set(referenced_tables) - allowed_tables
    if unauthorized_tables:
        raise HTTPException(
            status_code=403,
            detail=f"Query references unauthorized tables: {', '.join(unauthorized_tables)}. Only 'excel_file' is allowed."
        )

    # Execute query
    try:
        result = engine.execute_sql(
            cleaned_sql,
            dialect=request.dialect,
            limit=request.limit
        )
        logger.info(f"Query execution completed, rows: {result.row_count if result else 'error'}")
    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        raise

    if result.error:
        raise HTTPException(status_code=400, detail=result.error)

    # Store full result for export
    query_id = str(uuid.uuid4())
    query_results[query_id] = result.data

    # Store query info
    sessions[session_id]['queries'][query_id] = {
        "sql": request.sql,
        "executed_at": datetime.now(),
        "row_count": result.row_count
    }

    # Return preview (random sample of 100 rows if dataset is large) — JSON-safe
    preview_limit = 100
    if result.row_count > preview_limit:
        # Random sample for better data representation
        preview_df = result.data.sample(n=preview_limit, random_state=None)
    else:
        preview_df = result.data

    preview_data = _df_to_jsonsafe_records(preview_df)

    return QueryResponse(
        query_id=query_id,
        row_count=result.row_count,
        column_count=len(result.column_names),
        columns=result.column_names,
        execution_time_ms=result.execution_time_ms,
        preview=preview_data,
        has_more=result.row_count > preview_limit
    )

@app.get("/api/sessions/{session_id}/query-history", response_model=QueryHistoryResponse)
async def get_query_history(session_id: str):
    """Get query history for a session"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    queries = sessions[session_id].get('queries', {})
    history = []

    for query_id, query_info in queries.items():
        history.append({
            "id": query_id,
            "query": query_info["sql"],
            "timestamp": query_info["executed_at"].isoformat(),
            "executionTime": query_info.get("execution_time_ms"),
            "rowCount": query_info.get("row_count"),
            "status": "success"  # We only store successful queries
        })

    # Sort by timestamp descending (most recent first)
    history.sort(key=lambda x: x["timestamp"], reverse=True)

    return {"history": history}

@app.delete("/api/sessions/{session_id}/query-history/{query_id}", response_model=SuccessResponse)
async def delete_query_from_history(request: Request, session_id: str, query_id: str):
    """Delete a query from history"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    queries = sessions[session_id].get('queries', {})
    if query_id not in queries:
        raise HTTPException(status_code=404, detail="Query not found")

    del queries[query_id]

    # Also remove from query_results if it exists
    if query_id in query_results:
        del query_results[query_id]

    return SuccessResponse(success=True, message="Query deleted successfully")

@app.post("/api/sessions/{session_id}/export")
@require_perm("data.export")
async def export_results(req: Request, session_id: str, request: ExportRequest, current_user: dict = Depends(get_current_user)):
    """Export query results"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if this is a JSON conversion result or SQL query result
    if request.query_id.startswith('json_'):
        # JSON conversion result
        if 'json_result' not in sessions[session_id]:
            raise HTTPException(status_code=404, detail="JSON conversion result not found. Please run the conversion first.")

        # Load the Excel file that was created during conversion
        json_result = sessions[session_id]['json_result']
        excel_path = json_result.get('excel_path')

        if not excel_path or not Path(excel_path).exists():
            raise HTTPException(status_code=404, detail="JSON conversion output file not found. Please run the conversion again.")

        # Read the Excel file into a DataFrame for export
        logger.info(f"Exporting JSON conversion result from {excel_path}")
        df = pd.read_excel(excel_path)
    else:
        # SQL query result
        if request.query_id not in query_results:
            raise HTTPException(status_code=404, detail="Query results not found. Please run the query again.")

        df = query_results[request.query_id]

    # Generate filename
    filename = request.filename or f"neutron_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Export based on format
    api_dir = Path(__file__).parent
    temp_dir = api_dir / "temp_exports"
    temp_dir.mkdir(exist_ok=True)

    if request.format == "excel":
        file_path = temp_dir / f"{filename}.xlsx"
        df.to_excel(file_path, index=False)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif request.format == "csv":
        file_path = temp_dir / f"{filename}.csv"
        df.to_csv(file_path, index=False)
        media_type = "text/csv"
    elif request.format == "tsv":
        file_path = temp_dir / f"{filename}.tsv"
        df.to_csv(file_path, index=False, sep='\t')
        media_type = "text/tab-separated-values"
    elif request.format == "parquet":
        file_path = temp_dir / f"{filename}.parquet"
        df.to_parquet(file_path, index=False)
        media_type = "application/octet-stream"
    elif request.format == "json":
        file_path = temp_dir / f"{filename}.json"
        # Convert to JSON-safe records and write with proper formatting
        json_records = _df_to_jsonsafe_records(df)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_records, f, indent=2, ensure_ascii=False)
        media_type = "application/json"
    else:
        raise HTTPException(status_code=400, detail="Invalid export format")

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type=media_type,
        background=BackgroundTask(lambda: file_path.unlink(missing_ok=True))
    )

@app.get("/api/sessions/{session_id}/sheet-names")
async def sheet_names(session_id: str, filename: str | None = Query(None)):
    """List Excel sheet names for an uploaded file in this session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        from neutron_utils.excel_ops import ExcelReader
    except Exception:
        raise HTTPException(status_code=500, detail="Excel utilities unavailable")

    files = sessions[session_id].get('files', {})
    file_info = None
    if filename and filename in files:
        file_info = files[filename]
    else:
        # Pick first Excel file in session
        for info in files.values():
            if str(info.get('path', '')).lower().endswith(('.xlsx', '.xls', '.xlsm')):
                file_info = info
                break
    if not file_info:
        raise HTTPException(status_code=404, detail="No Excel file found in session")
    path = Path(file_info['path'])
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")
    try:
        sheets = ExcelReader.get_sheet_names(str(path))
        return {"filename": file_info.get('filename', path.name), "sheets": sheets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/tables")
async def list_tables(session_id: str):
    """List loaded tables in session"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    engine = sessions[session_id]['engine']
    tables = []

    for table_name, file_path in engine.tables.items():
        table_info = engine.get_table_info(table_name)
        tables.append({
            "name": table_name,
            "file": Path(file_path).name,
            "row_count": table_info.get('row_count', 0),
            "column_count": len(table_info.get('columns', []))
        })

    return {"tables": tables}

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

class JsonUploadResponse(BaseModel):
    filename: str
    size_mb: float
    object_count: int
    depth: int
    columns: list[str]
    preview: list[dict[str, Any]]

class JsonConvertRequest(BaseModel):
    json_data: str
    options: dict[str, Any] = Field(default_factory=lambda: {
        "expand_arrays": True,
        "max_depth": 5,
        "auto_safe": True,
        "include_summary": True
    })

class JsonConvertResponse(BaseModel):
    success: bool
    output_file: str
    total_rows: int
    sheets: list[str]
    columns: list[str]
    preview: list[dict[str, Any]]
    is_preview_only: bool = False

@app.post("/api/sessions/{session_id}/json/upload", response_model=JsonUploadResponse)
async def upload_json(request: Request, session_id: str, file: UploadFile = File(...)):
    """Upload and analyze JSON file"""
    # Rate limit: 10 uploads per minute
    client_ip = get_client_ip(request)
    if not rate_limiter.check_rate_limit(f"upload:{client_ip}", max_requests=10, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 10 uploads per minute.")

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Only JSON files are supported")

    # Security: Limit JSON file size to prevent OOM (100MB max, same as Excel)
    MAX_JSON_SIZE = 100 * 1024 * 1024  # 100MB
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size > MAX_JSON_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"JSON file too large ({file_size / 1024 / 1024:.1f}MB). Maximum size is {MAX_JSON_SIZE / 1024 / 1024}MB"
        )

    # Save uploaded file temporarily
    api_dir = Path(__file__).parent
    temp_dir = api_dir / "temp_uploads"
    temp_dir.mkdir(exist_ok=True)

    # Sanitize filename to prevent path traversal (HIGH-01)
    safe_filename = sanitize_filename(file.filename)
    file_path = temp_dir / f"{uuid.uuid4()}_{safe_filename}"

    try:
        # Stream file to disk instead of loading entirely into memory
        async with aiofiles.open(file_path, 'wb') as f:
            # Stream in chunks to avoid OOM
            chunk_size = 1024 * 1024  # 1MB chunks
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                await f.write(chunk)

        # Analyze JSON structure
        engine = JsonToExcelEngine()
        load_result = engine.load_json(str(file_path))

        if not load_result['success']:
            raise HTTPException(status_code=400, detail=load_result.get('error', 'Failed to load JSON'))

        # Get column paths
        columns = load_result.get('columns', [])

        # Preview data (first 10 objects)
        preview_data = []
        if 'preview' in load_result and hasattr(load_result['preview'], 'to_dict'):
            # Convert DataFrame to list of dicts using JSON-safe conversion
            preview_data = _df_to_jsonsafe_records(load_result['preview'])
        elif 'data' in load_result and isinstance(load_result['data'], list):
            preview_data = load_result['data'][:10]

        # Store JSON info in session
        sessions[session_id]['json_file'] = {
            'path': str(file_path),
            'filename': file.filename,
            'engine': engine,
            'columns': columns,
            'data': load_result.get('data', [])
        }

        # Get metadata for counts
        metadata = load_result.get('metadata', {})
        data = load_result.get('data', [])

        # Calculate object count based on data type
        if isinstance(data, list):
            object_count = len(data)
        elif isinstance(data, dict):
            # Count objects in detected arrays
            detected_arrays = load_result.get('detected_arrays', {})
            if detected_arrays:
                # Use the largest array count
                object_count = max(arr['length'] for arr in detected_arrays.values())
            else:
                object_count = 1
        else:
            object_count = 0

        # Estimate depth from column names
        max_depth = 1
        for col in columns:
            depth = col.count('.') + 1
            max_depth = max(max_depth, depth)

        return JsonUploadResponse(
            filename=file.filename,
            size_mb=len(content) / (1024 * 1024),
            object_count=object_count,
            depth=max_depth,
            columns=columns[:50],  # Limit columns shown
            preview=preview_data
        )

    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_id}/json/convert", response_model=JsonConvertResponse)
async def convert_json(request: Request, session_id: str, body: JsonConvertRequest):
    """Convert JSON data to Excel format"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # Security: Enforce JSON size limit (same as upload: 100MB)
    MAX_JSON_SIZE = 100 * 1024 * 1024  # 100MB
    json_size = len(body.json_data.encode('utf-8'))

    if json_size > MAX_JSON_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"JSON payload too large ({json_size / 1024 / 1024:.1f}MB). Maximum size is {MAX_JSON_SIZE / 1024 / 1024}MB"
        )

    api_dir = Path(__file__).parent
    temp_dir = api_dir / "temp_uploads"
    temp_dir.mkdir(exist_ok=True)

    # Create temporary files
    temp_json = temp_dir / f"{uuid.uuid4()}_input.json"
    temp_excel = temp_dir / f"{uuid.uuid4()}_output.xlsx"

    try:
        # Write JSON data to temp file
        async with aiofiles.open(temp_json, 'w') as f:
            await f.write(body.json_data)

        # Reuse engine from session if available, otherwise create new
        if 'json_file' in sessions[session_id] and 'engine' in sessions[session_id]['json_file']:
            engine = sessions[session_id]['json_file']['engine']
        else:
            engine = JsonToExcelEngine()

        # Check if preview_only mode
        preview_only = body.options.get('preview_only', False)

        if preview_only:
            # Only analyze structure, don't do full conversion
            preview_limit = body.options.get('limit', 100)
            logger.info(f"Analyzing JSON structure for preview (session {session_id}, limit {preview_limit})")

            load_result = engine.load_json(str(temp_json))
            if not load_result['success']:
                raise HTTPException(status_code=400, detail=load_result.get('error', 'Failed to analyze JSON'))

            # Return lightweight preview data with configurable limit
            preview_data = []
            if 'preview' in load_result:
                preview_raw = load_result['preview']
                if hasattr(preview_raw, 'to_dict'):
                    preview_data = _df_to_jsonsafe_records(preview_raw)[:preview_limit]
                elif isinstance(preview_raw, list):
                    preview_data = preview_raw[:preview_limit]
            elif 'data' in load_result and isinstance(load_result['data'], list):
                preview_data = load_result['data'][:preview_limit]

            # Get total rows from metadata or fallback
            total_rows = load_result.get('metadata', {}).get('total_records', len(load_result.get('data', [])))

            result = {
                'success': True,
                'preview_data': preview_data,
                'column_names': load_result.get('columns', []),
                'rows': total_rows,
                'sheet_names': ['Preview'],
                'sheets': 1
            }
            logger.info(f"Preview analysis completed: {result.get('rows', 0)} total rows, {len(preview_data)} in preview")
        else:
            # Full conversion
            logger.info(f"Starting JSON to Excel conversion for session {session_id}")

            result = engine.convert(
                str(temp_json),
                str(temp_excel),
                expand_arrays=body.options.get('expand_arrays', True),
                max_depth=body.options.get('max_depth', 5),
                auto_safe=body.options.get('auto_safe', True),
                include_summary=body.options.get('include_summary', True)
            )

            logger.info(f"Conversion completed with result: {result.get('success', False)}")

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Conversion failed'))

        # Store result in session (only if Excel file was actually created)
        if not preview_only:
            sessions[session_id]['json_result'] = {
                'excel_path': str(temp_excel),
                'result': result
            }

        # Use preview from result if available, otherwise fallback to reading Excel
        # Random sample for better data representation
        preview_limit = 100
        preview = []
        if 'preview_data' in result and result['preview_data']:
            preview_data = result['preview_data']
            if len(preview_data) > preview_limit:
                # Random sample
                import random
                preview = random.sample(preview_data, preview_limit)
            else:
                preview = preview_data
        elif temp_excel.exists():
            try:
                full_df = pd.read_excel(temp_excel)
                if len(full_df) > preview_limit:
                    preview_df = full_df.sample(n=preview_limit, random_state=None)
                else:
                    preview_df = full_df
                preview = _df_to_jsonsafe_records(preview_df)
            except Exception as e:
                logger.warning(f"Could not read Excel file for preview: {e}")

        # Get column information from result first
        column_list = result.get('column_names', [])[:50]
        if not column_list and 'columns' in result:
            if isinstance(result['columns'], list):
                column_list = result['columns'][:50]
            elif isinstance(result['columns'], int) and temp_excel.exists():
                try:
                    df_cols = pd.read_excel(temp_excel, nrows=0)
                    column_list = list(df_cols.columns)[:50]
                except:
                    column_list = []

        # Get sheet information
        sheet_names = result.get('sheet_names', [])
        if not sheet_names:
            sheet_count = result.get('sheets', 1)
            if sheet_count > 1:
                sheet_names = [f"Sheet{i+1}" for i in range(sheet_count)]
            else:
                sheet_names = ['Sheet1']

        # Get actual row count from the converted data
        actual_rows = result.get('rows', 0)
        if actual_rows == 0 and len(preview) > 0:
            # Fallback to preview length if engine didn't report row count
            actual_rows = len(preview)

        return JsonConvertResponse(
            success=True,
            output_file=temp_excel.name,
            total_rows=actual_rows,
            sheets=sheet_names,
            columns=column_list,
            preview=preview,
            is_preview_only=preview_only
        )

    except Exception as e:
        # Cleanup temp files
        for f in [temp_json, temp_excel]:
            if f.exists():
                f.unlink()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Always cleanup input JSON
        if temp_json.exists():
            temp_json.unlink()

@app.get("/api/sessions/{session_id}/json/download")
async def download_json_result(session_id: str, format: str = Query("excel", pattern="^(excel|csv|tsv|parquet)$")):
    """Download converted JSON as Excel or CSV"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    if 'json_result' not in sessions[session_id]:
        raise HTTPException(status_code=404, detail="No conversion result found")

    json_result = sessions[session_id]['json_result']
    excel_path_str = json_result.get('excel_path')

    if not excel_path_str:
        # Clean up stale session data
        del sessions[session_id]['json_result']
        raise HTTPException(status_code=404, detail="Result file path not found. Please convert again.")

    excel_path = Path(excel_path_str)

    # Validate file still exists
    if not excel_path.exists():
        # Clean up stale session data
        del sessions[session_id]['json_result']
        raise HTTPException(
            status_code=410,
            detail="Result file expired or was cleaned up. Please run the conversion again."
        )

    # Check file age (auto-cleanup after 24 hours)
    try:
        file_age_seconds = datetime.now().timestamp() - excel_path.stat().st_mtime
        if file_age_seconds > 86400:  # 24 hours
            excel_path.unlink(missing_ok=True)
            del sessions[session_id]['json_result']
            raise HTTPException(
                status_code=410,
                detail="Result file expired (24-hour limit). Please run the conversion again."
            )
    except OSError:
        # File stat failed, file probably doesn't exist
        del sessions[session_id]['json_result']
        raise HTTPException(
            status_code=404,
            detail="Result file not accessible. Please run the conversion again."
        )

    if format == "excel":
        return FileResponse(
            excel_path,
            filename=f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        # Convert to other formats
        try:
            df = pd.read_excel(excel_path, sheet_name=0)

            if format == "csv":
                output_path = excel_path.with_suffix('.csv')
                df.to_csv(output_path, index=False)
                media_type = "text/csv"
                extension = "csv"
            elif format == "tsv":
                output_path = excel_path.with_suffix('.tsv')
                df.to_csv(output_path, index=False, sep='\t')
                media_type = "text/tab-separated-values"
                extension = "tsv"
            elif format == "parquet":
                output_path = excel_path.with_suffix('.parquet')
                df.to_parquet(output_path, index=False)
                media_type = "application/octet-stream"
                extension = "parquet"

            return FileResponse(
                output_path,
                filename=f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}",
                media_type=media_type,
                background=BackgroundTask(lambda: output_path.unlink() if output_path.exists() else None)
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"{format.upper()} conversion failed: {str(e)}")

# ============================================================================
# Library API Endpoints (Saved Queries)
# ============================================================================

class SavedQueryRequest(BaseModel):
    name: str
    query: str
    query_type: str
    folder: str | None = None
    description: str | None = None
    tags: list[str] | None = None

class SavedQueryUpdateRequest(BaseModel):
    name: str | None = None
    query: str | None = None
    query_type: str | None = None
    folder: str | None = None
    description: str | None = None
    tags: list[str] | None = None

@app.post("/api/saved-queries")
async def save_query(request: Request, body: SavedQueryRequest):
    """Save a query for later use"""
    try:
        query_id = elohimos_memory.save_query(
            name=body.name,
            query=body.query,
            query_type=body.query_type,
            folder=body.folder,
            description=body.description,
            tags=body.tags
        )
        return {"id": query_id, "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/saved-queries")
async def get_saved_queries(
    folder: str | None = Query(None),
    query_type: str | None = Query(None)
):
    """Get all saved queries"""
    try:
        queries = elohimos_memory.get_saved_queries(
            folder=folder,
            query_type=query_type
        )
        return {"queries": queries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/saved-queries/{query_id}")
async def update_saved_query(request: Request, query_id: int, body: SavedQueryUpdateRequest):
    """Update a saved query (partial updates supported)"""
    try:
        # Get existing query
        all_queries = elohimos_memory.get_saved_queries()
        existing = next((q for q in all_queries if q['id'] == query_id), None)

        if not existing:
            raise HTTPException(status_code=404, detail="Query not found")

        # Merge updates with existing data
        elohimos_memory.update_saved_query(
            query_id=query_id,
            name=body.name if body.name is not None else existing['name'],
            query=body.query if body.query is not None else existing['query'],
            query_type=body.query_type if body.query_type is not None else existing['query_type'],
            folder=body.folder if body.folder is not None else existing.get('folder'),
            description=body.description if body.description is not None else existing.get('description'),
            tags=body.tags if body.tags is not None else (json.loads(existing.get('tags', '[]')) if existing.get('tags') else None)
        )
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/saved-queries/{query_id}")
async def delete_saved_query(request: Request, query_id: int):
    """Delete a saved query"""
    try:
        elohimos_memory.delete_saved_query(query_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

@app.get("/api/settings")
async def get_settings():
    """Get current app settings"""
    return app_settings.dict()

@app.post("/api/settings")
async def update_settings(request: Request, settings: AppSettings):
    """Update app settings"""
    global app_settings
    app_settings = settings
    save_app_settings(settings)
    return {"success": True, "settings": app_settings.dict()}

@app.get("/api/settings/memory-status")
async def get_memory_status():
    """Get current memory usage and allocation"""
    try:
        import psutil
        process = psutil.Process()
        mem_info = process.memory_info()
        system_mem = psutil.virtual_memory()

        return {
            "process_memory_mb": mem_info.rss / (1024 * 1024),
            "system_total_mb": system_mem.total / (1024 * 1024),
            "system_available_mb": system_mem.available / (1024 * 1024),
            "system_percent_used": system_mem.percent,
            "settings": {
                "app_percent": app_settings.app_memory_percent,
                "processing_percent": app_settings.processing_memory_percent,
                "cache_percent": app_settings.cache_memory_percent,
            }
        }
    except ImportError:
        return {
            "error": "psutil not available",
            "settings": {
                "app_percent": app_settings.app_memory_percent,
                "processing_percent": app_settings.processing_memory_percent,
                "cache_percent": app_settings.cache_memory_percent,
            }
        }

# ============================================================================
# Danger Zone Admin Endpoints
# ============================================================================

@app.post("/api/admin/reset-all")
# @limiter.limit("3/hour")  # Very strict limit for destructive admin operations
async def reset_all_data(request: Request):
    """Reset all app data - clears database and temp files"""
    try:
        import shutil

        # Clear all saved queries and history
        elohimos_memory.memory.conn.execute("DELETE FROM query_history")
        elohimos_memory.memory.conn.execute("DELETE FROM saved_queries")
        elohimos_memory.memory.conn.execute("DELETE FROM app_settings")
        elohimos_memory.memory.conn.commit()

        # Reset settings to defaults
        global app_settings
        app_settings = AppSettings()

        # Clear temp directories
        api_dir = Path(__file__).parent
        temp_uploads = api_dir / "temp_uploads"
        temp_exports = api_dir / "temp_exports"

        if temp_uploads.exists():
            shutil.rmtree(temp_uploads)
            temp_uploads.mkdir()

        if temp_exports.exists():
            shutil.rmtree(temp_exports)
            temp_exports.mkdir()

        # Clear all sessions
        sessions.clear()
        query_results.clear()

        return {"success": True, "message": "All data has been reset"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")

@app.post("/api/admin/uninstall")
async def uninstall_app(request: Request):
    """Uninstall app - removes all data directories"""
    try:
        import shutil
        from pathlib import Path

        # Close database connection
        elohimos_memory.close()

        # Get data directories
        api_dir = Path(__file__).parent
        neutron_data = api_dir / ".neutron_data"
        omnistudio_data = Path.home() / ".omnistudio"

        # Remove directories
        if neutron_data.exists():
            shutil.rmtree(neutron_data)

        if omnistudio_data.exists():
            shutil.rmtree(omnistudio_data)

        return {"success": True, "message": "App data has been uninstalled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Uninstall failed: {str(e)}")

# New Danger Zone Endpoints

@app.post("/api/admin/clear-chats")
async def clear_chats(request: Request):
    """Clear all AI chat history"""
    try:
        import shutil
        api_dir = Path(__file__).parent
        chats_dir = api_dir / ".neutron_data" / "chats"

        if chats_dir.exists():
            shutil.rmtree(chats_dir)
            chats_dir.mkdir(parents=True)
            (chats_dir / "sessions.json").write_text("[]")

        return {"success": True, "message": "AI chat history cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear chats failed: {str(e)}")

@app.post("/api/admin/clear-team-messages")
async def clear_team_messages(request: Request):
    """Clear P2P team chat history"""
    try:
        import shutil
        api_dir = Path(__file__).parent
        p2p_dir = api_dir / ".neutron_data" / "p2p"

        if p2p_dir.exists():
            shutil.rmtree(p2p_dir)
            p2p_dir.mkdir(parents=True)

        return {"success": True, "message": "Team messages cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear team messages failed: {str(e)}")

@app.post("/api/admin/clear-query-library")
async def clear_query_library(request: Request):
    """Clear all saved SQL queries"""
    try:
        elohimos_memory.memory.conn.execute("DELETE FROM saved_queries")
        elohimos_memory.memory.conn.commit()

        return {"success": True, "message": "Query library cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear library failed: {str(e)}")

@app.post("/api/admin/clear-query-history")
async def clear_query_history(request: Request):
    """Clear SQL execution history"""
    try:
        elohimos_memory.memory.conn.execute("DELETE FROM query_history")
        elohimos_memory.memory.conn.commit()

        return {"success": True, "message": "Query history cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear history failed: {str(e)}")

@app.post("/api/admin/clear-temp-files")
async def clear_temp_files(request: Request):
    """Clear uploaded files and exports"""
    try:
        import shutil
        api_dir = Path(__file__).parent

        for temp_dir_name in ["temp_uploads", "temp_exports"]:
            temp_dir = api_dir / temp_dir_name
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                temp_dir.mkdir()

        return {"success": True, "message": "Temp files cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear temp failed: {str(e)}")

@app.post("/api/admin/clear-code-files")
async def clear_code_files(request: Request):
    """Clear saved code editor files"""
    try:
        import shutil
        api_dir = Path(__file__).parent
        code_dir = api_dir / ".neutron_data" / "code"

        if code_dir.exists():
            shutil.rmtree(code_dir)
            code_dir.mkdir(parents=True)

        return {"success": True, "message": "Code files cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear code failed: {str(e)}")

@app.post("/api/admin/reset-settings")
async def reset_settings(request: Request):
    """Reset all settings to defaults"""
    try:
        elohimos_memory.memory.conn.execute("DELETE FROM app_settings")
        elohimos_memory.memory.conn.commit()

        global app_settings
        app_settings = AppSettings()

        return {"success": True, "message": "Settings reset to defaults"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset settings failed: {str(e)}")

@app.post("/api/admin/reset-data")
async def reset_data(request: Request):
    """Delete all data but keep settings"""
    try:
        import shutil

        # Clear database tables except settings
        elohimos_memory.memory.conn.execute("DELETE FROM query_history")
        elohimos_memory.memory.conn.execute("DELETE FROM saved_queries")
        elohimos_memory.memory.conn.commit()

        # Clear chat data
        api_dir = Path(__file__).parent
        neutron_data = api_dir / ".neutron_data"

        for subdir in ["chats", "p2p", "code", "uploads"]:
            target = neutron_data / subdir
            if target.exists():
                shutil.rmtree(target)
                target.mkdir(parents=True)

        # Clear temp files
        for temp_dir_name in ["temp_uploads", "temp_exports"]:
            temp_dir = api_dir / temp_dir_name
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                temp_dir.mkdir()

        sessions.clear()
        query_results.clear()

        return {"success": True, "message": "All data deleted, settings preserved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset data failed: {str(e)}")

@app.post("/api/admin/export-all")
@require_perm("data.export")
async def export_all(request: Request, current_user: dict = Depends(get_current_user)):
    """Export complete backup as ZIP"""
    try:
        import shutil
        import zipfile

        api_dir = Path(__file__).parent
        temp_dir = api_dir / "temp_exports"
        temp_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_path = temp_dir / f"omnistudio_backup_{timestamp}.zip"

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add chat data
            chats_dir = api_dir / ".neutron_data" / "chats"
            if chats_dir.exists():
                for file in chats_dir.rglob('*'):
                    if file.is_file():
                        zipf.write(file, f"chats/{file.relative_to(chats_dir)}")

            # Add database
            db_file = Path.home() / ".omnistudio" / "omnistudio.db"
            if db_file.exists():
                zipf.write(db_file, "database/omnistudio.db")

        return FileResponse(
            path=zip_path,
            filename=zip_path.name,
            media_type="application/zip",
            background=BackgroundTask(lambda: zip_path.unlink(missing_ok=True))
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.post("/api/admin/export-chats")
async def export_chats(request: Request):
    """Export AI chat history as JSON"""
    try:
        import json

        api_dir = Path(__file__).parent
        chats_dir = api_dir / ".neutron_data" / "chats"

        all_chats = []
        if chats_dir.exists():
            sessions_file = chats_dir / "sessions.json"
            if sessions_file.exists():
                all_chats = json.loads(sessions_file.read_text())

        temp_dir = api_dir / "temp_exports"
        temp_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_path = temp_dir / f"chats_export_{timestamp}.json"
        export_path.write_text(json.dumps(all_chats, indent=2))

        return FileResponse(
            path=export_path,
            filename=export_path.name,
            media_type="application/json",
            background=BackgroundTask(lambda: export_path.unlink(missing_ok=True))
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export chats failed: {str(e)}")

@app.post("/api/admin/export-queries")
async def export_queries(request: Request):
    """Export query library as JSON"""
    try:
        queries = elohimos_memory.get_saved_queries()

        temp_dir = Path(__file__).parent / "temp_exports"
        temp_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_path = temp_dir / f"queries_export_{timestamp}.json"
        export_path.write_text(json.dumps(queries, indent=2))

        return FileResponse(
            path=export_path,
            filename=export_path.name,
            media_type="application/json",
            background=BackgroundTask(lambda: export_path.unlink(missing_ok=True))
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export queries failed: {str(e)}")


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
        temp_dir = Path("/tmp/omnistudio_uploads")
        temp_dir.mkdir(exist_ok=True)

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
        if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
            raise HTTPException(status_code=400, detail="Invalid table name")

        # Step 2: Whitelist validation (ensures table exists in our metadata)
        allowed_tables = await asyncio.to_thread(data_engine.get_all_table_names)
        if table_name not in allowed_tables:
            raise HTTPException(status_code=400, detail="Table not found in dataset metadata")

        # Now safe to use f-string (SQLite doesn't support ? for table names)
        # Both regex and whitelist validation passed
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
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
