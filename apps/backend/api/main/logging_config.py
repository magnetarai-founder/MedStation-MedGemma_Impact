"""
Logging configuration for MagnetarStudio API.

Suppresses verbose DEBUG and INFO logs from various services to reduce terminal noise.
"""

import logging


def configure_logging():
    """
    Configure logging levels for all services.

    Suppresses DEBUG logs from httpcore and httpx to reduce terminal noise.
    Suppresses verbose INFO logs from various services for cleaner startup.
    """
    # Suppress DEBUG logs from httpcore and httpx to reduce terminal noise
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Suppress verbose INFO logs from various services for cleaner startup
    logging.getLogger("metal4_engine").setLevel(logging.WARNING)
    logging.getLogger("metal4_diagnostics").setLevel(logging.WARNING)
    logging.getLogger("metal4_resources").setLevel(logging.WARNING)
    logging.getLogger("data_engine").setLevel(logging.WARNING)
    logging.getLogger("code_editor_service").setLevel(logging.WARNING)
    logging.getLogger("docs_service").setLevel(logging.WARNING)
    logging.getLogger("mlx_embedder").setLevel(logging.WARNING)
    logging.getLogger("unified_embedder").setLevel(logging.WARNING)
    logging.getLogger("token_counter").setLevel(logging.WARNING)
    logging.getLogger("chat_service").setLevel(logging.WARNING)
    logging.getLogger("neutron_core.engine").setLevel(logging.WARNING)
