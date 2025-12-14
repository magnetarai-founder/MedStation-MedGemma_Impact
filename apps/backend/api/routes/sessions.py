"""
Session Management Routes

Manages database query sessions with isolated NeutronEngine instances.
Each session has its own engine, uploaded files, and query results.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from neutron_core.engine import NeutronEngine
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

router = APIRouter(
    prefix="/api/v1/sessions",
    tags=["sessions"]
)

# Import shared state from main.py
# NOTE: Circular import is OK here during migration - sessions/query_results
# are module-level vars that get populated after all imports complete
def get_sessions():
    from api import main
    return main.sessions

def get_query_results():
    from api import main
    return main.query_results

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
    """Create a new session with isolated engine"""
    try:
        sessions = get_sessions()
        session_id = str(uuid.uuid4())
        created_at = datetime.now()

        sessions[session_id] = {
            "id": session_id,
            "created_at": created_at,
            "engine": NeutronEngine(),
            "files": {},
            "queries": {}
        }

        return SuccessResponse(
            data=SessionResponse(session_id=session_id, created_at=created_at),
            message="Session created successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to create session"
            ).model_dump()
        )

@router.delete(
    "/{session_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    summary="Delete session",
    description="Clean up session and its resources (engine, files, query results)"
)
async def delete_session(session_id: str) -> SuccessResponse[Dict]:
    """Clean up session and its resources"""
    try:
        sessions = get_sessions()
        query_results = get_query_results()

        if session_id not in sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Session not found"
                ).model_dump()
            )

        session = sessions[session_id]

        # Close engine
        if 'engine' in session:
            session['engine'].close()

        # Clean up temp files
        for file_info in session.get('files', {}).values():
            if 'path' in file_info and Path(file_info['path']).exists():
                Path(file_info['path']).unlink()

        # Clean up query results
        for query_id in session.get('queries', {}):
            query_results.pop(query_id, None)

        del sessions[session_id]

        return SuccessResponse(
            data={"session_id": session_id},
            message="Session deleted successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to delete session"
            ).model_dump()
        )
