"""
Chat Files Routes - File upload and attachment management

Provides endpoints for uploading files to chat sessions.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, status

try:
    from api.auth_middleware import get_current_user, User
except ImportError:
    from auth_middleware import get_current_user, User
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["chat-files"]
)


@router.post(
    "/sessions/{chat_id}/upload",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="chat_upload_file",
    summary="Upload file to chat",
    description="Upload a file attachment to a chat session"
)
async def upload_file_to_chat(
    chat_id: str,
    file: UploadFile = File(..., description="File to upload"),
    current_user: User = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """Upload a file to a chat session"""
    from api.services import chat

    try:
        user_id = current_user.get("user_id") if isinstance(current_user, dict) else current_user.user_id

        # Verify session exists
        session = await chat.get_session(chat_id, user_id=user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Chat session not found"
                ).model_dump()
            )

        # Read file content
        content = await file.read()

        # Upload file
        file_info = await chat.upload_file_to_chat(
            chat_id=chat_id,
            filename=file.filename or "upload",
            content=content,
            content_type=file.content_type or "application/octet-stream"
        )

        return SuccessResponse(
            data=file_info,
            message=f"File '{file.filename}' uploaded successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to upload file", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to upload file"
            ).model_dump()
        )
