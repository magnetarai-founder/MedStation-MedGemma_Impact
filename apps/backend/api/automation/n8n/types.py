"""
n8n Types - Request/response models for n8n integration

Extracted from n8n_router.py during P2 decomposition.
Contains:
- N8NConfigRequest (configuration)
- ExportStageRequest (workflow export)
- N8NWebhookRequest (webhook payload)
"""

from pydantic import BaseModel
from typing import Dict, Any, Optional


class N8NConfigRequest(BaseModel):
    """Request to configure n8n"""
    base_url: str
    api_key: str
    enabled: bool = True


class ExportStageRequest(BaseModel):
    """Request to export stage to n8n"""
    workflow_id: str
    stage_id: str


class N8NWebhookRequest(BaseModel):
    """Incoming webhook from n8n"""
    work_item_id: str
    results: Dict[str, Any]
    status: str  # completed, failed, etc.
    error: Optional[str] = None


__all__ = [
    "N8NConfigRequest",
    "ExportStageRequest",
    "N8NWebhookRequest",
]
