"""
n8n Workflow Converter

Converts between ElohimOS and n8n workflow formats.

Supports bidirectional conversion:
- elohim_to_n8n: Export ElohimOS workflow stage to n8n
- n8n_to_elohim_stage: Import n8n workflow as automation stage

Extracted from n8n_integration.py during P2 decomposition.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


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


__all__ = [
    "N8NWorkflowConverter",
]
