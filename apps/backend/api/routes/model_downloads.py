"""
Model Downloads Management Routes

Provides queue management, status, and cancel endpoints.
Sprint 5 Theme B: Download Queue Management
"""

import logging
from fastapi import APIRouter, HTTPException, Body, Depends, Request
from typing import List

from auth_middleware import get_current_user
from api.services.model_download_queue import get_download_queue

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/models/downloads",
    tags=["model-downloads"]
)


@router.post("/enqueue", name="models_enqueue_downloads")
async def enqueue_downloads(
    request: Request,
    models: List[str] = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    Enqueue models for download

    Body:
        {
            "models": ["llama3.2:3b", "qwen2.5-coder:7b"]
        }

    Returns:
        {
            "enqueued": ["llama3.2:3b"],
            "skipped": ["qwen2.5-coder:7b"]  // already downloading/queued
        }
    """
    queue = get_download_queue()

    enqueued = []
    skipped = []

    for model in models:
        success = await queue.enqueue(model)
        if success:
            enqueued.append(model)
        else:
            skipped.append(model)

    return {
        "enqueued": enqueued,
        "skipped": skipped,
        "message": f"Enqueued {len(enqueued)} model(s)"
    }


@router.get("/status", name="models_get_download_status")
async def get_download_status(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Get status of all downloads

    Returns:
        {
            "downloads": [
                {
                    "name": "llama3.2:3b",
                    "status": "downloading",
                    "progress": 45.2,
                    "speed": "5.2 MB/s",
                    "position": null
                },
                {
                    "name": "qwen2.5-coder:7b",
                    "status": "queued",
                    "progress": 0,
                    "speed": null,
                    "position": 2
                }
            ],
            "active_count": 2,
            "queued_count": 1
        }
    """
    queue = get_download_queue()
    downloads = await queue.get_status()

    active_count = sum(1 for d in downloads if d["status"] == "downloading")
    queued_count = sum(1 for d in downloads if d["status"] == "queued")

    return {
        "downloads": downloads,
        "active_count": active_count,
        "queued_count": queued_count
    }


@router.post("/{model_name}/cancel", name="models_cancel_download")
async def cancel_download(
    request: Request,
    model_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel a download (active or queued)

    Returns:
        {
            "success": true,
            "message": "Download canceled"
        }
    """
    queue = get_download_queue()
    success = await queue.cancel(model_name)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Download for '{model_name}' not found or already completed"
        )

    return {
        "success": True,
        "message": f"Download for '{model_name}' canceled"
    }


@router.delete("/clear-completed", name="models_clear_completed_downloads")
async def clear_completed_downloads(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Clear completed/failed/canceled downloads from history

    Returns:
        {
            "success": true,
            "message": "Completed downloads cleared"
        }
    """
    queue = get_download_queue()
    await queue.clear_completed()

    return {
        "success": True,
        "message": "Completed downloads cleared"
    }
