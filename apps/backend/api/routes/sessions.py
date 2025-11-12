import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from neutron_core.engine import NeutronEngine

router = APIRouter()

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

@router.post("/create", response_model=SessionResponse)
async def create_session(request: Request):
    """Create a new session with isolated engine"""
    sessions = get_sessions()
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "id": session_id,
        "created_at": datetime.now(),
        "engine": NeutronEngine(),
        "files": {},
        "queries": {}
    }
    return SessionResponse(session_id=session_id, created_at=sessions[session_id]["created_at"])

@router.delete("/{session_id}")
async def delete_session(request: Request, session_id: str):
    """Clean up session and its resources"""
    sessions = get_sessions()
    query_results = get_query_results()

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

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
    return {"message": "Session deleted"}
