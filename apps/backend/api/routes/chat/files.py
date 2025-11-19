"""
Chat Files Routes - File upload and attachment management
"""

import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Request, Depends

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/sessions/{chat_id}/upload", name="chat_upload_file")
async def upload_file_to_chat_endpoint(
    request: Request,
    chat_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a file to a chat session"""
    from api.services import chat

    try:
        # Verify session exists
        session = await chat.get_session(chat_id, user_id=current_user["user_id"])
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        # Read file content
        content = await file.read()

        # Upload file
        file_info = await chat.upload_file_to_chat(
            chat_id=chat_id,
            filename=file.filename or "upload",
            content=content,
            content_type=file.content_type or "application/octet-stream"
        )

        return file_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
