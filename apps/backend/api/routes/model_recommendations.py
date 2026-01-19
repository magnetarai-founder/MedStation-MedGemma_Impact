#!/usr/bin/env python3
"""
Model Recommendation API
Provides curated model recommendations based on system capabilities

Follows MagnetarStudio API standards (see API_STANDARDS.md).
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field

# Auth imports
from api.auth_middleware import get_current_user
from api.routes.schemas import SuccessResponse, ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/models", tags=["models"])

# ===== Request/Response Models =====

class SystemInfo(BaseModel):
    """User's Mac system information"""
    total_memory_gb: float = Field(..., description="Total unified memory in GB")
    cpu_cores: int = Field(..., description="Number of CPU cores")
    has_metal: bool = Field(default=True, description="Metal GPU support")


class ModelCompatibility(BaseModel):
    """Model compatibility assessment"""
    performance: str = Field(..., description="excellent, good, fair, insufficient")
    reason: str = Field(..., description="Human-readable compatibility reason")
    estimated_memory_usage: Optional[float] = Field(None, description="Estimated memory usage in GB")


class RecommendedModel(BaseModel):
    """A recommended model with all metadata"""
    model_name: str
    display_name: str
    description: str
    tags: List[str]
    parameter_size: str
    estimated_memory_gb: float
    compatibility: ModelCompatibility
    badges: List[str]
    is_installed: bool
    is_multi_purpose: bool
    primary_use_cases: List[str]
    popularity_rank: int
    capability: str


class RecommendationsResponse(BaseModel):
    """Response containing recommended models"""
    recommendations: List[RecommendedModel]
    total_count: int
    filtered_by_hardware: bool
    learning_enabled: bool = False
    personalization_active: bool = False


# ===== Data Loading =====

def load_curated_models() -> Dict[str, Any]:
    """Load curated models from JSON file"""
    data_path = Path(__file__).parent.parent / "data" / "curated_models.json"

    try:
        with open(data_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Curated models file not found: {data_path}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Model recommendations data not found"
            ).model_dump()
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in curated models", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Invalid model recommendations data"
            ).model_dump()
        )


# ===== Compatibility Logic =====

def assess_compatibility(
    model: Dict[str, Any],
    total_memory_gb: float
) -> ModelCompatibility:
    """
    Assess if a model is compatible with user's hardware

    Args:
        model: Model metadata from curated list
        total_memory_gb: User's total memory

    Returns:
        ModelCompatibility with performance level and reason
    """
    min_mem = model.get("min_memory_gb", 8)
    rec_mem = model.get("recommended_memory_gb", 16)
    param_size = model.get("parameter_size", "7B")

    # Estimate actual memory usage (rough heuristic)
    # For quantized models: ~0.7GB per billion parameters (Q4)
    try:
        param_value = float(param_size.replace("B", "").replace("+", ""))
        estimated_usage = param_value * 0.7
    except (ValueError, AttributeError):
        estimated_usage = min_mem

    # Calculate available memory (leave 25% for system/other apps)
    available_mem = total_memory_gb * 0.75

    # Determine performance level
    if total_memory_gb < min_mem:
        return ModelCompatibility(
            performance="insufficient",
            reason=f"Requires at least {min_mem}GB RAM, you have {total_memory_gb}GB",
            estimated_memory_usage=estimated_usage
        )
    elif total_memory_gb >= rec_mem and estimated_usage < available_mem * 0.5:
        return ModelCompatibility(
            performance="excellent",
            reason=f"Fits comfortably in {total_memory_gb}GB with room for multitasking",
            estimated_memory_usage=estimated_usage
        )
    elif total_memory_gb >= rec_mem:
        return ModelCompatibility(
            performance="good",
            reason=f"Runs well on {total_memory_gb}GB, may use most available memory",
            estimated_memory_usage=estimated_usage
        )
    else:
        return ModelCompatibility(
            performance="fair",
            reason=f"Can run but may be slow. Recommended: {rec_mem}GB, you have {total_memory_gb}GB",
            estimated_memory_usage=estimated_usage
        )


def get_primary_use_cases(tags: List[str]) -> List[str]:
    """Map tags to workspace/use case names"""
    use_case_map = {
        "chat": "Chat",
        "code": "Code",
        "reasoning": "Reasoning",
        "deep-reasoning": "Reasoning",
        "data": "Database",
        "vision": "Vision",
        "creative": "Creative",
        "orchestration": "Orchestrator"
    }

    use_cases = []
    for tag in tags:
        if tag in use_case_map:
            case = use_case_map[tag]
            if case not in use_cases:
                use_cases.append(case)

    return use_cases or ["General"]


