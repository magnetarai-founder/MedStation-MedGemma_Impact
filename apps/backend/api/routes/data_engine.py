"""
Data Engine API endpoints.

Handles dataset uploads, queries, and management for the unified data engine.
"""

import asyncio
import logging
import re
from pathlib import Path

import aiofiles
import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from typing import Any, Dict

from api.auth_middleware import get_current_user
from api.permission_engine import require_perm
from api.schemas.api_models import DatasetListResponse
from api.utils import sanitize_filename

# Import data engine (will be initialized in main.py)
_data_engine = None

# Import settings (will be initialized in main.py)
_settings = None

# MED-02: Compile frequently-used regex patterns once at module load
_TABLE_NAME_VALIDATOR = re.compile(r'^[a-zA-Z0-9_]+$')

router = APIRouter(
    prefix="/api/data",
    tags=["Data Engine"],
    dependencies=[Depends(get_current_user)]  # All data endpoints require auth
)
logger = logging.getLogger(__name__)


def set_data_engine(engine) -> None:
    """Set the data engine instance (called from main.py during initialization)"""
    global _data_engine
    _data_engine = engine


def set_settings(settings) -> None:
    """Set the settings instance (called from main.py during initialization)"""
    global _settings
    _settings = settings


class QueryRequest(BaseModel):
    query: str


@router.post("/upload")
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
    if _data_engine is None or _settings is None:
        raise HTTPException(status_code=503, detail="Data engine not initialized")

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
        temp_dir = _settings.temp_uploads_dir

        # Sanitize filename to prevent path traversal (HIGH-01)
        safe_filename = sanitize_filename(file.filename)
        file_path = temp_dir / safe_filename

        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        # Load into data engine
        result = await asyncio.to_thread(
            _data_engine.upload_and_load,
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


@router.get("/datasets", response_model=DatasetListResponse)
async def list_datasets(session_id: str | None = None):
    """List all datasets, optionally filtered by session"""
    if _data_engine is None:
        raise HTTPException(status_code=503, detail="Data engine not initialized")

    try:
        datasets = await asyncio.to_thread(
            _data_engine.list_datasets,
            session_id
        )
        return DatasetListResponse(datasets=datasets)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str) -> Dict[str, Any]:
    """Get dataset metadata"""
    if _data_engine is None:
        raise HTTPException(status_code=503, detail="Data engine not initialized")

    try:
        metadata = await asyncio.to_thread(
            _data_engine.get_dataset_metadata,
            dataset_id
        )

        if not metadata:
            raise HTTPException(status_code=404, detail="Dataset not found")

        return metadata
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(request: Request, dataset_id: str) -> Dict[str, Any]:
    """Delete a dataset"""
    if _data_engine is None:
        raise HTTPException(status_code=503, detail="Data engine not initialized")

    try:
        deleted = await asyncio.to_thread(
            _data_engine.delete_dataset,
            dataset_id
        )

        if not deleted:
            raise HTTPException(status_code=404, detail="Dataset not found")

        return {"status": "deleted", "dataset_id": dataset_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
@require_perm("data.run_sql")
async def execute_data_query(req: Request, request: QueryRequest, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Execute SQL query on loaded datasets"""
    if _data_engine is None:
        raise HTTPException(status_code=503, detail="Data engine not initialized")

    try:
        result = await asyncio.to_thread(
            _data_engine.execute_sql,
            request.query
        )
        return result
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discover/{dataset_id}")
async def rediscover_queries(request: Request, dataset_id: str) -> Dict[str, Any]:
    """Re-run brute-force discovery on a dataset"""
    if _data_engine is None:
        raise HTTPException(status_code=503, detail="Data engine not initialized")

    try:
        metadata = await asyncio.to_thread(
            _data_engine.get_dataset_metadata,
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
        allowed_tables = await asyncio.to_thread(_data_engine.get_all_table_names)
        if table_name not in allowed_tables:
            raise HTTPException(status_code=400, detail="Table not found in dataset metadata")

        # SECURITY NOTE: f-string is safe ONLY because of dual validation above
        # ⚠️  DO NOT REMOVE REGEX OR WHITELIST VALIDATION - SQLite doesn't support parameterized table names
        # ⚠️  If you remove validation, this becomes an immediate SQL injection vulnerability
        cursor = _data_engine.conn.execute(f"SELECT * FROM {table_name} LIMIT 1000")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        df = pd.DataFrame([dict(row) for row in rows], columns=columns)

        # Re-run discovery
        suggestions = await asyncio.to_thread(
            _data_engine._brute_force_discover,
            table_name,
            df
        )

        return {"query_suggestions": suggestions}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
