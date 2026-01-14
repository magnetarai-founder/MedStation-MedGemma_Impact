"""
Session Management Routes

Manages database query sessions with isolated NeutronEngine instances.
Each session has its own engine, uploaded files, and query results.

Follows MagnetarStudio API standards (see API_STANDARDS.md).

SECURITY: All endpoints require authentication to prevent:
- Resource exhaustion attacks (creating many sessions)
- Unauthorized data access
- Session hijacking
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict
from fastapi import APIRouter, HTTPException, status, Depends

from neutron_core.engine import NeutronEngine
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from api.auth_middleware import get_current_user

router = APIRouter(
    prefix="/api/v1/sessions",
    tags=["sessions"],
    dependencies=[Depends(get_current_user)]  # SECURITY: Require auth for all endpoints
)

# Use thread-safe state functions from core/state.py
from api.core.state import (
    get_session, set_session, delete_session, get_all_sessions,
    get_query_result, delete_query_result
)

# Models
class SessionResponse(BaseModel):
    session_id: str
    created_at: datetime

@router.post(
    "/create",
    response_model=SuccessResponse[SessionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create session",
    description="Create a new database query session with isolated engine"
)
async def create_session() -> SuccessResponse[SessionResponse]:
    """Create a new session with isolated engine (thread-safe)"""
    try:
        session_id = str(uuid.uuid4())
        created_at = datetime.now()

        # Use thread-safe state function
        set_session(session_id, {
            "id": session_id,
            "created_at": created_at,
            "engine": NeutronEngine(),
            "files": {},
            "queries": {}
        })

        return SuccessResponse(
            data=SessionResponse(session_id=session_id, created_at=created_at),
            message="Session created successfully"
        )

    except (MemoryError, OSError) as e:
        # Specific exceptions for resource issues
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Insufficient resources to create session"
            ).model_dump()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code=ErrorCode.VALIDATION_ERROR,
                message=str(e)
            ).model_dump()
        )

@router.delete(
    "/{session_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    summary="Delete session",
    description="Clean up session and its resources (engine, files, query results)"
)
async def delete_session_route(session_id: str) -> SuccessResponse[Dict]:
    """Clean up session and its resources (thread-safe)"""
    # Get session first (thread-safe)
    session = get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code=ErrorCode.NOT_FOUND,
                message="Session not found"
            ).model_dump()
        )

    try:
        # Close engine
        if 'engine' in session:
            session['engine'].close()

        # Clean up temp files
        for file_info in session.get('files', {}).values():
            if 'path' in file_info:
                file_path = Path(file_info['path'])
                if file_path.exists():
                    file_path.unlink()

        # Clean up query results (thread-safe)
        for query_id in session.get('queries', {}):
            delete_query_result(query_id)

        # Delete session (thread-safe)
        delete_session(session_id)

        return SuccessResponse(
            data={"session_id": session_id},
            message="Session deleted successfully"
        )

    except OSError as e:
        # File system errors during cleanup - session may be partially cleaned
        import logging
        logging.getLogger(__name__).warning(f"File cleanup error for session {session_id}: {e}")
        # Still delete the session even if file cleanup failed
        delete_session(session_id)
        return SuccessResponse(
            data={"session_id": session_id},
            message="Session deleted (some temp files may remain)"
        )
