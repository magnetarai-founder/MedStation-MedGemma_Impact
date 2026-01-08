"""
Vault Files Comments Routes

Handles file comments CRUD operations:
- Add comments to files
- Get file comments with pagination
- Update existing comments
- Delete comments

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from typing import Dict
from fastapi import APIRouter, HTTPException, Request, Form, Depends, status
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from api.auth_middleware import get_current_user
from api.utils import get_user_id
from api.services.vault.core import get_vault_service
from api.rate_limiter import get_client_ip, rate_limiter
from api.audit_logger import get_audit_logger

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

router = APIRouter()


@router.post(
    "/files/{file_id}/comments",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_201_CREATED,
    name="vault_files_add_comment",
    summary="Add comment to file",
    description="Add a comment to a file"
)
async def add_file_comment_endpoint(
    request: Request,
    file_id: str,
    comment_text: str = Form(...),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Add a comment to a file.

    Returns:
        SuccessResponse containing comment details
    """
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:comment:add:{get_user_id(current_user)}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.comment.added"
            ).model_dump()
        )

    service = get_vault_service()
    user_id = get_user_id(current_user)

    try:
        result = service.add_file_comment(user_id, vault_type, file_id, comment_text)

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.comment.added",
            resource="vault",
            resource_id=file_id,
            details={"file_id": file_id, "comment_id": result.get("comment_id")}
        )

        return SuccessResponse(data=result, message="Comment added to file successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add comment to file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to add comment"
            ).model_dump()
        )


@router.get(
    "/files/{file_id}/comments",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_get_comments",
    summary="Get file comments",
    description="Get file comments with pagination"
)
async def get_file_comments_endpoint(
    request: Request,
    file_id: str,
    vault_type: str = "real",
    limit: int = 50,
    offset: int = 0,
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Get file comments with pagination.

    Returns:
        SuccessResponse containing paginated comments
    """
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:comment:list:{get_user_id(current_user)}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.comment.list"
            ).model_dump()
        )

    service = get_vault_service()
    user_id = get_user_id(current_user)

    try:
        all_comments = service.get_file_comments(user_id, vault_type, file_id)
        # Apply pagination
        total = len(all_comments)
        comments = all_comments[offset:offset + limit]
        has_more = (offset + limit) < total

        return SuccessResponse(
            data={
                "comments": comments,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": has_more
            },
            message="File comments retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get comments for file {file_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to get file comments"
            ).model_dump()
        )


@router.put(
    "/comments/{comment_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_update_comment",
    summary="Update comment",
    description="Update a file comment"
)
async def update_file_comment_endpoint(
    request: Request,
    comment_id: str,
    comment_text: str = Form(...),
    vault_type: str = Form("real"),
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Update a comment.

    Returns:
        SuccessResponse containing updated comment details
    """
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:comment:update:{get_user_id(current_user)}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.comment.updated"
            ).model_dump()
        )

    service = get_vault_service()
    user_id = get_user_id(current_user)

    try:
        result = service.update_file_comment(user_id, vault_type, comment_id, comment_text)

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.comment.updated",
            resource="vault",
            resource_id=comment_id,
            details={"comment_id": comment_id}
        )

        return SuccessResponse(data=result, message="Comment updated successfully")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code=ErrorCode.NOT_FOUND,
                message=str(e)
            ).model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update comment {comment_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to update comment"
            ).model_dump()
        )


@router.delete(
    "/comments/{comment_id}",
    response_model=SuccessResponse[Dict],
    status_code=status.HTTP_200_OK,
    name="vault_files_delete_comment",
    summary="Delete comment",
    description="Delete a file comment"
)
async def delete_file_comment_endpoint(
    request: Request,
    comment_id: str,
    vault_type: str = "real",
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[Dict]:
    """
    Delete a comment.

    Returns:
        SuccessResponse confirming comment deleted
    """
    # Rate limiting: 60 requests per minute per user
    ip = get_client_ip(request)
    key = f"vault:comment:delete:{get_user_id(current_user)}:{ip}"
    if not rate_limiter.check_rate_limit(key, max_requests=60, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse(
                error_code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded for vault.comment.deleted"
            ).model_dump()
        )

    service = get_vault_service()
    user_id = get_user_id(current_user)

    try:
        success = service.delete_file_comment(user_id, vault_type, comment_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message="Comment not found"
                ).model_dump()
            )

        # Audit logging after success
        audit_logger.log(
            user_id=user_id,
            action="vault.comment.deleted",
            resource="vault",
            resource_id=comment_id,
            details={"comment_id": comment_id}
        )

        return SuccessResponse(data={"success": True}, message="Comment deleted")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete comment {comment_id}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to delete comment"
            ).model_dump()
        )
