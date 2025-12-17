"""
SQL validation routes.

Handles SQL syntax validation before execution.
"""

from fastapi import APIRouter, HTTPException, status
from api.schemas.api_models import ValidationRequest, ValidationResponse
from api.routes.schemas import ErrorResponse, ErrorCode
from api.routes.sql_json.utils import get_logger, get_sessions, validate_session_exists
from api.routes.sql_json.sql_processor import validate_sql_syntax


router = APIRouter(tags=["sessions"])


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
        validate_session_exists(session_id, sessions)

        is_valid, errors, warnings = validate_sql_syntax(
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
