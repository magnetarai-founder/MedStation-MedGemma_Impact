"""
Setup Wizard API Routes

Comprehensive first-run setup wizard endpoints that extend
the existing founder_setup routes with full onboarding:

- Ollama detection and installation guidance
- System resource detection
- Model recommendations
- Model downloads with progress
- Hot slot configuration
- Account creation

Integrates with existing founder_setup_wizard.py for
founder password initialization.

Endpoints:
- GET /api/v1/setup/status - Overall setup status
- GET /api/v1/setup/ollama - Check Ollama installation/service
- GET /api/v1/setup/resources - Detect system resources
- GET /api/v1/setup/models/recommendations - Get recommended models
- GET /api/v1/setup/models/installed - List installed models
- POST /api/v1/setup/models/download - Download a model
- POST /api/v1/setup/hot-slots - Configure hot slots
- POST /api/v1/setup/account - Create local account
- POST /api/v1/setup/complete - Mark setup as complete
"""

import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

try:
    from ..services.setup_wizard import get_setup_wizard
    from ..founder_setup_wizard import get_founder_wizard
except ImportError:
    from services.setup_wizard import get_setup_wizard
    from founder_setup_wizard import get_founder_wizard

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/setup", tags=["setup-wizard"])


# ===== Pydantic Models =====

class SetupStatusResponse(BaseModel):
    """Overall setup status"""
    setup_completed: bool
    founder_setup_completed: bool
    founder_password_storage: Optional[str] = None
    is_macos: bool


class OllamaStatusResponse(BaseModel):
    """Ollama installation and service status"""
    installed: bool
    running: bool
    version: Optional[str] = None
    base_url: str
    install_instructions: Dict[str, str]


class SystemResourcesResponse(BaseModel):
    """System resource detection"""
    ram_gb: int
    disk_free_gb: int
    recommended_tier: str
    tier_info: Dict[str, any]


class ModelInfo(BaseModel):
    """Model information"""
    name: str
    display_name: str
    category: str
    size_gb: float
    description: str
    use_cases: List[str]
    recommended_for: str
    performance: Dict[str, any]


class ModelRecommendationsResponse(BaseModel):
    """Model recommendations for a tier"""
    tier: str
    models: List[ModelInfo]
    hot_slot_recommendations: Dict[int, Optional[str]]
    total_size_gb: float


class InstalledModelInfo(BaseModel):
    """Installed model info from Ollama"""
    name: str
    size: int
    modified_at: str


class InstalledModelsResponse(BaseModel):
    """List of installed models"""
    models: List[InstalledModelInfo]


class DownloadModelRequest(BaseModel):
    """Download model request"""
    model_name: str = Field(..., description="Ollama model name (e.g., 'qwen2.5-coder:7b')")


class DownloadModelResponse(BaseModel):
    """Download model response"""
    success: bool
    model_name: str
    message: Optional[str] = None


class ConfigureHotSlotsRequest(BaseModel):
    """Configure hot slots request"""
    slots: Dict[int, Optional[str]] = Field(
        ...,
        description="Mapping of slot number (1-4) to model name (null to clear)"
    )


class ConfigureHotSlotsResponse(BaseModel):
    """Configure hot slots response"""
    success: bool
    message: Optional[str] = None


class CreateAccountRequest(BaseModel):
    """Create local account request"""
    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=8)
    confirm_password: str
    founder_password: Optional[str] = Field(None, description="Optional founder password to initialize")


class CreateAccountResponse(BaseModel):
    """Create account response"""
    success: bool
    user_id: Optional[str] = None
    founder_setup_complete: bool = False
    error: Optional[str] = None


class CompleteSetupResponse(BaseModel):
    """Complete setup response"""
    success: bool
    message: str


# ===== API Endpoints =====

@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status():
    """
    Get overall setup status

    Returns whether the setup wizard has been completed.
    This checks the founder_setup table for completion status.

    Public endpoint - no authentication required.
    """
    try:
        founder_wizard = get_founder_wizard()
        founder_info = founder_wizard.get_setup_info()

        return SetupStatusResponse(
            setup_completed=founder_info["setup_completed"],
            founder_setup_completed=founder_info["setup_completed"],
            founder_password_storage=founder_info.get("password_storage_type"),
            is_macos=founder_info.get("is_macos", False)
        )

    except Exception as e:
        logger.error(f"❌ Failed to get setup status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get setup status")


@router.get("/ollama", response_model=OllamaStatusResponse)
async def check_ollama():
    """
    Check Ollama installation and service status

    Detects:
    - If Ollama binary is installed
    - If Ollama service is running
    - Ollama version
    - Platform-specific installation instructions

    Public endpoint - no authentication required (setup phase).
    """
    try:
        wizard = get_setup_wizard()
        status = await wizard.check_ollama_status()

        return OllamaStatusResponse(**status)

    except Exception as e:
        logger.error(f"❌ Failed to check Ollama status: {e}")
        raise HTTPException(status_code=500, detail="Failed to check Ollama status")


