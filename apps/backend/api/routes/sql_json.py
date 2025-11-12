"""
SQL/JSON Router - Session-based data processing endpoints (upload + query).

Export remains served from api.main to avoid duplication while we
stabilize OpenAPI and behavior incrementally.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Request, Header, Body
from api.schemas.api_models import FileUploadResponse, QueryResponse

router = APIRouter()

# Getter functions to access shared state from main.py
def get_sessions():
    from api import main
    return main.sessions

def get_config():
    from neutron_utils.config import config
    return config

def get_save_upload():
    from api import main
    return main.save_upload

def get_column_info():
    from api import main
    return main.get_column_info

def get_df_to_jsonsafe_records():
    from api import main
    return main._df_to_jsonsafe_records

def get_rate_limiter():
    from api import main
    return main.rate_limiter

def get_client_ip():
    from api import main
    return main.get_client_ip

def get_is_duplicate_request():
    from api import main
    return main._is_duplicate_request

def get_sanitize_for_log():
    from api import main
    return main.sanitize_for_log

def get_store_query_result():
    from api import main
    return main._store_query_result

def get_logger():
    from api import main
    return main.logger

def get_SQLProcessor():
    from neutron_utils.sql_utils import SQLProcessor
    return SQLProcessor

def get_query_results():
    from api import main
    return main.query_results

def get_current_user():
    from api.main import get_current_user
    return get_current_user

def get_require_perm():
    from api.main import require_perm
    return require_perm

# Endpoints
@router.post("/{session_id}/upload", name="sessions_upload", response_model=FileUploadResponse)
async def upload_file_router(
    session_id: str,
    file: UploadFile = File(...),
    sheet_name: str | None = Form(None)
):
    """Upload and load an Excel file"""
    sessions = get_sessions()

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    if not file.filename.lower().endswith(('.xlsx', '.xls', '.xlsm', '.csv')):
        raise HTTPException(status_code=400, detail="Only Excel (.xlsx, .xls, .xlsm) and CSV files are supported")

    # Save file (streamed) and enforce max size
    save_upload = get_save_upload()
    file_path = await save_upload(file)
    size_mb = file_path.stat().st_size / (1024 * 1024)
    config = get_config()
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

        # Import QueryResult for type checking
        from neutron_core.engine import QueryResult

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

        # Get column info (canonical ColumnInfo from main.py)
        get_column_info_func = get_column_info()
        columns = get_column_info_func(preview_result.data)

        # JSON-safe preview
        df_to_jsonsafe = get_df_to_jsonsafe_records()
        preview_records = df_to_jsonsafe(preview_result.data)

        return {
            "filename": file.filename,
            "size_mb": file_info['size_mb'],
            "row_count": result.row_count,
            "column_count": len(result.column_names),
            "columns": [c.model_dump() for c in columns],
            "preview": preview_records
        }

    except HTTPException:
        raise
    except Exception as e:
        # Clean up file on error
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/query", name="sessions_query", response_model=QueryResponse)
async def execute_query_router(
    session_id: str,
    req: Request,
    body: dict = Body(...),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    """Execute SQL query with deduplication support"""
    sessions = get_sessions()
    rate_limiter = get_rate_limiter()
    get_client_ip_func = get_client_ip()
    is_duplicate_request = get_is_duplicate_request()
    sanitize_for_log = get_sanitize_for_log()
    store_query_result = get_store_query_result()
    logger = get_logger()
    SQLProcessor = get_SQLProcessor()
    df_to_jsonsafe = get_df_to_jsonsafe_records()

    # Request deduplication: Check if this is a duplicate request
    if idempotency_key:
        if is_duplicate_request(f"query:{idempotency_key}"):
            logger.warning(f"Duplicate query request detected: {idempotency_key}")
            raise HTTPException(
                status_code=409,
                detail="Duplicate request detected. This query was already executed recently. Please wait 60 seconds or use a different idempotency key."
            )

    # Rate limit: 60 queries per minute
    client_ip = get_client_ip_func(req)
    if not rate_limiter.check_rate_limit(f"query:{client_ip}", max_requests=60, window_seconds=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 60 queries per minute.")

    # Sanitize SQL for logging (redact potential sensitive data)
    sql_text = body.get('sql', '')
    sanitized_sql = sanitize_for_log(sql_text[:100])
    logger.info(f"Executing query for session {session_id}: {sanitized_sql}...")

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    engine = sessions[session_id]['engine']
    logger.info(f"Engine found for session {session_id}")

    # Clean SQL (strip comments/trailing semicolons) to avoid parsing issues when embedding in LIMIT wrapper
    cleaned_sql = SQLProcessor.clean_sql(sql_text)
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

    # Execute query with timeout protection
    # NOTE: True async cancellation requires aiosqlite (MED-06)
    # For now, we use asyncio.wait_for to enforce max query time
    timeout = body.get('timeout_seconds') or 300  # 5min default

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                engine.execute_sql,
                cleaned_sql,
                limit=body.get('limit')
            ),
            timeout=timeout
        )
        logger.info(f"Query execution completed, rows: {result.row_count if result else 'error'}")
    except asyncio.TimeoutError:
        logger.error(f"Query execution timed out after {timeout}s")
        raise HTTPException(
            status_code=408,
            detail=f"Query execution exceeded timeout of {timeout} seconds. Consider adding a LIMIT clause or optimizing your query."
        )
    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        raise

    if result.error:
        raise HTTPException(status_code=400, detail=result.error)

    # Store full result for export (with size limits)
    query_id = str(uuid.uuid4())
    cached = store_query_result(query_id, result.data)

    if not cached:
        logger.warning(f"Query result not cached (too large), export will be unavailable")

    # Store query info
    sessions[session_id]['queries'][query_id] = {
        "sql": sql_text,
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

    preview_data = df_to_jsonsafe(preview_df)

    return {
        "query_id": query_id,
        "row_count": result.row_count,
        "column_count": len(result.column_names),
        "columns": result.column_names,
        "execution_time_ms": result.execution_time_ms,
        "preview": preview_data,
        "has_more": result.row_count > preview_limit
    }

# Note: Export endpoint intentionally not registered here; served by api.main
