"""
Metal 4 GPU initialization.

Initializes Metal 4 engine for GPU acceleration on Apple Silicon.
"""

import logging

logger = logging.getLogger(__name__)


def initialize_metal4() -> None:
    """
    Initialize Metal 4 GPU / SQL engines used by the app.

    Metal 4 provides GPU acceleration for:
    - Local AI inference
    - SQL query execution
    - Embedding generation

    Note: Failures are logged but do not prevent startup.
    The system will fall back to CPU processing if Metal 4 is unavailable.
    """
    try:
        from metal4_engine import get_metal4_engine, validate_metal4_setup
        metal4_engine = get_metal4_engine()

        # Validation is silent - Metal 4 banner already shown during import
        # Engine is initialized lazily on first use
        logger.debug("Metal 4 engine available")
    except Exception as e:
        logger.warning(f"Metal 4 not available: {e}")
        # Not fatal - system will use CPU fallback
