"""
HuggingFace GGUF Model Routes

Endpoints for:
- Listing available GGUF models from registry
- Listing downloaded models
- Downloading models with streaming progress
- Deleting downloaded models
- Hardware validation
"""

import logging
import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode
from api.errors import http_500
from api.auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/huggingface", tags=["huggingface"])


# ==============================================================================
# Response Models
# ==============================================================================

class GGUFModelResponse(BaseModel):
    """GGUF model info for API responses"""
    id: str
    name: str
    repo_id: str
    filename: str
    size_gb: float
    parameter_count: str
    quantization: str
    context_length: int
    min_vram_gb: float
    recommended_vram_gb: float
    capabilities: List[str]
    description: str
    is_downloaded: bool = False


class DownloadedModelResponse(BaseModel):
    """Downloaded model info"""
    repo_id: str
    filename: str
    path: str
    size_bytes: int
    quantization: Optional[str]
    downloaded_at: str


class HardwareInfoResponse(BaseModel):
    """Hardware info for UI display"""
    platform: str
    is_apple_silicon: bool
    total_memory_gb: float
    available_memory_gb: float
    gpu_name: Optional[str]
    gpu_vram_gb: Optional[float]
    has_metal: bool
    has_cuda: bool
    recommended_quantization: str


class DownloadRequest(BaseModel):
    """Download request body"""
    model_id: str  # Registry model ID (e.g., "medgemma-1.5-4b-q4")


# ==============================================================================
# Registry Endpoints
# ==============================================================================

@router.get(
    "/models",
    response_model=SuccessResponse[List[GGUFModelResponse]],
    status_code=status.HTTP_200_OK,
    name="huggingface_list_available_models"
)
async def list_available_models(
    capability: Optional[str] = Query(None, description="Filter by capability (medical, code, chat, vision)"),
    recommended_only: bool = Query(False, description="Only show recommended models"),
):
    """
    List available GGUF models from the curated registry

    Returns models with hardware requirements so UI can show compatibility warnings.
    """
    from api.services.huggingface import GGUFRegistry, get_gguf_registry
    from api.services.huggingface.storage import get_huggingface_storage
    from api.services.model_source.types import ModelCapability

    try:
        registry = get_gguf_registry()
        storage = get_huggingface_storage()

        # Get models based on filters
        if recommended_only:
            models = registry.list_recommended()
        elif capability:
            try:
                cap = ModelCapability(capability)
                models = registry.list_by_capability(cap)
            except ValueError:
                models = registry.list_all_models()
        else:
            models = registry.list_all_models()

        # Convert to response format with download status
        result = []
        for model in models:
            is_downloaded = storage.is_model_downloaded(model.repo_id, model.filename)
            result.append(GGUFModelResponse(
                id=model.id,
                name=model.name,
                repo_id=model.repo_id,
                filename=model.filename,
                size_gb=model.size_gb,
                parameter_count=model.parameter_count,
                quantization=model.quantization.value,
                context_length=model.context_length,
                min_vram_gb=model.min_vram_gb,
                recommended_vram_gb=model.recommended_vram_gb,
                capabilities=[c.value for c in model.capabilities],
                description=model.description,
                is_downloaded=is_downloaded,
            ))

        return SuccessResponse(
            data=result,
            message=f"Found {len(result)} available GGUF models"
        )

    except Exception as e:
        logger.error(f"Failed to list available models: {e}", exc_info=True)
        raise http_500("Failed to list available models")


@router.get(
    "/models/medical",
    response_model=SuccessResponse[List[GGUFModelResponse]],
    status_code=status.HTTP_200_OK,
    name="huggingface_list_medical_models"
)
async def list_medical_models():
    """
    List medical-specialized GGUF models (MedGemma, etc.)

    Shortcut endpoint for the Kaggle competition focus.
    """
    from api.services.huggingface import GGUFRegistry, get_gguf_registry
    from api.services.huggingface.storage import get_huggingface_storage

    try:
        registry = get_gguf_registry()
        storage = get_huggingface_storage()

        models = registry.list_medical_models()

        result = []
        for model in models:
            is_downloaded = storage.is_model_downloaded(model.repo_id, model.filename)
            result.append(GGUFModelResponse(
                id=model.id,
                name=model.name,
                repo_id=model.repo_id,
                filename=model.filename,
                size_gb=model.size_gb,
                parameter_count=model.parameter_count,
                quantization=model.quantization.value,
                context_length=model.context_length,
                min_vram_gb=model.min_vram_gb,
                recommended_vram_gb=model.recommended_vram_gb,
                capabilities=[c.value for c in model.capabilities],
                description=model.description,
                is_downloaded=is_downloaded,
            ))

        return SuccessResponse(
            data=result,
            message=f"Found {len(result)} medical models"
        )

    except Exception as e:
        logger.error(f"Failed to list medical models: {e}", exc_info=True)
        raise http_500("Failed to list medical models")


# ==============================================================================
# Downloaded Models Endpoints
# ==============================================================================

