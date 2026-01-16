"""Backward Compatibility Shim - use api.automation.n8n instead."""

from api.automation.n8n.integration import (
    N8NIntegrationService,
    init_n8n_service,
    get_n8n_service,
    logger,
    # Re-exported from client/cache modules
    N8NConfig,
    N8NWorkflowMapping,
    N8NClient,
    N8NOfflineCache,
    get_n8n_cache,
    N8NWorkflowConverter,
)

__all__ = [
    "N8NIntegrationService",
    "init_n8n_service",
    "get_n8n_service",
    "logger",
    "N8NConfig",
    "N8NWorkflowMapping",
    "N8NClient",
    "N8NOfflineCache",
    "get_n8n_cache",
    "N8NWorkflowConverter",
]
