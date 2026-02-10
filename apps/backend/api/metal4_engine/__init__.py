"""
Metal 4 Unified Command Queue Engine for MedStation

Provides:
- Unified command queues (Q_render, Q_ml, Q_blit)
- Event-based synchronization (zero CPU overhead)
- Zero-copy unified memory heaps
- True parallelism for AI + DB + UI operations

Architecture:
- Q_render: Graphics/UI (never blocks on ML)
- Q_ml: ML/Compute (embeddings, inference, SQL kernels)
- Q_blit: Async transfers (background I/O)

Components:
- capabilities.py: MetalVersion enum, MetalCapabilities dataclass, detection
- engine.py: Metal4Engine class with tick flow methods
"""

import logging
from typing import Any

from api.metal4_engine.capabilities import (
    MetalVersion,
    MetalCapabilities,
    detect_metal_capabilities,
)
from api.metal4_engine.engine import Metal4Engine

logger = logging.getLogger(__name__)


# ===== Global Engine Instance =====

_metal4_engine: Metal4Engine | None = None


def get_metal4_engine() -> Metal4Engine:
    """Get singleton Metal 4 engine instance"""
    global _metal4_engine
    if _metal4_engine is None:
        _metal4_engine = Metal4Engine()
    return _metal4_engine


def _reset_metal4_engine() -> None:
    """Reset the global instance - for testing only."""
    global _metal4_engine
    _metal4_engine = None


def validate_metal4_setup() -> dict[str, Any]:
    """
    Validate Metal 4 setup and return detailed status

    Returns:
        Status dict with capabilities and recommendations
    """
    engine = get_metal4_engine()
    caps = engine.get_capabilities_dict()

    status = {
        'status': 'ready' if engine.is_available() else 'unavailable',
        'capabilities': caps,
        'recommendations': []
    }

    # Add recommendations
    if not engine.capabilities.is_apple_silicon:
        status['recommendations'].append(
            "Consider using Apple Silicon for optimal performance (3-5x faster)"
        )

    if engine.capabilities.version.value < MetalVersion.METAL_4.value:
        status['recommendations'].append(
            f"Upgrade to macOS Sequoia 15.0+ for Metal 4 features"
        )

    if not engine.capabilities.supports_mps:
        status['recommendations'].append(
            "Install PyTorch with MPS support for GPU acceleration"
        )

    if engine.is_available():
        status['recommendations'].append(
            f"All optimizations enabled - expect 3-5x performance improvement"
        )

    return status


__all__ = [
    # Main class
    "Metal4Engine",
    # Capabilities
    "MetalVersion",
    "MetalCapabilities",
    "detect_metal_capabilities",
    # Singleton
    "get_metal4_engine",
    "_reset_metal4_engine",
    # Validation
    "validate_metal4_setup",
]
