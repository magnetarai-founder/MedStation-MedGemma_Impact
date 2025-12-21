"""
n8n Integration Service
Handles integration with n8n for hybrid human + automation workflows
"""

import aiohttp
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import json

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

    async def list_workflows(self) -> List[Dict[str, Any]]:
        """List all n8n workflows"""
        session = await self._get_session()
        url = f"{self.config.base_url}/api/v1/workflows"

        try:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get('data', [])
        except Exception as e:
            logger.error(f"Failed to list n8n workflows: {e}")
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
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute n8n workflow programmatically"""
        session = await self._get_session()
        url = f"{self.config.base_url}/api/v1/workflows/{workflow_id}/execute"

        try:
            async with session.post(url, json=data) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"Failed to execute n8n workflow {workflow_id}: {e}")
            raise

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


# ============================================
# N8N WORKFLOW CONVERTER
# ============================================

class N8NWorkflowConverter:
    """Converts between ElohimOS and n8n workflow formats"""

    @staticmethod
    def elohim_to_n8n(elohim_workflow: Dict[str, Any], stage_id: str) -> Dict[str, Any]:
        """
        Convert ElohimOS workflow stage to n8n workflow

        Creates an n8n workflow that:
        1. Receives data via webhook
        2. Processes it (custom logic)
        3. Returns results via webhook response
        """
        stage = next(
            (s for s in elohim_workflow.get('stages', []) if s['id'] == stage_id),
            None
        )

        if not stage:
            raise ValueError(f"Stage {stage_id} not found in workflow")

        # Build n8n workflow structure
        n8n_workflow = {
            "name": f"{elohim_workflow['name']} - {stage['name']} (Automation)",
            "nodes": [
                {
                    "parameters": {
                        "httpMethod": "POST",
                        "path": f"elohim/{elohim_workflow['id']}/{stage_id}",
                        "responseMode": "responseNode",
                        "options": {}
                    },
                    "name": "Webhook",
                    "type": "n8n-nodes-base.webhook",
                    "typeVersion": 1.1,
                    "position": [250, 300],
                    "webhookId": f"elohim_{stage_id}"
                },
                {
                    "parameters": {
                        "jsCode": "// Process work item data\nconst workItem = $input.item.json;\n\n// Custom automation logic here\nconst result = {\n  status: 'completed',\n  data: workItem,\n  timestamp: new Date().toISOString()\n};\n\nreturn result;"
                    },
                    "name": "Process Data",
                    "type": "n8n-nodes-base.code",
                    "typeVersion": 2,
                    "position": [450, 300]
                },
                {
                    "parameters": {
                        "respondWith": "json",
                        "responseBody": "={{ $json }}"
                    },
                    "name": "Respond to Webhook",
                    "type": "n8n-nodes-base.respondToWebhook",
                    "typeVersion": 1,
                    "position": [650, 300]
                }
            ],
            "connections": {
                "Webhook": {
                    "main": [[{"node": "Process Data", "type": "main", "index": 0}]]
                },
                "Process Data": {
                    "main": [[{"node": "Respond to Webhook", "type": "main", "index": 0}]]
                }
            },
            "active": True,
            "settings": {
                "executionOrder": "v1"
            },
            "tags": ["elohimos", "automation", elohim_workflow['id']]
        }

        return n8n_workflow

    @staticmethod
    def n8n_to_elohim_stage(n8n_workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert n8n workflow to ElohimOS automation stage

        Extracts webhook URL and creates automation config
        """
        # Find webhook node
        webhook_node = next(
            (node for node in n8n_workflow.get('nodes', [])
             if node.get('type') == 'n8n-nodes-base.webhook'),
            None
        )

        if not webhook_node:
            raise ValueError("No webhook node found in n8n workflow")

        webhook_path = webhook_node.get('parameters', {}).get('path', '')

        return {
            "stage_type": "automation",
            "automation": {
                "type": "n8n_webhook",
                "n8n_workflow_id": n8n_workflow.get('id'),
                "webhook_path": webhook_path,
                "timeout_seconds": 300
            }
        }


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
