"""
n8n Client

HTTP client for n8n REST API with offline fallback support.

Features:
- Workflow CRUD operations
- Execution management with offline queue
- Webhook triggering
- Automatic caching of workflow lists

Extracted from n8n_integration.py during P2 decomposition.
"""

import aiohttp
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from api.automation.n8n.cache import get_n8n_cache

logger = logging.getLogger(__name__)


# ============================================
# CONFIGURATION MODELS
# ============================================

class N8NConfig(BaseModel):
    """n8n instance configuration"""
    base_url: str  # e.g., "https://n8n.example.com"
    api_key: str
    enabled: bool = True
    timeout_seconds: int = 30


class N8NWorkflowMapping(BaseModel):
    """Maps ElohimOS workflow stage to n8n workflow"""
    elohim_workflow_id: str
    elohim_stage_id: str
    n8n_workflow_id: str
    n8n_webhook_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# N8N CLIENT
# ============================================

class N8NClient:
    """Client for n8n REST API"""

    def __init__(self, config: N8NConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    'X-N8N-API-KEY': self.config.api_key,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            )
        return self.session

    async def close(self) -> None:
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()

    # ============================================
    # WORKFLOW OPERATIONS
    # ============================================

    async def list_workflows(self, use_cache_fallback: bool = True) -> Dict[str, Any]:
        """
        List all n8n workflows with offline fallback.

        Tier 10.5: Returns cached data when n8n is unreachable.

        Args:
            use_cache_fallback: If True, return cached data on failure

        Returns:
            Dict with keys:
            - workflows: List of workflow dicts
            - stale: True if data is from cache (n8n unreachable)
            - cached_at: ISO timestamp if stale, else None
        """
        session = await self._get_session()
        url = f"{self.config.base_url}/api/v1/workflows"
        cache = get_n8n_cache()

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                workflows = data.get('data', [])

                # Cache successful result
                cache.cache_workflows(workflows)

                return {
                    'workflows': workflows,
                    'stale': False,
                    'cached_at': None
                }
        except Exception as e:
            logger.error(f"Failed to list n8n workflows: {e}")

            if use_cache_fallback:
                cached_workflows, cached_at = cache.get_cached_workflows()
                if cached_workflows:
                    logger.warning(f"⚠️  Using cached n8n workflows (from {cached_at})")
                    return {
                        'workflows': cached_workflows,
                        'stale': True,
                        'cached_at': cached_at.isoformat() if cached_at else None
                    }

            raise

    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get specific n8n workflow"""
        session = await self._get_session()
        url = f"{self.config.base_url}/api/v1/workflows/{workflow_id}"

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to get n8n workflow {workflow_id}: {e}")
            raise

    async def create_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new n8n workflow"""
        session = await self._get_session()
        url = f"{self.config.base_url}/api/v1/workflows"

        try:
            async with session.post(url, json=workflow_data) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to create n8n workflow: {e}")
            raise

    async def execute_workflow(
        self,
        workflow_id: str,
        data: Dict[str, Any],
        queue_on_failure: bool = True
    ) -> Dict[str, Any]:
        """
        Execute n8n workflow programmatically with offline queue.

        Tier 10.5: Queues execution for later retry if n8n is unreachable.

        Args:
            workflow_id: ID of workflow to execute
            data: Input data for workflow
            queue_on_failure: If True, queue execution when n8n unreachable

        Returns:
            Dict with execution result or queue status:
            - On success: Full execution response from n8n
            - On queued: {'queued': True, 'queue_id': '...', 'message': '...'}
        """
        session = await self._get_session()
        url = f"{self.config.base_url}/api/v1/workflows/{workflow_id}/execute"

        try:
            async with session.post(url, json=data) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to execute n8n workflow {workflow_id}: {e}")

            if queue_on_failure:
                cache = get_n8n_cache()
                queue_id = cache.queue_execution(workflow_id, data)
                logger.warning(f"⚠️  n8n unreachable, queued execution {queue_id}")
                return {
                    'queued': True,
                    'queue_id': queue_id,
                    'message': 'n8n unreachable, execution queued for later retry'
                }

            raise

    async def retry_queued_executions(self) -> Dict[str, Any]:
        """
        Retry queued executions.

        Tier 10.5: Call this when n8n becomes available again.

        Returns:
            Dict with retry results:
            - succeeded: Number of successful retries
            - failed: Number of failed retries
            - remaining: Number still in queue
        """
        cache = get_n8n_cache()
        pending = cache.get_pending_executions(limit=10)

        succeeded = 0
        failed = 0

        for item in pending:
            try:
                # Try to execute without queueing again
                await self.execute_workflow(
                    item['workflow_id'],
                    item['data'],
                    queue_on_failure=False
                )
                cache.remove_from_queue(item['queue_id'])
                succeeded += 1
                logger.info(f"✅ Retried queued execution {item['queue_id']}")
            except Exception as e:
                cache.mark_retry_failed(item['queue_id'], str(e))
                failed += 1
                logger.warning(f"⚠️  Retry failed for {item['queue_id']}: {e}")

        remaining = len(cache.get_pending_executions(limit=100))

        return {
            'succeeded': succeeded,
            'failed': failed,
            'remaining': remaining
        }

    async def trigger_webhook(
        self,
        webhook_url: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Trigger n8n workflow via webhook"""
        session = await self._get_session()

        try:
            async with session.post(webhook_url, json=data) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to trigger n8n webhook: {e}")
            raise

    # ============================================
    # EXECUTION MONITORING
    # ============================================

    async def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """Get execution status and results"""
        session = await self._get_session()
        url = f"{self.config.base_url}/api/v1/executions/{execution_id}"

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to get execution {execution_id}: {e}")
            raise


__all__ = [
    "N8NConfig",
    "N8NWorkflowMapping",
    "N8NClient",
]
