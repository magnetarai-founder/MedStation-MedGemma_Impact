"""Backward Compatibility Shim - use api.automation.n8n instead."""

from api.automation.n8n.types import (
    N8NConfigRequest,
    ExportStageRequest,
    N8NWebhookRequest,
)

__all__ = ["N8NConfigRequest", "ExportStageRequest", "N8NWebhookRequest"]
