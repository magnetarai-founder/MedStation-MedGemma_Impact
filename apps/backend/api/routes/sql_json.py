"""
SQL/JSON Router - Session-based data processing endpoints.

Handles upload, query, validation, export, and JSON conversion operations.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Request, Header, Body, Query, Depends, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from api.schemas.api_models import (
    FileUploadResponse,
    QueryResponse,
    ValidationRequest,
    ValidationResponse,
    QueryHistoryResponse,
    SuccessResponse,
    SheetNamesResponse,
    TablesListResponse,
    JsonUploadResponse,
    JsonConvertRequest,
    JsonConvertResponse,
    ExportRequest,
)

router = APIRouter(tags=["sessions"])

# Getter functions to access shared state from main.py
def get_sessions():
    from api import main
    return main.sessions

def get_config():
    from neutron_utils.config import config
    return config

def get_save_upload():
    from api.services.files import save_upload
    return save_upload

def get_column_info():
    from api.services.sql_helpers import get_column_info as _get_column_info
    return _get_column_info

def get_df_to_jsonsafe_records():
    from api.services.sql_helpers import df_to_jsonsafe_records
    return df_to_jsonsafe_records

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

def get_query_results():
    from api import main
    return main.query_results

def get_query_result_sizes():
    from api import main
    return main._query_result_sizes

def get_total_cache_size_ref():
    from api import main
    return main

def get_sanitize_filename():
    from api.main import sanitize_filename
    return sanitize_filename

# Endpoints
@router.post(
    "/{session_id}/upload",
    name="sessions_upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_200_OK
)
async def upload_file_router(
    session_id: str,
    file: UploadFile = File(...),
    sheet_name: str | None = Form(None)
) -> FileUploadResponse:
    """Upload and load an Excel file"""
    logger = get_logger()
    sessions = get_sessions()

    try:
        if session_id not in sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Session '{session_id}' not found",
                    details={"session_id": session_id}
                ).model_dump()
            )

        if not file.filename.lower().endswith(('.xlsx', '.xls', '.xlsm', '.csv')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Only Excel (.xlsx, .xls, .xlsm) and CSV files are supported",
                    details={"filename": file.filename}
                ).model_dump()
            )

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
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=f"File too large: {size_mb:.1f} MB (limit {int(max_mb)} MB)",
                    details={"size_mb": size_mb, "max_mb": max_mb}
                ).model_dump()
            )

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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message="Internal error: invalid engine result during load"
                ).model_dump()
            )

        if result.error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=result.error
                ).model_dump()
            )

        # Get preview data
        preview_result = engine.execute_sql("SELECT * FROM excel_file LIMIT 20")

        if preview_result is None or not isinstance(preview_result, QueryResult):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message="Internal error: invalid engine result during preview"
                ).model_dump()
            )

        if preview_result.error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message=preview_result.error
                ).model_dump()
            )

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

        return FileUploadResponse(
            filename=file.filename,
            size_mb=file_info['size_mb'],
            row_count=result.row_count,
            column_count=len(result.column_names),
            columns=[c.model_dump() for c in columns],
            preview=preview_records
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload file for session {session_id}", exc_info=True)
        # Clean up file on error
        if 'file_path' in locals() and file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to upload and process file"
            ).model_dump()
        )

@router.post(
    "/{session_id}/query",
    name="sessions_query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK
)
async def execute_query_router(
    session_id: str,
    req: Request,
    body: dict = Body(...),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
) -> QueryResponse:
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

    try:
        # Request deduplication: Check if this is a duplicate request
        if idempotency_key:
            if is_duplicate_request(f"query:{idempotency_key}"):
                logger.warning(f"Duplicate query request detected: {idempotency_key}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=ErrorResponse(
                        error_code=ErrorCode.CONFLICT,
                        message="Duplicate request detected. This query was already executed recently. Please wait 60 seconds or use a different idempotency key.",
                        details={"idempotency_key": idempotency_key}
                    ).model_dump()
                )

        # Rate limit: 60 queries per minute
        client_ip = get_client_ip_func(req)
        if not rate_limiter.check_rate_limit(f"query:{client_ip}", max_requests=60, window_seconds=60):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=ErrorResponse(
                    error_code=ErrorCode.RATE_LIMITED,
                    message="Rate limit exceeded. Max 60 queries per minute."
                ).model_dump()
            )

        # Sanitize SQL for logging (redact potential sensitive data)
        sql_text = body.get('sql', '')
        sanitized_sql = sanitize_for_log(sql_text[:100])
        logger.info(f"Executing query for session {session_id}: {sanitized_sql}...")

        if session_id not in sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Session '{session_id}' not found",
                    details={"session_id": session_id}
                ).model_dump()
            )

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
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorResponse(
                    error_code=ErrorCode.FORBIDDEN,
                    message=f"Query references unauthorized tables: {', '.join(unauthorized_tables)}. Only 'excel_file' is allowed.",
                    details={"unauthorized_tables": list(unauthorized_tables), "allowed_tables": list(allowed_tables)}
                ).model_dump()
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
            logger.error(f"Query execution timed out after {timeout}s", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail=ErrorResponse(
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message=f"Query execution exceeded timeout of {timeout} seconds. Consider adding a LIMIT clause or optimizing your query.",
                    details={"timeout_seconds": timeout}
                ).model_dump()
            )

        if result.error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=result.error
                ).model_dump()
            )

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

        return QueryResponse(
            query_id=query_id,
            row_count=result.row_count,
            column_count=len(result.column_names),
            columns=result.column_names,
            execution_time_ms=result.execution_time_ms,
            preview=preview_data,
            has_more=result.row_count > preview_limit
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query execution failed for session {session_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to execute query"
            ).model_dump()
        )

@router.post(
    "/{session_id}/validate",
    name="sessions_validate",
    response_model=ValidationResponse,
    status_code=status.HTTP_200_OK
)
async def validate_sql_router(
    session_id: str,
    body: ValidationRequest
) -> ValidationResponse:
    """Validate SQL syntax before execution"""
    logger = get_logger()
    sessions = get_sessions()

    try:
        if session_id not in sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Session '{session_id}' not found",
                    details={"session_id": session_id}
                ).model_dump()
            )

        from neutron_utils.sql_utils import SQLValidator
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SQL validation failed for session {session_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to validate SQL"
            ).model_dump()
        )

@router.get(
    "/{session_id}/query-history",
    name="sessions_query_history",
    response_model=QueryHistoryResponse,
    status_code=status.HTTP_200_OK
)
async def get_query_history_router(session_id: str) -> QueryHistoryResponse:
    """Get query history for a session"""
    logger = get_logger()
    sessions = get_sessions()

    try:
        if session_id not in sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Session '{session_id}' not found",
                    details={"session_id": session_id}
                ).model_dump()
            )

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

        return QueryHistoryResponse(history=history)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get query history for session {session_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve query history"
            ).model_dump()
        )

@router.delete(
    "/{session_id}/query-history/{query_id}",
    name="sessions_query_history_delete",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK
)
async def delete_query_from_history_router(
    session_id: str,
    query_id: str
) -> SuccessResponse:
    """Delete a query from history"""
    logger = get_logger()
    sessions = get_sessions()
    query_results = get_query_results()
    query_result_sizes = get_query_result_sizes()
    main_module = get_total_cache_size_ref()

    try:
        if session_id not in sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Session '{session_id}' not found",
                    details={"session_id": session_id}
                ).model_dump()
            )

        queries = sessions[session_id].get('queries', {})
        if query_id not in queries:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Query '{query_id}' not found",
                    details={"query_id": query_id, "session_id": session_id}
                ).model_dump()
            )

        del queries[query_id]

        # Also remove from query_results cache if it exists
        if query_id in query_results:
            size = query_result_sizes.get(query_id, 0)
            del query_results[query_id]
            if query_id in query_result_sizes:
                del query_result_sizes[query_id]
            main_module._total_cache_size -= size

        return SuccessResponse(success=True, message="Query deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete query {query_id} from session {session_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to delete query from history"
            ).model_dump()
        )

@router.get(
    "/{session_id}/sheet-names",
    name="sessions_sheet_names",
    response_model=SheetNamesResponse,
    status_code=status.HTTP_200_OK
)
async def sheet_names_router(
    session_id: str,
    filename: str | None = Query(None)
) -> SheetNamesResponse:
    """List Excel sheet names for an uploaded file in this session."""
    logger = get_logger()
    sessions = get_sessions()

    try:
        if session_id not in sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Session '{session_id}' not found",
                    details={"session_id": session_id}
                ).model_dump()
            )

        try:
            from neutron_utils.excel_ops import ExcelReader
        except Exception as e:
            logger.error("Excel utilities unavailable", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse(
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message="Excel utilities unavailable"
                ).model_dump()
            )

        from pathlib import Path
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="No Excel file found in session",
                    details={"session_id": session_id}
                ).model_dump()
            )

        path = Path(file_info['path'])
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="File not found on server",
                    details={"filename": file_info.get('filename')}
                ).model_dump()
            )

        sheets = ExcelReader.get_sheet_names(str(path))
        return SheetNamesResponse(
            filename=file_info.get('filename', path.name),
            sheets=sheets
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sheet names for session {session_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve sheet names"
            ).model_dump()
        )

@router.get(
    "/{session_id}/tables",
    name="sessions_tables",
    response_model=TablesListResponse,
    status_code=status.HTTP_200_OK
)
async def list_tables_router(session_id: str) -> TablesListResponse:
    """List loaded tables in session"""
    logger = get_logger()
    sessions = get_sessions()

    try:
        if session_id not in sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Session '{session_id}' not found",
                    details={"session_id": session_id}
                ).model_dump()
            )

        from pathlib import Path
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

        return TablesListResponse(tables=tables)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list tables for session {session_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to list tables"
            ).model_dump()
        )

# ============================================================================
# Export Endpoint
# ============================================================================

@router.post(
    "/{session_id}/export",
    name="sessions_export",
    status_code=status.HTTP_200_OK
)
async def export_results_router(
    session_id: str,
    req: Request,
    request: ExportRequest,
    current_user: dict = Depends(get_current_user)
):
    """Export query results"""
    sessions = get_sessions()
    query_results = get_query_results()
    df_to_jsonsafe = get_df_to_jsonsafe_records()
    logger = get_logger()
    require_perm = get_require_perm()

    try:
        # Apply permission check
        perm_decorator = require_perm("data.export")
        # Since we're inside a router, we need to call the decorator manually
        # The decorator expects an async function, so we check directly
        from api.main import has_permission
        if not has_permission(current_user, "data.export"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorResponse(
                    error_code=ErrorCode.FORBIDDEN,
                    message="Insufficient permissions to export data",
                    details={"required_permission": "data.export"}
                ).model_dump()
            )

        if session_id not in sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Session '{session_id}' not found",
                    details={"session_id": session_id}
                ).model_dump()
            )

        # Check if this is a JSON conversion result or SQL query result
        if request.query_id.startswith('json_'):
            # JSON conversion result
            if 'json_result' not in sessions[session_id]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error_code=ErrorCode.NOT_FOUND,
                        message="JSON conversion result not found. Please run the conversion first.",
                        details={"query_id": request.query_id}
                    ).model_dump()
                )

            # Load the Excel file that was created during conversion
            json_result = sessions[session_id]['json_result']
            excel_path = json_result.get('excel_path')

            if not excel_path or not Path(excel_path).exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error_code=ErrorCode.NOT_FOUND,
                        message="JSON conversion output file not found. Please run the conversion again."
                    ).model_dump()
                )

            # Read the Excel file into a DataFrame for export
            logger.info(f"Exporting JSON conversion result from {excel_path}")
            df = pd.read_excel(excel_path)
        else:
            # SQL query result
            if request.query_id not in query_results:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorResponse(
                        error_code=ErrorCode.NOT_FOUND,
                        message="Query results not found. Please run the query again.",
                        details={"query_id": request.query_id}
                    ).model_dump()
                )

            df = query_results[request.query_id]

        # Generate filename
        filename = request.filename or f"neutron_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Export based on format
        api_dir = Path(__file__).parent.parent
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
            json_records = df_to_jsonsafe(df)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json_records, f, indent=2, ensure_ascii=False)
            media_type = "application/json"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=f"Invalid export format: {request.format}",
                    details={"format": request.format, "allowed_formats": ["excel", "csv", "tsv", "parquet", "json"]}
                ).model_dump()
            )

        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type=media_type,
            background=BackgroundTask(lambda: file_path.unlink(missing_ok=True))
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed for session {session_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to export results"
            ).model_dump()
        )

# ============================================================================
# JSON Processing Endpoints
# ============================================================================

@router.post(
    "/{session_id}/json/upload",
    name="sessions_json_upload",
    response_model=JsonUploadResponse,
    status_code=status.HTTP_200_OK
)
async def upload_json_router(
    session_id: str,
    req: Request,
    file: UploadFile = File(...)
) -> JsonUploadResponse:
    """Upload and analyze JSON file"""
    sessions = get_sessions()
    rate_limiter = get_rate_limiter()
    get_client_ip_func = get_client_ip()
    sanitize_filename = get_sanitize_filename()
    df_to_jsonsafe = get_df_to_jsonsafe_records()
    logger = get_logger()

    try:
        # Rate limit: 10 uploads per minute
        client_ip = get_client_ip_func(req)
        if not rate_limiter.check_rate_limit(f"upload:{client_ip}", max_requests=10, window_seconds=60):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=ErrorResponse(
                    error_code=ErrorCode.RATE_LIMITED,
                    message="Rate limit exceeded. Max 10 uploads per minute."
                ).model_dump()
            )

        if session_id not in sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Session '{session_id}' not found",
                    details={"session_id": session_id}
                ).model_dump()
            )

        if not file.filename.endswith('.json'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message="Only JSON files are supported",
                    details={"filename": file.filename}
                ).model_dump()
            )

        # Security: Limit JSON file size to prevent OOM (100MB max)
        MAX_JSON_SIZE = 100 * 1024 * 1024  # 100MB
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning

        if file_size > MAX_JSON_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=f"JSON file too large ({file_size / 1024 / 1024:.1f}MB). Maximum size is {MAX_JSON_SIZE / 1024 / 1024}MB",
                    details={"size_mb": file_size / 1024 / 1024, "max_mb": MAX_JSON_SIZE / 1024 / 1024}
                ).model_dump()
            )

        # Save uploaded file temporarily
        from pathlib import Path
        import aiofiles
        api_dir = Path(__file__).parent.parent
        temp_dir = api_dir / "temp_uploads"
        temp_dir.mkdir(exist_ok=True)

        # Sanitize filename to prevent path traversal
        safe_filename = sanitize_filename(file.filename)
        file_path = temp_dir / f"{uuid.uuid4()}_{safe_filename}"

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
        from neutron_utils.json_to_excel import JsonToExcelEngine
        engine = JsonToExcelEngine()
        load_result = engine.load_json(str(file_path))

        if not load_result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=load_result.get('error', 'Failed to load JSON')
                ).model_dump()
            )

        # Get column paths
        columns = load_result.get('columns', [])

        # Preview data (first 10 objects)
        preview_data = []
        if 'preview' in load_result and hasattr(load_result['preview'], 'to_dict'):
            # Convert DataFrame to list of dicts using JSON-safe conversion
            preview_data = df_to_jsonsafe(load_result['preview'])
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

        # Get file size for response
        size_mb = file_path.stat().st_size / (1024 * 1024)

        return JsonUploadResponse(
            filename=file.filename,
            size_mb=size_mb,
            object_count=object_count,
            depth=max_depth,
            columns=columns[:50],  # Limit columns shown
            preview=preview_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JSON upload failed for session {session_id}", exc_info=True)
        if 'file_path' in locals() and file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to upload and analyze JSON file"
            ).model_dump()
        )


@router.post(
    "/{session_id}/json/convert",
    name="sessions_json_convert",
    response_model=JsonConvertResponse,
    status_code=status.HTTP_200_OK
)
async def convert_json_router(
    session_id: str,
    body: JsonConvertRequest
) -> JsonConvertResponse:
    """Convert JSON data to Excel format"""
    sessions = get_sessions()
    df_to_jsonsafe = get_df_to_jsonsafe_records()
    logger = get_logger()

    try:
        if session_id not in sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Session '{session_id}' not found",
                    details={"session_id": session_id}
                ).model_dump()
            )

        # Security: Enforce JSON size limit (100MB)
        MAX_JSON_SIZE = 100 * 1024 * 1024  # 100MB
        json_size = len(body.json_data.encode('utf-8'))

        if json_size > MAX_JSON_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=f"JSON payload too large ({json_size / 1024 / 1024:.1f}MB). Maximum size is {MAX_JSON_SIZE / 1024 / 1024}MB",
                    details={"size_mb": json_size / 1024 / 1024, "max_mb": MAX_JSON_SIZE / 1024 / 1024}
                ).model_dump()
            )

        from pathlib import Path
        import aiofiles
        import pandas as pd
        api_dir = Path(__file__).parent.parent
        temp_dir = api_dir / "temp_uploads"
        temp_dir.mkdir(exist_ok=True)

        # Create temporary files
        temp_json = temp_dir / f"{uuid.uuid4()}_input.json"
        temp_excel = temp_dir / f"{uuid.uuid4()}_output.xlsx"

        # Write JSON data to temp file
        async with aiofiles.open(temp_json, 'w') as f:
            await f.write(body.json_data)

        # Reuse engine from session if available, otherwise create new
        from neutron_utils.json_to_excel import JsonToExcelEngine
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
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error_code=ErrorCode.VALIDATION_ERROR,
                        message=load_result.get('error', 'Failed to analyze JSON')
                    ).model_dump()
                )

            # Return lightweight preview data with configurable limit
            preview_data = []
            if 'preview' in load_result:
                preview_raw = load_result['preview']
                if hasattr(preview_raw, 'to_dict'):
                    preview_data = df_to_jsonsafe(preview_raw)[:preview_limit]
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code=ErrorCode.VALIDATION_ERROR,
                    message=result.get('error', 'Conversion failed')
                ).model_dump()
            )

        # Store result in session (only if Excel file was actually created)
        if not preview_only:
            sessions[session_id]['json_result'] = {
                'excel_path': str(temp_excel),
                'result': result
            }

        # Use preview from result if available, otherwise fallback to reading Excel
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
                preview = df_to_jsonsafe(preview_df)
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JSON conversion failed for session {session_id}", exc_info=True)
        # Cleanup temp files
        if 'temp_json' in locals() and temp_json.exists():
            temp_json.unlink()
        if 'temp_excel' in locals() and temp_excel.exists():
            temp_excel.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to convert JSON to Excel"
            ).model_dump()
        )
    finally:
        # Always cleanup input JSON
        if 'temp_json' in locals() and temp_json.exists():
            temp_json.unlink()


@router.get(
    "/{session_id}/json/download",
    name="sessions_json_download",
    status_code=status.HTTP_200_OK
)
async def download_json_result_router(
    session_id: str,
    format: str = "excel"
):
    """Download converted JSON as Excel or CSV"""
    sessions = get_sessions()
    logger = get_logger()

    try:
        if session_id not in sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Session '{session_id}' not found",
                    details={"session_id": session_id}
                ).model_dump()
            )

        if 'json_result' not in sessions[session_id]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="No conversion result found"
                ).model_dump()
            )

        json_result = sessions[session_id]['json_result']
        excel_path_str = json_result.get('excel_path')

        if not excel_path_str:
            # Clean up stale session data
            del sessions[session_id]['json_result']
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Result file path not found. Please convert again."
                ).model_dump()
            )

        from pathlib import Path
        excel_path = Path(excel_path_str)

        # Validate file still exists
        if not excel_path.exists():
            # Clean up stale session data
            del sessions[session_id]['json_result']
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Result file expired or was cleaned up. Please run the conversion again."
                ).model_dump()
            )

        # Check file age (auto-cleanup after 24 hours)
        try:
            file_age_seconds = datetime.now().timestamp() - excel_path.stat().st_mtime
            if file_age_seconds > 86400:  # 24 hours
                excel_path.unlink(missing_ok=True)
                del sessions[session_id]['json_result']
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail=ErrorResponse(
                        error_code=ErrorCode.NOT_FOUND,
                        message="Result file expired (24-hour limit). Please run the conversion again."
                    ).model_dump()
                )
        except OSError as e:
            # File stat failed, file probably doesn't exist
            logger.error(f"File stat failed for {excel_path}", exc_info=True)
            del sessions[session_id]['json_result']
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Result file not accessible. Please run the conversion again."
                ).model_dump()
            )

        if format == "excel":
            return FileResponse(
                excel_path,
                filename=f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            # Convert to other formats
            import pandas as pd
            df = pd.read_excel(excel_path, sheet_name=0)

            if format == "csv":
                output_path = excel_path.with_suffix('.csv')
                df.to_csv(output_path, index=False)
                media_type = "text/csv"
                extension = ".csv"
            elif format == "tsv":
                output_path = excel_path.with_suffix('.tsv')
                df.to_csv(output_path, index=False, sep='\t')
                media_type = "text/tab-separated-values"
                extension = ".tsv"
            elif format == "parquet":
                output_path = excel_path.with_suffix('.parquet')
                df.to_parquet(output_path, index=False)
                media_type = "application/octet-stream"
                extension = ".parquet"
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse(
                        error_code=ErrorCode.VALIDATION_ERROR,
                        message=f"Invalid format: {format}",
                        details={"format": format, "allowed_formats": ["excel", "csv", "tsv", "parquet"]}
                    ).model_dump()
                )

            return FileResponse(
                output_path,
                filename=f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}",
                media_type=media_type,
                background=BackgroundTask(lambda: output_path.unlink(missing_ok=True))
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JSON download failed for session {session_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to download conversion result"
            ).model_dump()
        )