@router.get(
    "/models/local",
    response_model=SuccessResponse[List[DownloadedModelResponse]],
    status_code=status.HTTP_200_OK,
    name="huggingface_list_local_models"
)
async def list_local_models(
    current_user: dict = Depends(get_current_user)
):
    """List all locally downloaded GGUF models"""
    from api.services.huggingface.storage import get_huggingface_storage

    try:
        storage = get_huggingface_storage()
        models = storage.list_downloaded_models()

        result = [
            DownloadedModelResponse(
                repo_id=m["repo_id"],
                filename=m["filename"],
                path=m["path"],
                size_bytes=m.get("actual_size", m.get("size_bytes", 0)),
                quantization=m.get("quantization"),
                downloaded_at=m.get("downloaded_at", ""),
            )
            for m in models
            if m.get("exists", False)
        ]

        return SuccessResponse(
            data=result,
            message=f"Found {len(result)} downloaded models"
        )

    except Exception as e:
        logger.error(f"Failed to list local models: {e}", exc_info=True)
        raise http_500("Failed to list local models")


@router.get(
    "/storage",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="huggingface_storage_summary"
)
async def get_storage_summary(
    current_user: dict = Depends(get_current_user)
):
    """Get storage usage summary for downloaded models"""
    from api.services.huggingface.storage import get_huggingface_storage

    try:
        storage = get_huggingface_storage()
        summary = storage.get_storage_summary()

        return SuccessResponse(
            data=summary,
            message="Storage summary retrieved"
        )

    except Exception as e:
        logger.error(f"Failed to get storage summary: {e}", exc_info=True)
        raise http_500("Failed to get storage summary")


# ==============================================================================
# Download Endpoints
# ==============================================================================

