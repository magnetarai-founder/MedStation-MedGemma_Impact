"""
Model Downloads Management Routes

Provides queue management, status, and cancel endpoints for model downloads.

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import logging
from fastapi import APIRouter, HTTPException, Body, Depends, Request, status
from typing import List, Dict, Any

try:
    from api.auth_middleware import get_current_user
except ImportError:
    from api.auth_middleware import get_current_user
from api.services.model_download_queue import get_download_queue
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/models/downloads",
    tags=["model-downloads"]
)


@router.post(
    "/enqueue",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_201_CREATED,
    name="models_enqueue_downloads",
    summary="Enqueue model downloads",
    description="Enqueue one or more models for download"
)
async def enqueue_downloads(
    request: Request,
    models: List[str] = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """
    Enqueue models for download

    Models already downloading or queued will be skipped.
    """
    try:
        queue = get_download_queue()

        enqueued = []
        skipped = []

        for model in models:
            success = await queue.enqueue(model)
            if success:
                enqueued.append(model)
            else:
                skipped.append(model)

        return SuccessResponse(
            data={
                "enqueued": enqueued,
                "skipped": skipped
            },
            message=f"Enqueued {len(enqueued)} model(s), skipped {len(skipped)}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to enqueue models", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to enqueue model downloads"
            ).model_dump()
        )


@router.get(
    "/status",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="models_get_download_status",
    summary="Get download status",
    description="Get status of all model downloads (active, queued, completed, failed)"
)
async def get_download_status(
    request: Request,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """
    Get status of all downloads

    Returns list of downloads with their current status, progress, and queue position.
    """
    try:
        queue = get_download_queue()
        downloads = await queue.get_status()

        active_count = sum(1 for d in downloads if d["status"] == "downloading")
        queued_count = sum(1 for d in downloads if d["status"] == "queued")

        return SuccessResponse(
            data={
                "downloads": downloads,
                "active_count": active_count,
                "queued_count": queued_count
            },
            message=f"Retrieved status for {len(downloads)} download(s)"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get download status", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve download status"
            ).model_dump()
        )


@router.post(
    "/{model_name}/cancel",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="models_cancel_download",
    summary="Cancel download",
    description="Cancel an active or queued model download"
)
async def cancel_download(
    request: Request,
    model_name: str,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """Cancel a download (active or queued)"""
    try:
        queue = get_download_queue()
        success = await queue.cancel(model_name)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Download for '{model_name}' not found or already completed"
                ).model_dump()
            )

        return SuccessResponse(
            data={"model_name": model_name},
            message=f"Download for '{model_name}' canceled successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to cancel download for {model_name}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to cancel download"
            ).model_dump()
        )


@router.delete(
    "/clear-completed",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    name="models_clear_completed_downloads",
    summary="Clear completed downloads",
    description="Clear completed, failed, and canceled downloads from history"
)
async def clear_completed_downloads(
    request: Request,
    current_user: dict = Depends(get_current_user)
) -> SuccessResponse[Dict[str, Any]]:
    """Clear completed/failed/canceled downloads from history"""
    try:
        queue = get_download_queue()
        await queue.clear_completed()

        return SuccessResponse(
            data={},
            message="Completed downloads cleared successfully"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to clear completed downloads", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to clear completed downloads"
            ).model_dump()
        )
