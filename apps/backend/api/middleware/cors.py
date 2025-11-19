"""
CORS middleware configuration.

Configures Cross-Origin Resource Sharing for development and production.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def configure_cors(app: FastAPI) -> None:
    """
    Apply CORS settings to the app.

    Security (HIGH-04): CSRF Protection provided by:
    1. JWT tokens in Authorization header (not cookies - no automatic sending)
    2. CORS restricts origins to trusted dev servers
    3. Browsers enforce SOP - malicious sites can't read responses

    Args:
        app: FastAPI application instance
    """
    # Parse CORS origins from environment or use defaults
    cors_origins_env = os.getenv('ELOHIM_CORS_ORIGINS', '')
    if cors_origins_env:
        # Parse comma-separated list from environment
        allowed_origins = [origin.strip() for origin in cors_origins_env.split(',') if origin.strip()]
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=3600,  # LOW-03: Cache preflight requests for 1 hour
    )
