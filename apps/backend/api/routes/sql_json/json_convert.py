"""
JSON conversion routes.

Handles JSON to Excel conversion and download operations.
"""

import uuid
import aiofiles
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from api.schemas.api_models import JsonConvertRequest, JsonConvertResponse
from api.errors import http_400, http_404, http_500
from api.routes.sql_json.utils import (
    get_sessions,
    get_df_to_jsonsafe_records,
    get_logger,
    validate_session_exists
)


router = APIRouter(tags=["sessions"])


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
        validate_session_exists(session_id, sessions)

        # Security: Enforce JSON size limit (100MB)
        MAX_JSON_SIZE = 100 * 1024 * 1024  # 100MB
        json_size = len(body.json_data.encode('utf-8'))

        if json_size > MAX_JSON_SIZE:
            # Note: Using 413 Request Entity Too Large - no structured helper available
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"JSON payload too large ({json_size / 1024 / 1024:.1f}MB). Maximum size is {MAX_JSON_SIZE / 1024 / 1024}MB"
            )

        api_dir = Path(__file__).parent.parent.parent
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
                raise http_400(load_result.get('error', 'Failed to analyze JSON'))

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
            raise http_400(result.get('error', 'Conversion failed'))

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
                except (ValueError, OSError, pd.errors.EmptyDataError):
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
        raise http_500("Failed to convert JSON to Excel")
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
        validate_session_exists(session_id, sessions)

        if 'json_result' not in sessions[session_id]:
            raise http_404("No conversion result found", resource="json_result")

        json_result = sessions[session_id]['json_result']
        excel_path_str = json_result.get('excel_path')

        if not excel_path_str:
            # Clean up stale session data
            del sessions[session_id]['json_result']
            raise http_404("Result file path not found. Please convert again.", resource="excel_path")

        excel_path = Path(excel_path_str)

        # Validate file still exists
        if not excel_path.exists():
            # Clean up stale session data
            del sessions[session_id]['json_result']
            # Note: Using 410 Gone for expired files - no structured helper available
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Result file expired or was cleaned up. Please run the conversion again."
            )

        # Check file age (auto-cleanup after 24 hours)
        try:
            file_age_seconds = datetime.now().timestamp() - excel_path.stat().st_mtime
            if file_age_seconds > 86400:  # 24 hours
                excel_path.unlink(missing_ok=True)
                del sessions[session_id]['json_result']
                # Note: Using 410 Gone for expired files - no structured helper available
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="Result file expired (24-hour limit). Please run the conversion again."
                )
        except OSError as e:
            # File stat failed, file probably doesn't exist
            logger.error(f"File stat failed for {excel_path}", exc_info=True)
            del sessions[session_id]['json_result']
            raise http_404("Result file not accessible. Please run the conversion again.", resource="excel_file")

        if format == "excel":
            return FileResponse(
                excel_path,
                filename=f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            # Convert to other formats
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
                raise http_400(f"Invalid format: {format}. Allowed: excel, csv, tsv, parquet")

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
        raise http_500("Failed to download conversion result")
