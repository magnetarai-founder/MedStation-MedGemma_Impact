"""
Celery Task Queue Service

Provides async task processing for long-running operations:
- Agent execution
- Code analysis
- File processing
- Email notifications
- Report generation

Features:
- Distributed task execution
- Task scheduling
- Priority queues
- Result tracking
- Retry logic
- Task monitoring
"""

import logging
import os
from datetime import timedelta
from typing import Any

try:
    from celery import Celery, Task
    from celery.result import AsyncResult

    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    Celery = None
    Task = None
    AsyncResult = None

logger = logging.getLogger(__name__)


# Celery configuration
BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")


# Initialize Celery app
celery_app = None

if CELERY_AVAILABLE:
    celery_app = Celery("magnetar_tasks", broker=BROKER_URL, backend=RESULT_BACKEND)

    # Configure Celery
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,  # 1 hour max
        task_soft_time_limit=3000,  # 50 minutes soft limit
        worker_prefetch_multiplier=4,
        worker_max_tasks_per_child=1000,
        result_expires=86400,  # Results expire after 1 day
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_routes={
            "agent.*": {"queue": "agents"},
            "analysis.*": {"queue": "analysis"},
            "notifications.*": {"queue": "notifications"},
        },
    )
else:
    logger.warning("Celery not available - task queue disabled")


