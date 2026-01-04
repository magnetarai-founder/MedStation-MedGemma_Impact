"""
n8n Integration REST API
Endpoints for managing n8n integration
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime, UTC
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
    from .workflow_storage import get_workflow_storage
except ImportError:
    from api.n8n_integration import (
        N8NConfig,
        N8NIntegrationService,
        init_n8n_service,
        get_n8n_service
    )
    from api.workflow_models import WorkItem
    from api.workflow_orchestrator import WorkflowOrchestrator
    from api.workflow_storage import get_workflow_storage

logger = logging.getLogger(__name__)

from fastapi import Depends
from api.auth_middleware import get_current_user

# Dependency to check if n8n is enabled
def require_n8n_enabled() -> N8NIntegrationService:
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
async def configure_n8n(config: N8NConfigRequest) -> Dict[str, Any]:
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
async def get_n8n_config() -> Dict[str, Any]:
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
async def list_n8n_workflows(service: N8NIntegrationService = Depends(require_n8n_enabled)) -> Dict[str, Any]:
    """List all n8n workflows"""
    try:
        workflows = await service.client.list_workflows()
        return {"workflows": workflows}
    except Exception as e:
        logger.error(f"Failed to list n8n workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export-stage")
async def export_stage_to_n8n(
    request: ExportStageRequest,
    current_user: dict = Depends(get_current_user),
    service: N8NIntegrationService = Depends(require_n8n_enabled)
) -> Dict[str, Any]:
    """
    Export ElohimOS workflow stage to n8n

    Args:
        request: Export request with workflow and stage IDs
        current_user: Authenticated user from JWT

    Returns:
        n8n workflow ID and webhook URL
    """
    try:
        # Fetch workflow from storage using authenticated user
        storage = get_workflow_storage()
        user_id = current_user['user_id']

        workflow = storage.get_workflow(
            workflow_id=request.workflow_id,
            user_id=user_id
        )

        if not workflow:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow not found: {request.workflow_id}"
            )

        # Verify the requested stage exists in this workflow
        stage_ids = [stage.id for stage in workflow.stages]
        if request.stage_id not in stage_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Stage '{request.stage_id}' not found in workflow '{workflow.name}'"
            )

        # Convert Pydantic model to dict for n8n export
        workflow_data = workflow.model_dump()

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
            "webhook_url": mapping.n8n_webhook_url if mapping else None,
            "workflow_name": workflow.name,
            "stage_name": next(
                (s.name for s in workflow.stages if s.id == request.stage_id),
                None
            )
        }

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Failed to export stage to n8n: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# WEBHOOK HANDLERS
# ============================================

@router.post("/webhook/result")
async def handle_n8n_webhook(webhook_data: N8NWebhookRequest) -> Dict[str, Any]:
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

        # Get orchestrator to update work item
        try:
            from api.services.workflow_orchestrator import WorkflowOrchestrator
            from api.services.workflow_storage import get_workflow_storage
        except ImportError:
            from services.workflow_orchestrator import WorkflowOrchestrator
            from services.workflow_storage import get_workflow_storage

        storage = get_workflow_storage()
        orchestrator = WorkflowOrchestrator(storage=storage)

        # Find the work item - we need to look up by ID
        # The webhook doesn't include user_id, so we search across all
        work_item = None
        if storage:
            # Try to find work item by ID (admin search)
            work_item = storage.get_work_item_by_id(work_item_id)

        if not work_item:
            logger.warning(f"Work item not found: {work_item_id}")
            return {
                "status": "error",
                "message": f"Work item not found: {work_item_id}"
            }

        user_id = work_item.created_by  # Use creator as owner

        if webhook_data.status == "completed":
            logger.info(f"✅ n8n automation completed for {work_item_id}")

            # Update work item with results
            work_item.data['n8n_results'] = webhook_data.results
            work_item.data['n8n_execution'] = {
                'status': 'completed',
                'completed_at': datetime.now(UTC).isoformat()
            }

            # Complete the current stage and advance
            try:
                orchestrator.complete_stage(
                    work_item_id=work_item_id,
                    user_id=user_id,
                    stage_data=webhook_data.results,
                    notes="Automation completed via n8n"
                )
                logger.info(f"✅ Work item {work_item_id} advanced to next stage")
            except Exception as e:
                logger.error(f"Failed to advance work item: {e}")

        elif webhook_data.status == "failed":
            logger.error(f"❌ n8n automation failed for {work_item_id}: {webhook_data.error}")

            # Update work item with error
            work_item.data['n8n_execution'] = {
                'status': 'failed',
                'error': webhook_data.error,
                'failed_at': datetime.now(UTC).isoformat()
            }

            # Mark work item as failed
            from api.workflow_models import WorkItemStatus
            work_item.status = WorkItemStatus.FAILED
            work_item.updated_at = datetime.now(UTC)

            if storage:
                storage.save_work_item(work_item, user_id=user_id)

        return {
            "status": "received",
            "work_item_id": work_item_id,
            "processed": True
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
) -> Dict[str, Any]:
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
async def get_stage_mappings(service: N8NIntegrationService = Depends(require_n8n_enabled)) -> Dict[str, Any]:
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
async def n8n_health_check() -> Dict[str, Any]:
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