# ===== Main Endpoint =====

@router.get(
    "/recommended",
    response_model=SuccessResponse[RecommendationsResponse],
    status_code=status.HTTP_200_OK,
    name="models_get_recommendations",
    summary="Get model recommendations",
    description="Get curated model recommendations filtered by system capabilities"
)
async def get_recommended_models(
    total_memory_gb: float = Query(..., description="Total system memory in GB"),
    cpu_cores: int = Query(..., description="Number of CPU cores"),
    has_metal: bool = Query(True, description="Metal GPU support"),
    installed_models: Optional[str] = Query(None, description="Comma-separated list of installed models"),
    current_user: Dict = Depends(get_current_user)
) -> SuccessResponse[RecommendationsResponse]:
    """
    Get curated model recommendations based on system capabilities

    Returns models sorted by:
    1. Recommended (badge) first
    2. Installed models highlighted
    3. Experimental models mixed in with badges
    4. Filtered by hardware compatibility

    Args:
        total_memory_gb: Total system memory in GB
        cpu_cores: Number of CPU cores
        has_metal: Metal GPU support (default: True)
        installed_models: Comma-separated list of installed models

    Returns:
        Filtered and sorted model recommendations

    Note: Static recommendations - learning integration coming in future phase
    """
    try:
        # Load curated models
        data = load_curated_models()
        all_models = data.get("models", [])

        # Parse installed models
        installed_set = set()
        if installed_models:
            installed_set = set(m.strip() for m in installed_models.split(","))

        # Filter and build recommendations
        recommendations = []

        for model in all_models:
            # Assess compatibility
            compatibility = assess_compatibility(model, total_memory_gb)

            # Skip insufficient models (user can't run them)
            if compatibility.performance == "insufficient":
                continue

            # Check if installed
            is_installed = model["model_name"] in installed_set

            # Build recommendation
            rec = RecommendedModel(
                model_name=model["model_name"],
                display_name=model["display_name"],
                description=model["description"],
                tags=model["tags"],
                parameter_size=model["parameter_size"],
                estimated_memory_gb=compatibility.estimated_memory_usage or model["min_memory_gb"],
                compatibility=compatibility,
                badges=model.get("badges", []),
                is_installed=is_installed,
                is_multi_purpose=model.get("is_multi_purpose", False),
                primary_use_cases=get_primary_use_cases(model["tags"]),
                popularity_rank=model.get("popularity_rank", 999),
                capability=model.get("capability", "general")
            )

            recommendations.append(rec)

        # Sort by popularity_rank (lower = more recommended)
        # This ensures recommended models appear first
        recommendations.sort(key=lambda x: x.popularity_rank)

        result = RecommendationsResponse(
            recommendations=recommendations,
            total_count=len(recommendations),
            filtered_by_hardware=True,
            learning_enabled=False,  # Phase 2
            personalization_active=False  # Phase 2
        )

        return SuccessResponse(
            data=result,
            message=f"Retrieved {len(recommendations)} compatible model{'s' if len(recommendations) != 1 else ''}"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get model recommendations", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to retrieve model recommendations"
            ).model_dump()
        )


# ===== Health Check =====

class RecommendationsHealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    last_updated: str
    total_models: int
    learning_enabled: bool


@router.get(
    "/recommended/health",
    response_model=SuccessResponse[RecommendationsHealthResponse],
    status_code=status.HTTP_200_OK,
    name="models_recommendations_health",
    summary="Recommendations health check",
    description="Check if model recommendations system is healthy"
)
async def recommendations_health() -> SuccessResponse[RecommendationsHealthResponse]:
    """
    Health check for recommendations system

    Returns:
        System health status and metadata
    """
    try:
        data = load_curated_models()

        health_data = RecommendationsHealthResponse(
            status="healthy",
            version=data.get("version", "unknown"),
            last_updated=data.get("last_updated", "unknown"),
            total_models=len(data.get("models", [])),
            learning_enabled=False
        )

        return SuccessResponse(
            data=health_data,
            message="Recommendations system is healthy"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Health check failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Failed to check recommendations health"
            ).model_dump()
        )


# ===== Model Enrichment Endpoint =====

# Import enrichment route
try:
    from .models.enrichment import router as enrichment_router
    # Include enrichment routes under /api/v1/models
    router.include_router(enrichment_router)
    logger.info("✅ Model enrichment routes registered")
except Exception as e:
    logger.warning(f"⚠️ Could not register enrichment routes: {e}")