@router.post(
    "/models/download",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    name="huggingface_download_model"
)
async def download_model(
    request: DownloadRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Download a GGUF model from HuggingFace Hub

    Returns a Server-Sent Events stream with progress updates:
    - {"status": "starting", "progress": 0, "message": "..."}
    - {"status": "downloading", "progress": 45.2, "speed_bps": 12345678, ...}
    - {"status": "completed", "progress": 100, "message": "..."}
    - {"status": "failed", "error": "..."}
    """
    from api.services.huggingface import GGUFRegistry, get_gguf_registry
    from api.services.huggingface.downloader import get_huggingface_downloader

    # Validate model exists in registry
    registry = get_gguf_registry()
    model = registry.get_model(request.model_id)

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code=ErrorCode.NOT_FOUND,
                message=f"Model not found in registry: {request.model_id}"
            ).model_dump()
        )

    async def event_stream():
        """Stream download progress as Server-Sent Events"""
        downloader = get_huggingface_downloader()

        try:
            async for progress in downloader.download_model(
                repo_id=model.repo_id,
                filename=model.filename
            ):
                # Convert to dict for JSON serialization
                data = {
                    "job_id": progress.job_id,
                    "status": progress.status,
                    "progress": progress.progress,
                    "downloaded_bytes": progress.downloaded_bytes,
                    "total_bytes": progress.total_bytes,
                    "speed_bps": progress.speed_bps,
                    "eta_seconds": progress.eta_seconds,
                    "message": progress.message,
                    "model_id": request.model_id,
                }
                if progress.error:
                    data["error"] = progress.error

                yield f"data: {json.dumps(data)}\n\n"

        except Exception as e:
            logger.error(f"Error in download stream: {e}", exc_info=True)
            error_data = {
                "status": "failed",
                "progress": 0,
                "message": str(e),
                "error": str(e),
                "model_id": request.model_id,
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ==============================================================================
# Download Control Endpoints (Pause/Resume/Cancel)
# ==============================================================================

@router.get(
    "/downloads",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="huggingface_list_downloads"
)
async def list_active_downloads(
    current_user: dict = Depends(get_current_user)
):
    """List all active and paused downloads"""
    from api.services.huggingface.downloader import get_huggingface_downloader

    try:
        downloader = get_huggingface_downloader()
        active = downloader.get_active_downloads()
        paused = downloader.get_paused_downloads()

        return SuccessResponse(
            data={
                "active": active,
                "paused": paused,
                "total": len(active) + len(paused)
            },
            message=f"Found {len(active)} active, {len(paused)} paused downloads"
        )

    except Exception as e:
        logger.error(f"Failed to list downloads: {e}", exc_info=True)
        raise http_500("Failed to list downloads")


@router.post(
    "/downloads/{job_id}/pause",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="huggingface_pause_download"
)
async def pause_download(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Pause an active download

    The partial file is preserved for later resumption.
    """
    from api.services.huggingface.downloader import get_huggingface_downloader

    try:
        downloader = get_huggingface_downloader()
        paused = await downloader.pause_download(job_id)

        if paused:
            return SuccessResponse(
                data={"job_id": job_id, "paused": True},
                message=f"Download paused: {job_id}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Download not found or not pauseable: {job_id}"
                ).model_dump()
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause download: {e}", exc_info=True)
        raise http_500("Failed to pause download")


@router.post(
    "/downloads/{job_id}/resume",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="huggingface_resume_download"
)
async def resume_download(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Resume a paused download

    Returns info needed to restart the download via the download endpoint.
    """
    from api.services.huggingface.downloader import get_huggingface_downloader

    try:
        downloader = get_huggingface_downloader()
        resume_info = await downloader.resume_download(job_id)

        if resume_info:
            repo_id, filename = resume_info.split(":", 1)
            return SuccessResponse(
                data={
                    "job_id": job_id,
                    "resumed": True,
                    "repo_id": repo_id,
                    "filename": filename,
                    "message": "Download ready to resume. Call the download endpoint to continue."
                },
                message=f"Download ready to resume: {job_id}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Download not found or not paused: {job_id}"
                ).model_dump()
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume download: {e}", exc_info=True)
        raise http_500("Failed to resume download")


@router.delete(
    "/downloads/{job_id}",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="huggingface_cancel_download"
)
async def cancel_download(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Cancel an active or paused download"""
    from api.services.huggingface.downloader import get_huggingface_downloader

    try:
        downloader = get_huggingface_downloader()
        canceled = await downloader.cancel_download(job_id)

        if canceled:
            return SuccessResponse(
                data={"job_id": job_id, "canceled": True},
                message=f"Download canceled: {job_id}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Download not found: {job_id}"
                ).model_dump()
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel download: {e}", exc_info=True)
        raise http_500("Failed to cancel download")


# ==============================================================================
# Model Management Endpoints
# ==============================================================================

@router.delete(
    "/models/{model_id}",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="huggingface_delete_model"
)
async def delete_model(
    model_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a downloaded GGUF model"""
    from api.services.huggingface import GGUFRegistry, get_gguf_registry
    from api.services.huggingface.storage import get_huggingface_storage

    try:
        registry = get_gguf_registry()
        storage = get_huggingface_storage()

        # Get model info from registry
        model = registry.get_model(model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Model not found: {model_id}"
                ).model_dump()
            )

        # Delete the model
        deleted = storage.unregister_model(model.repo_id, model.filename)

        if deleted:
            return SuccessResponse(
                data={"model_id": model_id, "deleted": True},
                message=f"Model '{model_id}' deleted successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Model not found locally: {model_id}"
                ).model_dump()
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete model: {e}", exc_info=True)
        raise http_500("Failed to delete model")


# ==============================================================================
# Hardware Endpoints
# ==============================================================================

@router.get(
    "/hardware",
    response_model=SuccessResponse[HardwareInfoResponse],
    status_code=status.HTTP_200_OK,
    name="huggingface_hardware_info"
)
async def get_hardware_info():
    """
    Get hardware information for model compatibility (public endpoint)

    Returns GPU capabilities and recommended quantization level.
    """
    from api.services.llamacpp.hardware import get_hardware_info, recommend_quantization

    try:
        hardware = get_hardware_info()
        recommended = recommend_quantization(hardware)

        return SuccessResponse(
            data=HardwareInfoResponse(
                platform=hardware.platform,
                is_apple_silicon=hardware.is_apple_silicon,
                total_memory_gb=round(hardware.total_memory_gb, 1),
                available_memory_gb=round(hardware.available_memory_gb, 1),
                gpu_name=hardware.gpu_name,
                gpu_vram_gb=round(hardware.gpu_vram_gb, 1) if hardware.gpu_vram_gb else None,
                has_metal=hardware.has_metal,
                has_cuda=hardware.has_cuda,
                recommended_quantization=recommended,
            ),
            message="Hardware info retrieved"
        )

    except Exception as e:
        logger.error(f"Failed to get hardware info: {e}", exc_info=True)
        raise http_500("Failed to get hardware info")


@router.post(
    "/models/{model_id}/validate",
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    name="huggingface_validate_model"
)
async def validate_model_compatibility(
    model_id: str,
):
    """
    Validate if a model will fit in available VRAM (public endpoint)

    Returns whether the model can run and any warnings.
    """
    from api.services.huggingface import GGUFRegistry, get_gguf_registry
    from api.services.llamacpp.hardware import get_hardware_info, validate_model_fits

    try:
        registry = get_gguf_registry()
        model = registry.get_model(model_id)

        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code=ErrorCode.NOT_FOUND,
                    message=f"Model not found: {model_id}"
                ).model_dump()
            )

        hardware = get_hardware_info()
        fits, message = validate_model_fits(model.size_gb, model.min_vram_gb, hardware)

        return SuccessResponse(
            data={
                "model_id": model_id,
                "compatible": fits,
                "message": message,
                "model_size_gb": model.size_gb,
                "min_vram_gb": model.min_vram_gb,
                "available_vram_gb": round(hardware.gpu_vram_gb, 1) if hardware.gpu_vram_gb else None,
            },
            message="Validation complete"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate model: {e}", exc_info=True)
        raise http_500("Failed to validate model")