@router.get("/resources", response_model=SystemResourcesResponse)
async def get_system_resources():
    """
    Detect system resources (RAM, disk space)

    Returns recommended tier based on available RAM:
    - Essential: 8GB+
    - Balanced: 16GB+
    - Power User: 32GB+

    Public endpoint - no authentication required (setup phase).
    """
    try:
        wizard = get_setup_wizard()
        resources = await wizard.detect_system_resources()

        return SystemResourcesResponse(**resources)

    except Exception as e:
        logger.error(f"❌ Failed to detect system resources: {e}")
        raise HTTPException(status_code=500, detail="Failed to detect system resources")


@router.get("/models/recommendations", response_model=ModelRecommendationsResponse)
async def get_model_recommendations(tier: Optional[str] = None):
    """
    Get recommended models for a tier

    Args:
        tier: Optional tier (essential|balanced|power_user)
              If not provided, auto-detects based on system RAM

    Returns model recommendations from config/recommended_models.json
    with hot slot suggestions.

    Public endpoint - no authentication required (setup phase).
    """
    try:
        wizard = get_setup_wizard()
        recommendations = await wizard.load_model_recommendations(tier=tier)

        return ModelRecommendationsResponse(**recommendations)

    except Exception as e:
        logger.error(f"❌ Failed to get model recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get model recommendations")


@router.get("/models/installed", response_model=InstalledModelsResponse)
async def get_installed_models():
    """
    Get list of installed Ollama models

    Queries Ollama API for currently installed models.

    Public endpoint - no authentication required (setup phase).
    """
    try:
        wizard = get_setup_wizard()
        models = await wizard.get_installed_models()

        return InstalledModelsResponse(models=models)

    except Exception as e:
        logger.error(f"❌ Failed to get installed models: {e}")
        raise HTTPException(status_code=500, detail="Failed to get installed models")


@router.post("/models/download", response_model=DownloadModelResponse)
async def download_model(body: DownloadModelRequest):
    """
    Download a model via Ollama

    This is a blocking endpoint that downloads the model synchronously.
    For progress updates, use Server-Sent Events (SSE) endpoint.

    Args:
        model_name: Ollama model name (e.g., "qwen2.5-coder:7b-instruct")

    Public endpoint - no authentication required (setup phase).

    Note: This can take several minutes for large models.
    """
    try:
        wizard = get_setup_wizard()

        # Download model (blocking)
        success = await wizard.download_model(body.model_name)

        if success:
            return DownloadModelResponse(
                success=True,
                model_name=body.model_name,
                message=f"Model '{body.model_name}' downloaded successfully"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download model '{body.model_name}'"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to download model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hot-slots", response_model=ConfigureHotSlotsResponse)
async def configure_hot_slots(body: ConfigureHotSlotsRequest):
    """
    Configure hot slots (1-4 favorite models)

    Args:
        slots: Mapping of slot number (1-4) to model name
               Use null to clear a slot

    Example:
        {
            "slots": {
                "1": "gpt-oss:20b",
                "2": "qwen2.5-coder:14b",
                "3": "llama3.1:8b",
                "4": null
            }
        }

    Public endpoint - no authentication required (setup phase).
    """
    try:
        wizard = get_setup_wizard()

        # Validate slot numbers
        for slot_num in body.slots.keys():
            if slot_num not in [1, 2, 3, 4]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid slot number: {slot_num} (must be 1-4)"
                )

        # Configure hot slots
        success = await wizard.configure_hot_slots(body.slots)

        if success:
            return ConfigureHotSlotsResponse(
                success=True,
                message="Hot slots configured successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to configure hot slots")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to configure hot slots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/account", response_model=CreateAccountResponse)
async def create_account(request: Request, body: CreateAccountRequest):
    """
    Create local super_admin account

    This endpoint:
    1. Optionally initializes founder password (if provided and not already setup)
    2. Creates local super_admin user account
    3. Returns user_id for session creation

    Args:
        username: Username (3-20 chars, alphanumeric + underscore)
        password: Password (min 8 chars)
        confirm_password: Password confirmation
        founder_password: Optional founder password (for founder_rights setup)

    Public endpoint - no authentication required (first-time setup).
    """
    try:
        # Validate password confirmation
        if body.password != body.confirm_password:
            return CreateAccountResponse(
                success=False,
                error="Passwords do not match"
            )

        wizard = get_setup_wizard()

        # Create account
        result = await wizard.create_local_account(
            username=body.username,
            password=body.password,
            founder_password=body.founder_password
        )

        return CreateAccountResponse(**result)

    except Exception as e:
        logger.error(f"❌ Failed to create account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete", response_model=CompleteSetupResponse)
async def complete_setup():
    """
    Mark setup wizard as completed

    This is called after all setup steps are finished.

    Public endpoint - no authentication required (setup phase).
    """
    try:
        wizard = get_setup_wizard()
        success = await wizard.complete_setup()

        if success:
            return CompleteSetupResponse(
                success=True,
                message="Setup wizard completed successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to complete setup")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to complete setup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export router
__all__ = ['router']