class TaskQueue:
    """
    Task queue service for async job processing.

    Usage:
        queue = TaskQueue()

        # Submit task
        task_id = await queue.submit_task("agent.execute", task="Do something", context={})

        # Check status
        status = await queue.get_task_status(task_id)

        # Get result
        result = await queue.get_task_result(task_id)

        # Cancel task
        await queue.cancel_task(task_id)
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize task queue.

        Args:
            enabled: Whether task queue is enabled
        """
        self.enabled = enabled and CELERY_AVAILABLE

        if not CELERY_AVAILABLE:
            logger.warning("Task queue disabled - Celery not available")

    async def submit_task(
        self, task_name: str, *args, priority: int = 5, eta: timedelta | None = None, **kwargs
    ) -> str | None:
        """
        Submit task to queue.

        Args:
            task_name: Name of task to execute
            *args: Positional arguments for task
            priority: Task priority (0-10, higher = more important)
            eta: Estimated time of arrival (schedule for later)
            **kwargs: Keyword arguments for task

        Returns:
            Task ID or None if failed
        """
        if not self.enabled:
            logger.warning(f"Task queue disabled - cannot submit {task_name}")
            return None

        try:
            # Submit task
            result = celery_app.send_task(
                task_name,
                args=args,
                kwargs=kwargs,
                priority=priority,
                countdown=eta.total_seconds() if eta else None,
            )

            logger.info(f"Submitted task {task_name} with ID {result.id}")
            return result.id

        except Exception as e:
            logger.error(f"Failed to submit task {task_name}: {e}")
            return None

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        """
        Get task status.

        Args:
            task_id: Task ID

        Returns:
            Dict with task status info
        """
        if not self.enabled:
            return {"status": "unavailable", "task_id": task_id}

        try:
            result = AsyncResult(task_id, app=celery_app)

            return {
                "task_id": task_id,
                "status": result.status,
                "ready": result.ready(),
                "successful": result.successful() if result.ready() else None,
                "failed": result.failed() if result.ready() else None,
                "progress": result.info if result.status == "PROGRESS" else None,
            }

        except Exception as e:
            logger.error(f"Failed to get task status for {task_id}: {e}")
            return {"task_id": task_id, "status": "error", "error": str(e)}

    async def get_task_result(self, task_id: str, timeout: float | None = None) -> Any | None:
        """
        Get task result (blocks if not ready).

        Args:
            task_id: Task ID
            timeout: Max time to wait (None = wait forever)

        Returns:
            Task result or None if failed/timeout
        """
        if not self.enabled:
            return None

        try:
            result = AsyncResult(task_id, app=celery_app)

            if timeout:
                return result.get(timeout=timeout)
            else:
                return result.get()

        except Exception as e:
            logger.error(f"Failed to get task result for {task_id}: {e}")
            return None

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel running task.

        Args:
            task_id: Task ID

        Returns:
            True if cancelled, False otherwise
        """
        if not self.enabled:
            return False

        try:
            result = AsyncResult(task_id, app=celery_app)
            result.revoke(terminate=True)

            logger.info(f"Cancelled task {task_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False

    async def get_queue_stats(self, queue_name: str = "celery") -> dict[str, Any]:
        """
        Get queue statistics.

        Args:
            queue_name: Name of queue

        Returns:
            Dict with queue stats
        """
        if not self.enabled:
            return {"enabled": False}

        try:
            inspect = celery_app.control.inspect()

            active = inspect.active()
            scheduled = inspect.scheduled()
            reserved = inspect.reserved()

            return {
                "enabled": True,
                "queue": queue_name,
                "active_tasks": sum(len(tasks) for tasks in (active or {}).values()),
                "scheduled_tasks": sum(len(tasks) for tasks in (scheduled or {}).values()),
                "reserved_tasks": sum(len(tasks) for tasks in (reserved or {}).values()),
            }

        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"enabled": True, "error": str(e)}

    async def purge_queue(self, queue_name: str = "celery") -> int:
        """
        Purge all tasks from queue.

        Args:
            queue_name: Name of queue to purge

        Returns:
            Number of tasks purged
        """
        if not self.enabled:
            return 0

        try:
            purged = celery_app.control.purge()
            logger.info(f"Purged {purged} tasks from {queue_name}")
            return purged

        except Exception as e:
            logger.error(f"Failed to purge queue {queue_name}: {e}")
            return 0


# Global task queue instance
_task_queue: TaskQueue | None = None


def get_task_queue() -> TaskQueue:
    """Get global task queue instance"""
    global _task_queue

    if _task_queue is None:
        enabled = os.getenv("TASK_QUEUE_ENABLED", "true").lower() == "true"
        _task_queue = TaskQueue(enabled=enabled)

    return _task_queue


# ===== Celery Tasks =====

if CELERY_AVAILABLE:

    @celery_app.task(name="agent.execute", bind=True)
    def execute_agent_task(self, task: str, context: dict[str, Any] | None = None):
        """
        Execute agent task.

        Args:
            task: Task description
            context: Task context

        Returns:
            Task result
        """
        logger.info(f"Executing agent task: {task}")

        # Update progress
        self.update_state(state="PROGRESS", meta={"stage": "planning", "progress": 0.1})

        try:
            # Import here to avoid circular imports

            # Execute agent (this is sync, so we can call directly)
            # In production, you'd use the actual async agent execution
            result = {
                "status": "completed",
                "task": task,
                "result": "Agent task completed successfully",
            }

            self.update_state(state="PROGRESS", meta={"stage": "completed", "progress": 1.0})

            return result

        except Exception as e:
            logger.error(f"Agent task failed: {e}")
            self.update_state(state="FAILURE", meta={"error": str(e)})
            raise

    @celery_app.task(name="analysis.code_review")
    def code_review_task(file_path: str, content: str):
        """
        Perform code review.

        Args:
            file_path: Path to file
            content: File content

        Returns:
            Code review result
        """
        logger.info(f"Reviewing code: {file_path}")

        # Placeholder for actual code review logic
        return {"file": file_path, "issues": [], "suggestions": [], "status": "reviewed"}

    @celery_app.task(name="analysis.embedding_generation")
    def generate_embeddings_task(message_ids: list[int]):
        """
        Generate embeddings for messages.

        Args:
            message_ids: List of message IDs

        Returns:
            Number of embeddings generated
        """
        logger.info(f"Generating embeddings for {len(message_ids)} messages")

        # Placeholder for actual embedding generation
        return {"generated": len(message_ids)}

    @celery_app.task(name="notifications.send_email")
    def send_email_task(to: str, subject: str, body: str):
        """
        Send email notification.

        Args:
            to: Recipient email
            subject: Email subject
            body: Email body

        Returns:
            Send status
        """
        logger.info(f"Sending email to {to}: {subject}")

        # Placeholder for actual email sending
        return {"sent": True, "to": to}
