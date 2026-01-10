"""
n8n Integration Service
Handles integration with n8n for hybrid human + automation workflows

OFFLINE FALLBACK (Tier 10.5):
- Caches last known workflow list
- Returns cached list with stale indicator when n8n unreachable
- Queues workflow executions when offline for later retry

Extracted modules (P2 decomposition):
- n8n_cache.py: N8NOfflineCache for offline support
- n8n_client.py: N8NClient and config models
- n8n_converter.py: N8NWorkflowConverter for format conversion
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Re-export from extracted modules for backward compatibility
from .n8n_cache import (
    N8NOfflineCache,
    get_n8n_cache,
)
from .n8n_client import (
    N8NConfig,
    N8NWorkflowMapping,
    N8NClient,
)
from .n8n_converter import (
    N8NWorkflowConverter,
)


# ============================================
# N8N INTEGRATION SERVICE
# ============================================

class N8NIntegrationService:
    """Main service for n8n integration"""

    def __init__(self, config: N8NConfig):
        self.config = config
        self.client = N8NClient(config)
        self.mappings: Dict[str, N8NWorkflowMapping] = {}

    async def close(self) -> None:
        """Cleanup resources"""
        await self.client.close()

    async def export_stage_to_n8n(
        self,
        elohim_workflow: Dict[str, Any],
        stage_id: str
    ) -> str:
        """
        Export ElohimOS workflow stage to n8n

        Returns:
            n8n workflow ID
        """
        if not self.config.enabled:
            raise ValueError("n8n integration is disabled")

        # Convert to n8n format
        n8n_workflow = N8NWorkflowConverter.elohim_to_n8n(elohim_workflow, stage_id)

        # Create in n8n
        result = await self.client.create_workflow(n8n_workflow)
        n8n_workflow_id = result.get('id')

        # Store mapping
        mapping = N8NWorkflowMapping(
            elohim_workflow_id=elohim_workflow['id'],
            elohim_stage_id=stage_id,
            n8n_workflow_id=n8n_workflow_id,
            n8n_webhook_url=f"{self.config.base_url}/webhook/{n8n_workflow.get('nodes', [{}])[0].get('parameters', {}).get('path', '')}"
        )
        self.mappings[f"{elohim_workflow['id']}:{stage_id}"] = mapping

        logger.info(f"✅ Exported stage {stage_id} to n8n workflow {n8n_workflow_id}")

        return n8n_workflow_id

    async def execute_automation_stage(
        self,
        work_item: Dict[str, Any],
        stage: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute automation stage via n8n

        Returns:
            Automation results
        """
        if not self.config.enabled:
            raise ValueError("n8n integration is disabled")

        automation_config = stage.get('automation', {})
        webhook_url = automation_config.get('webhook_url')

        if not webhook_url:
            # Try to find mapping
            mapping_key = f"{work_item['workflow_id']}:{stage['id']}"
            mapping = self.mappings.get(mapping_key)

            if mapping and mapping.n8n_webhook_url:
                webhook_url = mapping.n8n_webhook_url
            else:
                raise ValueError(f"No webhook URL configured for stage {stage['id']}")

        # Trigger n8n workflow
        payload = {
            "work_item_id": work_item['id'],
            "workflow_id": work_item['workflow_id'],
            "stage_id": stage['id'],
            "data": work_item['data'],
            "metadata": {
                "created_at": work_item.get('created_at'),
                "priority": work_item.get('priority')
            }
        }

        result = await self.client.trigger_webhook(webhook_url, payload)

        logger.info(f"✅ Executed n8n automation for work item {work_item['id']}")

        return result


# ============================================
# GLOBAL INSTANCE
# ============================================

_n8n_service: Optional[N8NIntegrationService] = None


def init_n8n_service(config: N8NConfig) -> N8NIntegrationService:
    """Initialize n8n integration service"""
    global _n8n_service

    _n8n_service = N8NIntegrationService(config)
    logger.info(f"🔌 n8n integration initialized: {config.base_url}")

    return _n8n_service


def get_n8n_service() -> Optional[N8NIntegrationService]:
    """Get n8n integration service instance"""
    return _n8n_service


__all__ = [
    # Re-exported from n8n_cache
    "N8NOfflineCache",
    "get_n8n_cache",
    # Re-exported from n8n_client
    "N8NConfig",
    "N8NWorkflowMapping",
    "N8NClient",
    # Re-exported from n8n_converter
    "N8NWorkflowConverter",
    # This module
    "N8NIntegrationService",
    "init_n8n_service",
    "get_n8n_service",
]
