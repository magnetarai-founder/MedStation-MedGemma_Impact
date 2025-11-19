"""
Startup initialization package for FastAPI application.

Centralizes startup logic:
- Database migrations
- Ollama model initialization
- Metal 4 GPU setup
- Health checks
- Background tasks
"""

from .migrations import run_startup_migrations
from .ollama import initialize_ollama
from .metal4 import initialize_metal4
from .health_checks import run_health_checks

__all__ = [
    "run_startup_migrations",
    "initialize_ollama",
    "initialize_metal4",
    "run_health_checks",
]
