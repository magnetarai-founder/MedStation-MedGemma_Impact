"""
Metal 4 GPU diagnostic API endpoints.

Provides Metal 4 capabilities, statistics, validation, and optimization settings.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from api.errors import http_400, http_503

router = APIRouter(prefix="/api/v1/metal", tags=["Metal 4 GPU"])
logger = logging.getLogger(__name__)

# Import Metal 4 engine (initialized in main.py)
_metal4_engine = None


def set_metal4_engine(engine) -> None:
    """Set the Metal 4 engine instance (called from main.py during initialization)"""
    global _metal4_engine
    _metal4_engine = engine


@router.get("/capabilities")
async def get_metal_capabilities() -> dict[str, Any]:
    """
    Get Metal 4 capabilities and system information

    Returns:
        Metal version, device name, feature support flags
    """
    if _metal4_engine is None:
        raise http_503("Metal 4 engine not available on this system")

    return _metal4_engine.get_capabilities_dict()


@router.get("/stats")
async def get_metal_stats() -> dict[str, Any]:
    """
    Get real-time Metal 4 statistics and performance metrics

    Returns:
        GPU utilization, memory usage, operation counts
    """
    if _metal4_engine is None:
        raise http_503("Metal 4 engine not available on this system")

    return _metal4_engine.get_stats()


@router.get("/validate")
async def validate_metal_setup() -> dict[str, Any]:
    """
    Validate Metal 4 setup and get recommendations

    Returns:
        Status, capabilities, and optimization recommendations
    """
    if _metal4_engine is None:
        return {
            'status': 'unavailable',
            'capabilities': {
                'available': False,
                'version': 0,
                'device_name': 'N/A',
                'is_apple_silicon': False,
                'features': {
                    'unified_memory': False,
                    'mps': False,
                    'ane': False,
                    'sparse_resources': False,
                    'ml_command_encoder': False
                }
            },
            'recommendations': [
                'Metal 4 requires macOS Sequoia 15.0+ on Apple Silicon',
                'Install PyTorch with MPS support for GPU acceleration'
            ]
        }

    from metal4_engine import validate_metal4_setup as _validate
    return _validate()


@router.get("/optimize/{operation_type}")
async def get_optimization_settings(operation_type: str) -> dict[str, Any]:
    """
    Get optimization settings for a specific operation type

    Args:
        operation_type: 'embedding', 'inference', 'sql', or 'render'

    Returns:
        Optimized settings dict for the operation
    """
    if _metal4_engine is None:
        raise http_503("Metal 4 engine not available on this system")

    valid_types = ['embedding', 'inference', 'sql', 'render']
    if operation_type not in valid_types:
        raise http_400(f"Invalid operation_type. Must be one of: {', '.join(valid_types)}")

    return _metal4_engine.optimize_for_operation(operation_type)
