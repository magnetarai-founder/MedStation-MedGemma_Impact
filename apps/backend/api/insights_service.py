"""
Insights Lab Service - Compatibility Facade

This file has been refactored into the api/insights/ module.
It now serves as a backward-compatible facade for imports.

For new code, import directly from the insights module:
    from api.insights import router
    from api.insights import transcribe_audio_with_whisper
    from api.insights.database import get_db

"The Lord is my rock, my firm foundation." - Psalm 18:2
"""

# Re-export everything from the new modular structure
from api.insights import (
    router,
    get_db,
    init_insights_db,
    INSIGHTS_DIR,
    RECORDINGS_DIR,
    BUILTIN_TEMPLATES,
    DEFAULT_TEMPLATE_IDS,
    transcribe_audio_with_whisper,
    get_audio_duration,
    apply_template_with_ollama,
    auto_apply_default_templates,
)

# Re-export Pydantic models for backward compatibility
from api.schemas.insights_models import (
    Recording,
    CreateRecordingResponse,
    RecordingListResponse,
    RecordingDetailResponse,
    UpdateRecordingRequest,
    Template,
    CreateTemplateRequest,
    UpdateTemplateRequest,
    TemplateListResponse,
    FormattedOutput,
    ApplyTemplateRequest,
    ApplyTemplateResponse,
    BatchApplyRequest,
    BatchApplyResponse,
    TemplateCategory,
    OutputFormat,
)

# For backward compatibility with direct imports
from api.insights.database import (
    build_safe_update,
    RECORDING_UPDATE_COLUMNS,
    TEMPLATE_UPDATE_COLUMNS,
    DATABASE_SCHEMA,
    INSIGHTS_DB_PATH,
)

__all__ = [
    "router",
    "get_db",
    "init_insights_db",
    "build_safe_update",
    "INSIGHTS_DIR",
    "RECORDINGS_DIR",
    "INSIGHTS_DB_PATH",
    "BUILTIN_TEMPLATES",
    "DEFAULT_TEMPLATE_IDS",
    "DATABASE_SCHEMA",
    "RECORDING_UPDATE_COLUMNS",
    "TEMPLATE_UPDATE_COLUMNS",
    "transcribe_audio_with_whisper",
    "get_audio_duration",
    "apply_template_with_ollama",
    "auto_apply_default_templates",
    # Models
    "Recording",
    "CreateRecordingResponse",
    "RecordingListResponse",
    "RecordingDetailResponse",
    "UpdateRecordingRequest",
    "Template",
    "CreateTemplateRequest",
    "UpdateTemplateRequest",
    "TemplateListResponse",
    "FormattedOutput",
    "ApplyTemplateRequest",
    "ApplyTemplateResponse",
    "BatchApplyRequest",
    "BatchApplyResponse",
    "TemplateCategory",
    "OutputFormat",
]
