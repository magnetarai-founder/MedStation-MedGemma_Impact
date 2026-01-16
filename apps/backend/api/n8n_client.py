"""Backward Compatibility Shim - use api.automation.n8n instead."""

from api.automation.n8n.client import N8NClient, N8NConfig, N8NWorkflowMapping, logger

__all__ = ["N8NClient", "N8NConfig", "N8NWorkflowMapping", "logger"]
