"""
Progress streaming (SSE) API endpoints.

Server-Sent Events endpoints for real-time progress updates on long-running tasks.
"""

import asyncio
import json
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from api.main import (
    delete_progress_stream,
    get_progress_stream,
    list_progress_streams,
    update_progress_stream,
)

router = APIRouter(prefix="/api/v1/progress", tags=["Progress Streaming"])
logger = logging.getLogger(__name__)


@router.get("/{task_id}")
async def progress_stream(task_id: str):
    """
    Server-Sent Events (SSE) endpoint for streaming progress updates

    Usage: GET /api/v1/progress/{task_id}
    Returns: text/event-stream with progress events

    Event format:
    {
        "task_id": "abc123",
        "status": "running|completed|failed|cancelled",
        "progress": 0-100,
        "message": "Progress message",
        "timestamp": "2025-01-01T00:00:00"
    }
    """
    async def event_generator():
        """Generate SSE events for progress updates"""
        try:
            last_update = None
            heartbeat_count = 0

            while True:
                # Check if task exists in progress tracking
                task_data = get_progress_stream(task_id)

                if task_data:
                    # Only send update if data changed
                    current_update = task_data.get("updated_at")
                    if current_update != last_update:
                        last_update = current_update

                        # Format SSE event
                        event_data = {
                            "task_id": task_id,
                            "status": task_data.get("status", "running"),
                            "progress": task_data.get("progress", 0),
                            "message": task_data.get("message", ""),
                            "timestamp": datetime.now(UTC).isoformat()
                        }

                        yield f"data: {json.dumps(event_data)}\n\n"

                        # Stop streaming if completed or failed
                        if task_data.get("status") in ["completed", "failed", "cancelled"]:
                            logger.info(f"Progress stream ending for task {task_id}: {task_data.get('status')}")
                            break
                else:
                    # Task not found, send initial event
                    yield f"data: {json.dumps({'task_id': task_id, 'status': 'not_found', 'message': 'Task not found or not started'})}\n\n"
                    break

                # Send heartbeat every 30 seconds to keep connection alive
                heartbeat_count += 1
                if heartbeat_count >= 30:
                    yield f": heartbeat\n\n"
                    heartbeat_count = 0

                # Wait before next check
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info(f"Progress stream cancelled for task {task_id}")
        except Exception as e:
            logger.error(f"Error in progress stream for task {task_id}: {e}")
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@router.post("/{task_id}")
async def update_progress(
    task_id: str,
    request: Request
):
    """
    Update progress for a task (internal use or webhook)

    Body: {
        "status": "running|completed|failed|cancelled",
        "progress": 0-100,
        "message": "Progress message"
    }
    """
    try:
        body = await request.json()
        status = body.get("status", "running")
        progress = body.get("progress", 0)
        message = body.get("message", "")

        updated_at = datetime.now(UTC).isoformat()
        update_progress_stream(task_id, status, progress, message, updated_at)

        logger.debug(f"Updated progress for task {task_id}: {status} ({progress}%)")

        return {"task_id": task_id, "updated": True}

    except Exception as e:
        logger.error(f"Failed to update progress for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}")
async def clear_progress(task_id: str):
    """Clear progress tracking for a completed task"""
    cleared = delete_progress_stream(task_id)

    if cleared:
        logger.info(f"Cleared progress tracking for task {task_id}")
        return {"task_id": task_id, "cleared": True}

    raise HTTPException(status_code=404, detail="Task not found")


@router.get("")
async def list_active_tasks():
    """List all active progress tracking tasks"""
    tasks = list_progress_streams()
    return {
        "tasks": tasks,
        "total": len(tasks)
    }
