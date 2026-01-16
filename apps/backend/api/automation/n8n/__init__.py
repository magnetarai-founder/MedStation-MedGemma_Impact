"""
N8N integration module.

Provides:
- N8NIntegrationService: Main service for N8N workflow integration
- N8NClient: Client for N8N API
- N8NOfflineCache: Offline caching for N8N workflows
- N8NWorkflowConverter: Convert workflows to N8N format
- router: FastAPI router for N8N endpoints
"""

from api.automation.n8n.integration import (
    N8NIntegrationService,
    init_n8n_service,
    get_n8n_service,
)
from api.automation.n8n.client import N8NClient, N8NConfig, N8NWorkflowMapping
from api.automation.n8n.cache import N8NOfflineCache, get_n8n_cache
from api.automation.n8n.converter import N8NWorkflowConverter
from api.automation.n8n.router import router
from api.automation.n8n.types import (
    N8NConfigRequest,
    ExportStageRequest,
    N8NWebhookRequest,
)

__all__ = [
    "N8NIntegrationService",
    "init_n8n_service",
    "get_n8n_service",
    "N8NClient",
    "N8NConfig",
    "N8NWorkflowMapping",
    "N8NOfflineCache",
    "get_n8n_cache",
    "N8NWorkflowConverter",
    "router",
    "N8NConfigRequest",
    "ExportStageRequest",
    "N8NWebhookRequest",
]
