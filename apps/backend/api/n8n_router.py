"""
n8n Integration REST API
Endpoints for managing n8n integration
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging

try:
    from .n8n_integration import (
        N8NConfig,
        N8NIntegrationService,
        init_n8n_service,
        get_n8n_service
    )
    from .workflow_models import WorkItem
    from .workflow_orchestrator import WorkflowOrchestrator
except ImportError:
    from n8n_integration import (
        N8NConfig,
        N8NIntegrationService,
        init_n8n_service,
        get_n8n_service
    )
    from workflow_models import WorkItem
    from workflow_orchestrator import WorkflowOrchestrator

logger = logging.getLogger(__name__)

from fastapi import Depends
from auth_middleware import get_current_user

# Dependency to check if n8n is enabled
def require_n8n_enabled():
    """Dependency that raises 404 if n8n is not configured/enabled"""
    service = get_n8n_service()
    if not service or not service.config.enabled:
        raise HTTPException(
            status_code=404,
            detail="n8n integration not configured or disabled"
        )
    return service

router = APIRouter(
    prefix="/api/v1/n8n",
    tags=["n8n"],
    dependencies=[Depends(get_current_user)]  # Require auth
)

# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

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


# ============================================
# CONFIGURATION
# ============================================

@router.post("/configure")
async def configure_n8n(config: N8NConfigRequest):
    """
    Configure n8n integration

    Args:
        config: n8n configuration

    Returns:
        Configuration status
    """
    try:
        n8n_config = N8NConfig(
            base_url=config.base_url,
            api_key=config.api_key,
            enabled=config.enabled
        )

        service = init_n8n_service(n8n_config)

        # Test connection
        try:
            await service.client.list_workflows()
            logger.info("✅ n8n connection test successful")
        except Exception as e:
            logger.error(f"n8n connection test failed: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to connect to n8n: {str(e)}"
            )

        return {
            "status": "configured",
            "base_url": config.base_url,
            "enabled": config.enabled
        }

    except Exception as e:
        logger.error(f"Failed to configure n8n: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_n8n_config():
    """Get current n8n configuration"""
    service = get_n8n_service()

    if not service:
        return {
            "configured": False,
            "enabled": False
        }

    return {
        "configured": True,
        "enabled": service.config.enabled,
        "base_url": service.config.base_url
    }


# ============================================
# WORKFLOW OPERATIONS
# ============================================

@router.get("/workflows")
async def list_n8n_workflows(service: N8NIntegrationService = Depends(require_n8n_enabled)):
    """List all n8n workflows"""
    try:
        workflows = await service.client.list_workflows()
        return {"workflows": workflows}
    except Exception as e:
        logger.error(f"Failed to list n8n workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export-stage")
async def export_stage_to_n8n(request: ExportStageRequest, service: N8NIntegrationService = Depends(require_n8n_enabled)):
    """
    Export ElohimOS workflow stage to n8n

    Args:
        request: Export request with workflow and stage IDs

    Returns:
        n8n workflow ID and webhook URL
    """

    # Get workflow (TODO: inject orchestrator properly)
    # For now, we'll accept workflow data in request
    try:
        # Mock workflow data for now
        workflow_data = {
            "id": request.workflow_id,
            "name": "Mock Workflow",
            "stages": [
                {
                    "id": request.stage_id,
                    "name": "Automation Stage",
                    "stage_type": "automation"
                }
            ]
        }

        n8n_workflow_id = await service.export_stage_to_n8n(
            workflow_data,
            request.stage_id
        )

        # Get mapping
        mapping_key = f"{request.workflow_id}:{request.stage_id}"
        mapping = service.mappings.get(mapping_key)

        return {
            "status": "exported",
            "n8n_workflow_id": n8n_workflow_id,
            "webhook_url": mapping.n8n_webhook_url if mapping else None
        }

    except Exception as e:
        logger.error(f"Failed to export stage to n8n: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# WEBHOOK HANDLERS
# ============================================

@router.post("/webhook/result")
async def handle_n8n_webhook(webhook_data: N8NWebhookRequest):
    """
    Receive results from n8n workflow execution

    This endpoint is called by n8n when automation completes

    Args:
        webhook_data: Results from n8n

    Returns:
        Acknowledgement
    """
    try:
        work_item_id = webhook_data.work_item_id

        logger.info(f"📨 Received n8n webhook for work item {work_item_id}")

        # TODO: Update work item with results
        # For now, just log
        if webhook_data.status == "completed":
            logger.info(f"✅ n8n automation completed for {work_item_id}")
            # orchestrator.complete_stage(work_item_id, stage_data=webhook_data.results)
        elif webhook_data.status == "failed":
            logger.error(f"❌ n8n automation failed for {work_item_id}: {webhook_data.error}")

        return {
            "status": "received",
            "work_item_id": work_item_id
        }

    except Exception as e:
        logger.error(f"Failed to process n8n webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# WORKFLOW EXECUTION
# ============================================

@router.post("/execute/{n8n_workflow_id}")
async def execute_n8n_workflow(
    n8n_workflow_id: str,
    data: Dict[str, Any] = Body(...),
    service: N8NIntegrationService = Depends(require_n8n_enabled)
):
    """
    Execute n8n workflow programmatically

    Args:
        n8n_workflow_id: n8n workflow ID
        data: Input data for workflow

    Returns:
        Execution results
    """
    try:
        result = await service.client.execute_workflow(n8n_workflow_id, data)

        return {
            "status": "executed",
            "result": result
        }

    except Exception as e:
        logger.error(f"Failed to execute n8n workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# MAPPINGS
# ============================================

@router.get("/mappings")
async def get_stage_mappings(service: N8NIntegrationService = Depends(require_n8n_enabled)):
    """Get all ElohimOS <-> n8n stage mappings"""
    mappings = [
        {
            "elohim_workflow_id": m.elohim_workflow_id,
            "elohim_stage_id": m.elohim_stage_id,
            "n8n_workflow_id": m.n8n_workflow_id,
            "webhook_url": m.n8n_webhook_url,
            "created_at": m.created_at.isoformat()
        }
        for m in service.mappings.values()
    ]

    return {"mappings": mappings}


# ============================================
# HEALTH CHECK
# ============================================

@router.get("/health")
async def n8n_health_check():
    """Check n8n integration health"""
    service = get_n8n_service()

    if not service:
        return {
            "status": "not_configured",
            "configured": False
        }

    # Try to connect
    try:
        workflows = await service.client.list_workflows()
        return {
            "status": "healthy",
            "configured": True,
            "enabled": service.config.enabled,
            "n8n_workflows": len(workflows)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "configured": True,
            "enabled": service.config.enabled,
            "error": str(e)
        }
