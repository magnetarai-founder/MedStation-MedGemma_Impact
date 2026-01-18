"""
Insights Lab Module

Voice transcription → Template application → Multi-output generation.
One recording, unlimited formatted outputs.

"The Lord is my rock, my firm foundation." - Psalm 18:2

This module has been refactored from insights_service.py (1,224 lines) into:
- database.py: Database schema, connection management, initialization
- templates.py: Built-in template definitions
- transcription.py: Whisper transcription logic
- template_engine.py: Ollama template application
- routes/recordings.py: Recording CRUD endpoints
- routes/templates.py: Template CRUD endpoints
- routes/outputs.py: Template application endpoints
- routes/legacy.py: Legacy compatibility endpoints
"""

from fastapi import APIRouter, Depends

from api.auth_middleware import get_current_user

from .database import init_insights_db, get_db, INSIGHTS_DIR, RECORDINGS_DIR
from .templates import BUILTIN_TEMPLATES, DEFAULT_TEMPLATE_IDS
from .transcription import transcribe_audio_with_whisper, get_audio_duration
from .template_engine import apply_template_with_ollama, auto_apply_default_templates
from .routes import recordings_router, templates_router, outputs_router, legacy_router

# Initialize database on import
init_insights_db()

# Create combined router with all routes
router = APIRouter(
    prefix="/api/v1/insights",
    tags=["Insights Lab"],
    dependencies=[Depends(get_current_user)]
)

# Include all sub-routers
router.include_router(recordings_router)
router.include_router(templates_router)
router.include_router(outputs_router)
router.include_router(legacy_router)

__all__ = [
    "router",
    "get_db",
    "init_insights_db",
    "INSIGHTS_DIR",
    "RECORDINGS_DIR",
    "BUILTIN_TEMPLATES",
    "DEFAULT_TEMPLATE_IDS",
    "transcribe_audio_with_whisper",
    "get_audio_duration",
    "apply_template_with_ollama",
    "auto_apply_default_templates",
]
