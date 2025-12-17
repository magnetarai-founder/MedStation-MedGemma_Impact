"""
SQL query execution routes.

Handles SQL query execution with rate limiting, deduplication, and security checks.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Header, Body, status
from api.schemas.api_models import QueryResponse
from api.routes.schemas import ErrorResponse, ErrorCode
from api.routes.sql_json.utils import (
    get_sessions,
    get_rate_limiter,
    get_client_ip,
    get_is_duplicate_request,
    get_sanitize_for_log,
    get_store_query_result,
    get_logger,
    get_SQLProcessor,
    get_df_to_jsonsafe_records,
    validate_session_exists
)
from api.routes.sql_json.sql_processor import clean_sql, extract_table_names, validate_table_access


router = APIRouter(tags=["sessions"])


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

        validate_session_exists(session_id, sessions)

        engine = sessions[session_id]['engine']
        logger.info(f"Engine found for session {session_id}")

        # Clean SQL (strip comments/trailing semicolons)
        cleaned_sql = clean_sql(sql_text)
        sanitized_cleaned = sanitize_for_log(cleaned_sql[:100])
        logger.info(f"Cleaned SQL: {sanitized_cleaned}...")

        # Security: Validate query only accesses allowed tables
        referenced_tables = extract_table_names(cleaned_sql)
        allowed_tables = {'excel_file'}  # Default table for uploaded files
        validate_table_access(referenced_tables, allowed_tables)

        # Execute query with timeout protection
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

        # Return preview (random sample of 100 rows if dataset is large)
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


@router.get(
    "/{session_id}/tables",
    name="sessions_tables",
    response_model=None,  # Will use TablesListResponse from schemas
    status_code=status.HTTP_200_OK
)
async def list_tables_router(session_id: str):
    """List loaded tables in session"""
    from pathlib import Path
    from api.schemas.api_models import TablesListResponse

    logger = get_logger()
    sessions = get_sessions()

    try:
        validate_session_exists(session_id, sessions)

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
