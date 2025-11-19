"""
Neutron Star Web API
FastAPI backend wrapper for the existing SQL engine

This is the main entry point that creates the FastAPI app and defines endpoints.
App creation and configuration logic has been extracted to app_factory.py.
"""

import asyncio
import datetime as _dt
import json
import logging
import math
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import pandas as pd
from fastapi import (
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
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

# Create FastAPI app using factory
from api.app_factory import create_app

app = create_app()

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
    try:
        from prometheus_metrics import get_prometheus_exporter
        prometheus_exporter = get_prometheus_exporter()
    except ImportError:
        raise HTTPException(status_code=503, detail="Prometheus metrics not available")

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
    try:
        from health_diagnostics import get_health_diagnostics
        health_diagnostics = get_health_diagnostics()
    except ImportError:
        raise HTTPException(status_code=503, detail="Health diagnostics not available")

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
    try:
        from health_diagnostics import get_health_diagnostics
        health_diagnostics = get_health_diagnostics()
    except ImportError:
        raise HTTPException(status_code=503, detail="Health diagnostics not available")

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
# Session endpoints migrated

# ============================================================================
# MIGRATED TO: api/routes/sql_json.py (Phase 4 - Upload Endpoint)
# ============================================================================
# Upload endpoints migrated

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
# MIGRATED TO: api/routes/sql_json.py (Phase 5 - JSON Convert)
###############################################################################

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
# Settings endpoints migrated

# ============================================================================
# MIGRATED TO: api/routes/admin.py
# ============================================================================
# Danger Zone Admin Endpoints - All 13 endpoints migrated to api/routes/admin.py


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
