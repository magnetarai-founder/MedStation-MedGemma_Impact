"""
Results export routes.

Handles exporting query results and JSON conversion results to various formats.
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from api.schemas.api_models import ExportRequest
from api.routes.schemas import ErrorResponse, ErrorCode
from api.routes.sql_json.utils import (
    get_sessions,
    get_query_results,
    get_df_to_jsonsafe_records,
    get_logger,
    get_require_perm,
    get_current_user,
    validate_session_exists
)


router = APIRouter(tags=["sessions"])


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

    try:
        # Apply permission check
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

        validate_session_exists(session_id, sessions)

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
        api_dir = Path(__file__).parent.parent.parent
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
