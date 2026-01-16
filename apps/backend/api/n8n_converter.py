"""Backward Compatibility Shim - use api.automation.n8n instead."""

from api.automation.n8n.converter import N8NWorkflowConverter, logger

__all__ = ["N8NWorkflowConverter", "logger"]
