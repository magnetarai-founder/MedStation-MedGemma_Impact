"""
Insights Lab Pydantic Models

Voice transcription → Template application → Multi-output generation.
One recording, unlimited formatted outputs.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ===== Enums =====

class TemplateCategory(str, Enum):
    GENERAL = "GENERAL"
    MEDICAL = "MEDICAL"
    ACADEMIC = "ACADEMIC"
    SERMON = "SERMON"
    MEETING = "MEETING"
    LEGAL = "LEGAL"
    INTERVIEW = "INTERVIEW"


class OutputFormat(str, Enum):
    MARKDOWN = "MARKDOWN"
    TEXT = "TEXT"
    JSON = "JSON"
    HTML = "HTML"


# ===== Recording Models =====

class Recording(BaseModel):
    """A voice recording with transcription"""
    id: str
    title: str
    file_path: str
    duration: float
    transcript: str
    speaker_segments: Optional[Dict[str, Any]] = None
    user_id: str
    team_id: Optional[str] = None
    folder_id: Optional[str] = None
    tags: List[str] = []
    created_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": "rec_abc123",
                "title": "Bible Study - John 3",
                "file_path": "/vault/recordings/rec_abc123.m4a",
                "duration": 3600.5,
                "transcript": "In the beginning...",
                "user_id": "user_123",
                "tags": ["sermon", "gospel"],
                "created_at": "2025-12-20T10:00:00Z"
            }
        }


class CreateRecordingResponse(BaseModel):
    """Response after uploading and transcribing a recording"""
    recording_id: str
    transcript: str
    duration: Optional[float] = None
    message: str = "Recording saved and transcribed"


class RecordingListResponse(BaseModel):
    """List of recordings"""
    recordings: List[Recording]
    total: int


class RecordingDetailResponse(BaseModel):
    """Single recording with all its formatted outputs"""
    recording: Recording
    outputs: List["FormattedOutput"]


class UpdateRecordingRequest(BaseModel):
    """Update recording metadata"""
    title: Optional[str] = None
    tags: Optional[List[str]] = None
    folder_id: Optional[str] = None


# ===== Template Models =====

class Template(BaseModel):
    """A formatting template/blueprint"""
    id: str
    name: str
    description: str
    system_prompt: str
    category: TemplateCategory
    is_builtin: bool
    output_format: OutputFormat
    created_by: str
    team_id: Optional[str] = None
    created_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": "tmpl_exec_summary",
                "name": "Executive Summary",
                "description": "Concise 2-3 paragraph summary",
                "system_prompt": "Summarize the following transcript...",
                "category": "GENERAL",
                "is_builtin": True,
                "output_format": "MARKDOWN",
                "created_by": "system",
                "created_at": "2025-12-20T10:00:00Z"
            }
        }


class CreateTemplateRequest(BaseModel):
    """Create a custom template"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    system_prompt: str = Field(..., min_length=10)
    category: TemplateCategory
    output_format: OutputFormat = OutputFormat.MARKDOWN
    team_id: Optional[str] = None


class UpdateTemplateRequest(BaseModel):
    """Update an existing template"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    system_prompt: Optional[str] = Field(None, min_length=10)
    category: Optional[TemplateCategory] = None
    output_format: Optional[OutputFormat] = None


class TemplateListResponse(BaseModel):
    """List of templates"""
    templates: List[Template]
    total: int


# ===== Formatted Output Models =====

class FormattedOutput(BaseModel):
    """A template-formatted output from a recording"""
    id: str
    recording_id: str
    template_id: str
    template_name: str
    content: str
    format: OutputFormat
    generated_at: str
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "out_xyz789",
                "recording_id": "rec_abc123",
                "template_id": "tmpl_exec_summary",
                "template_name": "Executive Summary",
                "content": "This sermon explored the theme of...",
                "format": "MARKDOWN",
                "generated_at": "2025-12-20T10:30:00Z"
            }
        }


class ApplyTemplateRequest(BaseModel):
    """Apply a template to a recording"""
    template_id: str
    use_foundation_models: bool = True  # Prefer on-device FM when available


class ApplyTemplateResponse(BaseModel):
    """Response after applying a template"""
    output_id: str
    content: str
    template_name: str
    message: str = "Template applied successfully"


class BatchApplyRequest(BaseModel):
    """Apply templates to multiple recordings"""
    recording_ids: List[str]
    template_ids: List[str]
    use_foundation_models: bool = True


class BatchApplyResponse(BaseModel):
    """Response after batch template application"""
    outputs: List[FormattedOutput]
    total_processed: int
    failed: int = 0
    message: str


# Forward reference update
RecordingDetailResponse.model_rebuild()
