"""
File upload routes.

Handles Excel, CSV, and JSON file uploads with validation and processing.
"""

import uuid
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Request, Query, status
from api.schemas.api_models import (
    FileUploadResponse,
    JsonUploadResponse,
    SheetNamesResponse
)
from api.routes.schemas import ErrorResponse, ErrorCode
from api.routes.sql_json.utils import (
    get_logger,
    get_sessions,
    get_config,
    get_save_upload,
    get_column_info,
    get_df_to_jsonsafe_records,
    get_rate_limiter,
    get_client_ip,
    get_sanitize_filename,
    validate_session_exists
)


router = APIRouter(tags=["sessions"])


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
        validate_session_exists(session_id, sessions)

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

        validate_session_exists(session_id, sessions)

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
        api_dir = Path(__file__).parent.parent.parent
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
        validate_session_exists(session_id, sessions)

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
