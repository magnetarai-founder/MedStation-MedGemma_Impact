"""
CORS middleware configuration.

Configures Cross-Origin Resource Sharing for development and production.
"""

import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


def configure_cors(app: FastAPI) -> None:
    """
    Apply CORS settings to the app with environment-based restrictions.

    Security (HIGH-02): CORS hardening:
    1. JWT tokens in Authorization header (not cookies - no automatic sending)
    2. CORS restricts origins based on environment (dev vs production)
    3. Restricted HTTP methods in production
    4. Restricted headers to required only
    5. Browsers enforce SOP - malicious sites can't read responses

    Args:
        app: FastAPI application instance
    """
    # Determine environment
    env = os.getenv('MEDSTATION_ENV', 'production').lower()
    is_production = env == 'production'

    # Parse CORS origins from environment or use defaults
    cors_origins_env = os.getenv('MEDSTATION_CORS_ORIGINS', '')
    if cors_origins_env:
        # Parse comma-separated list from environment
        allowed_origins = [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]
    else:
        if is_production:
            # SECURITY: Production requires explicit origin configuration
            # No defaults - must be set via environment variable
            allowed_origins = []
            logger.warning("No CORS origins configured for production!")
            logger.warning("Set MEDSTATION_CORS_ORIGINS environment variable")
        else:
            # Default dev origins - include common Vite fallback ports
            allowed_origins = [
                "http://localhost:4200",
                "http://localhost:4201",  # Vite fallback when 4200 is busy
                "http://127.0.0.1:4200",
                "http://localhost:5173",  # Vite default
                "http://localhost:5174",  # Vite fallback
                "http://localhost:5175",  # Vite fallback
                "http://127.0.0.1:5173",  # 127.0.0.1 equivalents for Vite
                "http://127.0.0.1:5174",
                "http://127.0.0.1:5175",
                "http://localhost:3000"
            ]

    # SECURITY: Restrict methods and headers based on environment
    if is_production:
        # Production: Only allow specific HTTP methods
        allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        # Production: Only allow required headers
        allowed_headers = [
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "Accept",
            "Origin"
        ]
    else:
        # Development: Allow all for easier debugging
        allowed_methods = ["*"]
        allowed_headers = ["*"]

        # SECURITY WARNING: Prominent alert about permissive CORS in development
        logger.warning("=" * 60)
        logger.warning("⚠️  DEVELOPMENT CORS MODE - NOT FOR PRODUCTION ⚠️")
        logger.warning("CORS is configured with permissive settings:")
        logger.warning("  - allow_methods: ['*']")
        logger.warning("  - allow_headers: ['*']")
        logger.warning("  - Origins: %s", ", ".join(allowed_origins[:3]) + "...")
        logger.warning("Set MEDSTATION_ENV=production for secure CORS settings")
        logger.warning("=" * 60)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=allowed_methods,
        allow_headers=allowed_headers,
        max_age=3600,  # Cache preflight requests for 1 hour
    )
