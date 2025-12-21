"""
Insights Lab Service v2

Voice transcription → Template application → Multi-output generation.
One recording, unlimited formatted outputs.

"The Lord is my rock, my firm foundation." - Psalm 18:2
"""

import os
import json
import asyncio
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC
from uuid import uuid4
import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Request, Form, Depends, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import aiofiles

logger = logging.getLogger(__name__)

# Storage paths
from config_paths import get_config_paths
PATHS = get_config_paths()
INSIGHTS_DIR = PATHS.data_dir / "insights"
RECORDINGS_DIR = INSIGHTS_DIR / "recordings"
INSIGHTS_DB_PATH = INSIGHTS_DIR / "insights.db"

# Ensure directories exist
INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

from auth_middleware import get_current_user
from utils import sanitize_for_log, sanitize_filename

# Import Pydantic models
from api.schemas.insights_models import (
    Recording, CreateRecordingResponse, RecordingListResponse,
    RecordingDetailResponse, UpdateRecordingRequest,
    Template, CreateTemplateRequest, UpdateTemplateRequest, TemplateListResponse,
    FormattedOutput, ApplyTemplateRequest, ApplyTemplateResponse,
    BatchApplyRequest, BatchApplyResponse,
    TemplateCategory, OutputFormat
)


# Whitelisted columns for SQL UPDATE to prevent injection
RECORDING_UPDATE_COLUMNS = frozenset({"title", "tags", "folder_id"})
TEMPLATE_UPDATE_COLUMNS = frozenset({"name", "description", "system_prompt", "category", "output_format"})


def build_safe_update(updates_dict: Dict[str, Any], allowed_columns: frozenset) -> tuple[list, list]:
    """
    Build safe SQL UPDATE clause with whitelist validation.

    Args:
        updates_dict: Dict of column_name -> value pairs
        allowed_columns: Frozenset of allowed column names

    Returns:
        Tuple of (update_clauses, params) for use in SQL query

    Raises:
        ValueError: If any column is not in the whitelist
    """
    clauses = []
    params = []

    for column, value in updates_dict.items():
        if column not in allowed_columns:
            raise ValueError(f"Invalid column for update: {column}")
        clauses.append(f"{column} = ?")
        params.append(value)

    return clauses, params

router = APIRouter(
    prefix="/api/v1/insights",
    tags=["Insights Lab"],
    dependencies=[Depends(get_current_user)]
)


# ===== Database Schema =====

DATABASE_SCHEMA = """
-- Recordings table (voice recording vault)
CREATE TABLE IF NOT EXISTS recordings (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    file_path TEXT NOT NULL,
    duration REAL DEFAULT 0,
    transcript TEXT NOT NULL,
    speaker_segments TEXT,
    user_id TEXT NOT NULL,
    team_id TEXT,
    folder_id TEXT,
    tags TEXT DEFAULT '[]',
    created_at TEXT NOT NULL
);

-- Templates table (formatting blueprints)
CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'GENERAL',
    is_builtin INTEGER DEFAULT 0,
    output_format TEXT DEFAULT 'MARKDOWN',
    created_by TEXT NOT NULL,
    team_id TEXT,
    created_at TEXT NOT NULL
);

-- Formatted outputs table (template-applied results)
CREATE TABLE IF NOT EXISTS formatted_outputs (
    id TEXT PRIMARY KEY,
    recording_id TEXT NOT NULL,
    template_id TEXT NOT NULL,
    template_name TEXT NOT NULL,
    content TEXT NOT NULL,
    format TEXT DEFAULT 'MARKDOWN',
    metadata TEXT,
    generated_at TEXT NOT NULL,
    FOREIGN KEY (recording_id) REFERENCES recordings(id) ON DELETE CASCADE,
    FOREIGN KEY (template_id) REFERENCES templates(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_recordings_user ON recordings(user_id);
CREATE INDEX IF NOT EXISTS idx_recordings_team ON recordings(team_id);
CREATE INDEX IF NOT EXISTS idx_recordings_created ON recordings(created_at);
CREATE INDEX IF NOT EXISTS idx_templates_category ON templates(category);
CREATE INDEX IF NOT EXISTS idx_templates_builtin ON templates(is_builtin);
CREATE INDEX IF NOT EXISTS idx_outputs_recording ON formatted_outputs(recording_id);
"""

BUILTIN_TEMPLATES = [
    {
        "id": "tmpl_exec_summary",
        "name": "Executive Summary",
        "description": "Concise 2-3 paragraph summary with key takeaways",
        "system_prompt": """Provide a concise executive summary of this transcript in 2-3 paragraphs.
Focus on the main points, key decisions, and actionable items.
Use clear, professional language. Start with the most important information.""",
        "category": "GENERAL",
        "output_format": "MARKDOWN"
    },
    {
        "id": "tmpl_key_points",
        "name": "Key Points",
        "description": "Bulleted list of main points",
        "system_prompt": """Extract the key points from this transcript as a bulleted list.
- Focus on actionable items, decisions, and important topics discussed
- Include specific names, numbers, or dates mentioned
- Keep each point concise (1-2 sentences)
- Order by importance, not chronologically""",
        "category": "GENERAL",
        "output_format": "MARKDOWN"
    },
    {
        "id": "tmpl_verbatim",
        "name": "Full Transcript",
        "description": "Clean, formatted verbatim transcript",
        "system_prompt": """Format this as a clean, readable transcript.
- Add paragraph breaks at natural pauses
- Clean up filler words (um, uh, like) unless they're meaningful
- Preserve the speaker's exact words otherwise
- Add [inaudible] markers if the original has gaps""",
        "category": "GENERAL",
        "output_format": "TEXT"
    },
    {
        "id": "tmpl_sermon_outline",
        "name": "Sermon Outline",
        "description": "Structured sermon outline with scripture references",
        "system_prompt": """Create a sermon outline from this transcript:

# [Title/Theme]

## Scripture References
- List all Bible verses mentioned

## Main Points
1. First main point
   - Sub-points
   - Supporting scripture
2. Second main point
   - Sub-points
   - Supporting scripture

## Illustrations/Stories
- Key illustrations used

## Application Questions
1. Reflection questions for the congregation

## Action Items
- Practical takeaways""",
        "category": "SERMON",
        "output_format": "MARKDOWN"
    },
    {
        "id": "tmpl_medical_soap",
        "name": "Medical Note (SOAP)",
        "description": "SOAP format medical documentation",
        "system_prompt": """Format this as a medical note following SOAP structure:

## Subjective
Patient's reported symptoms, history, and concerns.

## Objective
Observable findings, vital signs, examination results.

## Assessment
Diagnosis or clinical impression.

## Plan
- Treatment plan
- Medications
- Follow-up instructions
- Patient education

Use professional medical terminology. Preserve all clinical details accurately.""",
        "category": "MEDICAL",
        "output_format": "MARKDOWN"
    },
    {
        "id": "tmpl_meeting_minutes",
        "name": "Meeting Minutes",
        "description": "Formal meeting minutes with action items",
        "system_prompt": """Create formal meeting minutes:

# Meeting Minutes

**Date:** [Extract from context]
**Attendees:** [List if mentioned]

## Agenda Items
1. Topic discussed
2. Topic discussed

## Discussion Summary
Brief summary of key discussions.

## Decisions Made
- Decision 1
- Decision 2

## Action Items
| Action | Owner | Due Date |
|--------|-------|----------|
| Task   | Name  | Date     |

## Next Steps
- Follow-up items
- Next meeting date if mentioned""",
        "category": "MEETING",
        "output_format": "MARKDOWN"
    },
    {
        "id": "tmpl_academic_notes",
        "name": "Academic Notes",
        "description": "Lecture notes with key concepts and definitions",
        "system_prompt": """Format as academic lecture notes:

# [Topic/Subject]

## Key Concepts
- **Concept 1**: Definition and explanation
- **Concept 2**: Definition and explanation

## Main Arguments/Theories
1. First major point
2. Second major point

## Important Terms
| Term | Definition |
|------|------------|
| Term | Meaning    |

## Questions for Further Study
- Research questions raised

## References Mentioned
- Any books, papers, or sources cited""",
        "category": "ACADEMIC",
        "output_format": "MARKDOWN"
    },
]


def get_db():
    """Get database connection with row factory"""
    conn = sqlite3.connect(str(INSIGHTS_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_insights_db():
    """Initialize insights database tables and built-in templates"""
    conn = get_db()
    cursor = conn.cursor()

    # Create tables
    cursor.executescript(DATABASE_SCHEMA)

    # Insert built-in templates
    now = datetime.now(UTC).isoformat()
    for template in BUILTIN_TEMPLATES:
        cursor.execute("""
            INSERT OR IGNORE INTO templates
            (id, name, description, system_prompt, category, is_builtin, output_format, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, 'system', ?)
        """, (
            template["id"],
            template["name"],
            template["description"],
            template["system_prompt"],
            template["category"],
            template["output_format"],
            now
        ))

    conn.commit()
    conn.close()
    logger.info("Insights Lab database initialized")


# Initialize on import
init_insights_db()


# ===== Whisper Transcription =====

def transcribe_audio_with_whisper(audio_path: Path) -> dict:
    """
    Transcribe audio using Whisper (local)
    Tries whisper.cpp first, falls back to Python whisper with Metal 4.
    """
    try:
        import subprocess

        # Try whisper.cpp first (faster, C++ implementation)
        whisper_cpp_path = Path.home() / "whisper.cpp" / "main"

        if whisper_cpp_path.exists():
            logger.info("Using whisper.cpp for transcription")

            result = subprocess.run(
                [
                    str(whisper_cpp_path),
                    "-m", str(Path.home() / "whisper.cpp" / "models" / "ggml-base.en.bin"),
                    "-f", str(audio_path),
                    "--output-txt"
                ],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                txt_path = audio_path.with_suffix('.txt')
                if txt_path.exists():
                    transcript = txt_path.read_text().strip()
                    txt_path.unlink()
                    return {
                        "transcript": transcript,
                        "language": "en",
                        "method": "whisper.cpp"
                    }

        # Fall back to Python whisper with Metal 4 acceleration
        try:
            import whisper
            import torch
            from metal4_engine import get_metal4_engine

            logger.info("Using Python whisper library for transcription")

            metal4_engine = get_metal4_engine()
            metal4_engine.kick_frame()
            device = metal4_engine.get_device()
            optimization_settings = metal4_engine.optimize_for_operation('inference')

            logger.info(f"Device: {device}, FP16: {optimization_settings['use_fp16']}")

            import time
            start = time.time()

            model = whisper.load_model("base", device=device)
            result = model.transcribe(
                str(audio_path),
                fp16=optimization_settings['use_fp16'],
                language="en"
            )

            elapsed = (time.time() - start) * 1000
            logger.info(f"Whisper transcription: {elapsed:.2f}ms")

            return {
                "transcript": result["text"].strip(),
                "language": result.get("language", "en"),
                "method": f"whisper-python-{device}",
                "duration": result.get("duration", 0)
            }

        except ImportError as e:
            logger.warning(f"Whisper not available: {e}")

    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}", exc_info=True)

    raise HTTPException(
        status_code=503,
        detail="Whisper transcription not available. Please install whisper.cpp or Python whisper library."
    )


def get_audio_duration(audio_path: str) -> float:
    """Get audio file duration in seconds"""
    try:
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


# ===== Template Application =====

async def apply_template_with_ollama(transcript: str, system_prompt: str) -> str:
    """Apply template using local Ollama"""
    try:
        from chat_service import ollama_client

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here is the transcript to process:\n\n{transcript}"}
        ]

        full_response = ""
        async for chunk in ollama_client.chat(
            model="qwen2.5-coder:7b-instruct",
            messages=messages,
            temperature=0.5,
            top_p=0.9
        ):
            full_response += chunk

        return full_response.strip()

    except Exception as e:
        logger.error(f"Ollama template application failed: {e}")
        raise HTTPException(status_code=500, detail=f"Template application failed: {str(e)}")


async def auto_apply_default_templates(recording_id: str, transcript: str, user_id: str):
    """Auto-apply the 3 default templates on upload (background task)"""
    default_templates = ["tmpl_exec_summary", "tmpl_key_points", "tmpl_verbatim"]

    conn = get_db()
    cursor = conn.cursor()

    for template_id in default_templates:
        try:
            cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
            template_row = cursor.fetchone()

            if template_row:
                content = await apply_template_with_ollama(transcript, template_row["system_prompt"])

                output_id = f"out_{uuid4().hex[:12]}"
                now = datetime.now(UTC).isoformat()

                cursor.execute("""
                    INSERT INTO formatted_outputs
                    (id, recording_id, template_id, template_name, content, format, generated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    output_id, recording_id, template_id,
                    template_row["name"], content, template_row["output_format"], now
                ))

                logger.info(f"Auto-applied template {template_id} to recording {recording_id}")

        except Exception as e:
            logger.error(f"Error auto-applying template {template_id}: {e}")

    conn.commit()
    conn.close()


# ===== Recording Endpoints =====

@router.post("/recordings", response_model=CreateRecordingResponse)
async def create_recording(
    request: Request,
    audio_file: UploadFile = File(...),
    title: str = Form("Untitled Recording"),
    tags: str = Form("[]"),
    team_id: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload and transcribe a recording.
    Audio is saved permanently to the vault, transcribed with Whisper,
    and default templates are auto-applied.
    """
    user_id = current_user.get("user_id") or current_user.get("id")

    # Validate file type
    safe_filename = sanitize_filename(audio_file.filename or "audio")
    valid_extensions = ['.m4a', '.mp3', '.wav', '.webm', '.mp4', '.ogg']
    file_ext = Path(safe_filename).suffix.lower()

    if file_ext not in valid_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Supported: {', '.join(valid_extensions)}"
        )

    # Generate recording ID and path
    recording_id = f"rec_{uuid4().hex[:12]}"
    audio_path = RECORDINGS_DIR / f"{recording_id}{file_ext}"

    try:
        # Save audio file to vault (persistent!)
        async with aiofiles.open(audio_path, 'wb') as f:
            content = await audio_file.read()
            await f.write(content)

        logger.info(f"Saved recording: {audio_path} ({len(content)} bytes)")

        # Get duration
        duration = get_audio_duration(str(audio_path))

        # Transcribe with Whisper
        result = await asyncio.to_thread(transcribe_audio_with_whisper, audio_path)
        transcript = result["transcript"]

        logger.info(f"Transcription complete: {len(transcript)} chars")

        # Save to database
        conn = get_db()
        cursor = conn.cursor()
        now = datetime.now(UTC).isoformat()

        cursor.execute("""
            INSERT INTO recordings
            (id, title, file_path, duration, transcript, user_id, team_id, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            recording_id, title, str(audio_path), duration,
            transcript, user_id, team_id, tags, now
        ))

        conn.commit()
        conn.close()

        # Auto-apply default templates (fire and forget)
        asyncio.create_task(auto_apply_default_templates(recording_id, transcript, user_id))

        return CreateRecordingResponse(
            recording_id=recording_id,
            transcript=transcript,
            duration=duration,
            message="Recording saved and transcribed. Default templates being applied."
        )

    except HTTPException:
        raise
    except Exception as e:
        # Clean up on error
        if audio_path.exists():
            audio_path.unlink()
        logger.error(f"Recording creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recordings", response_model=RecordingListResponse)
async def list_recordings(
    request: Request,
    team_id: Optional[str] = None,
    folder_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """List all recordings for the current user/team"""
    user_id = current_user.get("user_id") or current_user.get("id")

    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM recordings WHERE user_id = ?"
    params: List[Any] = [user_id]

    if team_id:
        query += " AND team_id = ?"
        params.append(team_id)

    if folder_id:
        query += " AND folder_id = ?"
        params.append(folder_id)

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()

    recordings = []
    for row in rows:
        recordings.append(Recording(
            id=row["id"],
            title=row["title"],
            file_path=row["file_path"],
            duration=row["duration"],
            transcript=row["transcript"],
            speaker_segments=json.loads(row["speaker_segments"]) if row["speaker_segments"] else None,
            user_id=row["user_id"],
            team_id=row["team_id"],
            folder_id=row["folder_id"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            created_at=row["created_at"]
        ))

    # Get total count
    cursor.execute("SELECT COUNT(*) FROM recordings WHERE user_id = ?", (user_id,))
    total = cursor.fetchone()[0]

    conn.close()

    return RecordingListResponse(recordings=recordings, total=total)


@router.get("/recordings/{recording_id}")
async def get_recording(
    recording_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get a single recording with all its formatted outputs"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM recordings WHERE id = ?", (recording_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Recording not found")

    recording = Recording(
        id=row["id"],
        title=row["title"],
        file_path=row["file_path"],
        duration=row["duration"],
        transcript=row["transcript"],
        user_id=row["user_id"],
        team_id=row["team_id"],
        tags=json.loads(row["tags"]) if row["tags"] else [],
        created_at=row["created_at"]
    )

    # Get all formatted outputs
    cursor.execute("SELECT * FROM formatted_outputs WHERE recording_id = ? ORDER BY generated_at DESC", (recording_id,))
    output_rows = cursor.fetchall()

    outputs = []
    for out_row in output_rows:
        outputs.append(FormattedOutput(
            id=out_row["id"],
            recording_id=out_row["recording_id"],
            template_id=out_row["template_id"],
            template_name=out_row["template_name"],
            content=out_row["content"],
            format=OutputFormat(out_row["format"]),
            generated_at=out_row["generated_at"],
            metadata=json.loads(out_row["metadata"]) if out_row["metadata"] else None
        ))

    conn.close()

    return {"recording": recording, "outputs": outputs}


@router.put("/recordings/{recording_id}")
async def update_recording(
    recording_id: str,
    request: UpdateRecordingRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update recording metadata"""
    conn = get_db()
    cursor = conn.cursor()

    # Check exists
    cursor.execute("SELECT id FROM recordings WHERE id = ?", (recording_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Recording not found")

    # Build updates dict with whitelisted columns only
    updates_dict = {}
    if request.title is not None:
        updates_dict["title"] = request.title
    if request.tags is not None:
        updates_dict["tags"] = json.dumps(request.tags)
    if request.folder_id is not None:
        updates_dict["folder_id"] = request.folder_id

    if updates_dict:
        # Use safe builder with whitelist validation
        updates, params = build_safe_update(updates_dict, RECORDING_UPDATE_COLUMNS)
        params.append(recording_id)
        cursor.execute(f"UPDATE recordings SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

    conn.close()

    return {"message": "Recording updated", "recording_id": recording_id}


@router.delete("/recordings/{recording_id}")
async def delete_recording(
    recording_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Delete a recording and its outputs"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT file_path FROM recordings WHERE id = ?", (recording_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Recording not found")

    # Delete audio file
    file_path = Path(row["file_path"])
    if file_path.exists():
        file_path.unlink()

    # Delete from database (CASCADE deletes outputs)
    cursor.execute("DELETE FROM formatted_outputs WHERE recording_id = ?", (recording_id,))
    cursor.execute("DELETE FROM recordings WHERE id = ?", (recording_id,))

    conn.commit()
    conn.close()

    return {"message": "Recording deleted", "recording_id": recording_id}


# ===== Template Endpoints =====

@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    request: Request,
    category: Optional[str] = None,
    include_builtin: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """List all available templates"""
    user_id = current_user.get("user_id") or current_user.get("id")

    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM templates WHERE (created_by = ? OR is_builtin = 1)"
    params: List[Any] = [user_id]

    if not include_builtin:
        query = "SELECT * FROM templates WHERE created_by = ? AND is_builtin = 0"

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY is_builtin DESC, name ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()

    templates = []
    for row in rows:
        templates.append(Template(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            system_prompt=row["system_prompt"],
            category=TemplateCategory(row["category"]),
            is_builtin=bool(row["is_builtin"]),
            output_format=OutputFormat(row["output_format"]),
            created_by=row["created_by"],
            team_id=row["team_id"],
            created_at=row["created_at"]
        ))

    conn.close()

    return TemplateListResponse(templates=templates, total=len(templates))


@router.post("/templates")
async def create_template(
    request: CreateTemplateRequest = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Create a custom template"""
    user_id = current_user.get("user_id") or current_user.get("id")
    template_id = f"tmpl_{uuid4().hex[:12]}"

    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now(UTC).isoformat()

    cursor.execute("""
        INSERT INTO templates
        (id, name, description, system_prompt, category, is_builtin, output_format, created_by, team_id, created_at)
        VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
    """, (
        template_id,
        request.name,
        request.description,
        request.system_prompt,
        request.category.value,
        request.output_format.value,
        user_id,
        request.team_id,
        now
    ))

    conn.commit()
    conn.close()

    return {"template_id": template_id, "message": "Template created"}


@router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Update a custom template (cannot update built-in templates)"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT is_builtin FROM templates WHERE id = ?", (template_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Template not found")

    if row["is_builtin"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Cannot modify built-in templates")

    # Build updates dict with whitelisted columns only
    updates_dict = {}
    if request.name is not None:
        updates_dict["name"] = request.name
    if request.description is not None:
        updates_dict["description"] = request.description
    if request.system_prompt is not None:
        updates_dict["system_prompt"] = request.system_prompt
    if request.category is not None:
        updates_dict["category"] = request.category.value
    if request.output_format is not None:
        updates_dict["output_format"] = request.output_format.value

    if updates_dict:
        # Use safe builder with whitelist validation
        updates, params = build_safe_update(updates_dict, TEMPLATE_UPDATE_COLUMNS)
        params.append(template_id)
        cursor.execute(f"UPDATE templates SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

    conn.close()

    return {"message": "Template updated", "template_id": template_id}


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Delete a custom template (cannot delete built-in templates)"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT is_builtin FROM templates WHERE id = ?", (template_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Template not found")

    if row["is_builtin"]:
        conn.close()
        raise HTTPException(status_code=403, detail="Cannot delete built-in templates")

    cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
    conn.commit()
    conn.close()

    return {"message": "Template deleted", "template_id": template_id}


# ===== Template Application Endpoints =====

@router.post("/recordings/{recording_id}/apply-template", response_model=ApplyTemplateResponse)
async def apply_template(
    recording_id: str,
    request: ApplyTemplateRequest = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Apply a template to a recording"""
    conn = get_db()
    cursor = conn.cursor()

    # Get recording
    cursor.execute("SELECT transcript FROM recordings WHERE id = ?", (recording_id,))
    rec_row = cursor.fetchone()
    if not rec_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Recording not found")
    transcript = rec_row["transcript"]

    # Get template
    cursor.execute("SELECT * FROM templates WHERE id = ?", (request.template_id,))
    tmpl_row = cursor.fetchone()
    if not tmpl_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Template not found")

    # Apply template
    content = await apply_template_with_ollama(transcript, tmpl_row["system_prompt"])

    # Save output
    output_id = f"out_{uuid4().hex[:12]}"
    now = datetime.now(UTC).isoformat()

    cursor.execute("""
        INSERT INTO formatted_outputs
        (id, recording_id, template_id, template_name, content, format, generated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        output_id, recording_id, request.template_id,
        tmpl_row["name"], content, tmpl_row["output_format"], now
    ))

    conn.commit()
    conn.close()

    return ApplyTemplateResponse(
        output_id=output_id,
        content=content,
        template_name=tmpl_row["name"]
    )


@router.post("/recordings/batch-apply", response_model=BatchApplyResponse)
async def batch_apply_templates(
    request: BatchApplyRequest = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Apply multiple templates to multiple recordings"""
    outputs = []
    failed = 0

    conn = get_db()
    cursor = conn.cursor()

    for recording_id in request.recording_ids:
        # Get recording
        cursor.execute("SELECT transcript FROM recordings WHERE id = ?", (recording_id,))
        rec_row = cursor.fetchone()
        if not rec_row:
            failed += 1
            continue
        transcript = rec_row["transcript"]

        for template_id in request.template_ids:
            try:
                # Get template
                cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
                tmpl_row = cursor.fetchone()
                if not tmpl_row:
                    failed += 1
                    continue

                # Apply template
                content = await apply_template_with_ollama(transcript, tmpl_row["system_prompt"])

                # Save output
                output_id = f"out_{uuid4().hex[:12]}"
                now = datetime.now(UTC).isoformat()

                cursor.execute("""
                    INSERT INTO formatted_outputs
                    (id, recording_id, template_id, template_name, content, format, generated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    output_id, recording_id, template_id,
                    tmpl_row["name"], content, tmpl_row["output_format"], now
                ))

                outputs.append(FormattedOutput(
                    id=output_id,
                    recording_id=recording_id,
                    template_id=template_id,
                    template_name=tmpl_row["name"],
                    content=content,
                    format=OutputFormat(tmpl_row["output_format"]),
                    generated_at=now
                ))

            except Exception as e:
                logger.error(f"Batch apply failed for {recording_id}/{template_id}: {e}")
                failed += 1

    conn.commit()
    conn.close()

    return BatchApplyResponse(
        outputs=outputs,
        total_processed=len(outputs),
        failed=failed,
        message=f"Processed {len(outputs)} outputs, {failed} failed"
    )


@router.get("/recordings/{recording_id}/outputs")
async def list_recording_outputs(
    recording_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """List all formatted outputs for a recording"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM formatted_outputs WHERE recording_id = ? ORDER BY generated_at DESC", (recording_id,))
    rows = cursor.fetchall()

    outputs = []
    for row in rows:
        outputs.append(FormattedOutput(
            id=row["id"],
            recording_id=row["recording_id"],
            template_id=row["template_id"],
            template_name=row["template_name"],
            content=row["content"],
            format=OutputFormat(row["format"]),
            generated_at=row["generated_at"]
        ))

    conn.close()

    return {"outputs": outputs, "total": len(outputs)}


@router.delete("/outputs/{output_id}")
async def delete_output(
    output_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Delete a formatted output"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM formatted_outputs WHERE id = ?", (output_id,))

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Output not found")

    conn.commit()
    conn.close()

    return {"message": "Output deleted", "output_id": output_id}


# ===== Legacy Endpoints (kept for compatibility) =====

class TranscribeResponse(BaseModel):
    transcript: str
    duration_seconds: Optional[float] = None
    language: Optional[str] = None


class AnalyzeRequest(BaseModel):
    transcript: str
    document_title: Optional[str] = None


class AnalyzeResponse(BaseModel):
    analysis: str
    themes: list[str] = []
    key_insights: list[str] = []


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(request: Request, audio_file: UploadFile = File(...)):
    """
    Legacy endpoint: Transcribe audio file without saving to vault.
    Use POST /recordings for the new flow with persistent storage.
    """
    safe_filename = sanitize_filename(audio_file.filename or "audio")
    valid_extensions = ['.m4a', '.mp3', '.wav', '.webm', '.mp4', '.ogg']
    file_ext = Path(safe_filename).suffix.lower()

    if file_ext not in valid_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Supported: {', '.join(valid_extensions)}"
        )

    file_id = uuid4().hex[:12]
    audio_path = INSIGHTS_DIR / "audio" / f"{file_id}{file_ext}"
    audio_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        async with aiofiles.open(audio_path, 'wb') as f:
            content = await audio_file.read()
            await f.write(content)

        result = await asyncio.to_thread(transcribe_audio_with_whisper, audio_path)

        return TranscribeResponse(
            transcript=result["transcript"],
            language=result.get("language"),
            duration_seconds=result.get("duration")
        )

    finally:
        # Legacy behavior: clean up temp file
        if audio_path.exists():
            audio_path.unlink()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_transcript(req: Request, request: AnalyzeRequest):
    """
    Legacy endpoint: Analyze transcript with theological reflection prompt.
    Use POST /recordings/{id}/apply-template with tmpl_sermon_outline for similar results.
    """
    if not request.transcript or len(request.transcript.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Transcript is too short (minimum 10 characters)"
        )

    system_prompt = """You are a thoughtful theological reflection assistant.
Organize scattered thoughts, surface key insights, connect ideas to Scripture,
and suggest probing questions for deeper study.
Highlight profound insights with a lightbulb emoji.
Maintain reverence for the sacred nature of spiritual growth."""

    user_prompt = f"""Analyze this theological reflection{f" titled '{request.document_title}'" if request.document_title else ""}:

{request.transcript}

Provide a thoughtful analysis that helps organize these thoughts and surface the key spiritual insights."""

    try:
        from chat_service import ollama_client

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        full_response = ""
        async for chunk in ollama_client.chat(
            model="qwen2.5-coder:7b-instruct",
            messages=messages,
            temperature=0.7,
            top_p=0.9
        ):
            full_response += chunk

        # Extract themes
        themes = []
        keywords = ["grace", "faith", "love", "mercy", "salvation", "redemption", "forgiveness", "hope", "prayer", "worship"]
        for kw in keywords:
            if kw.lower() in request.transcript.lower():
                themes.append(kw.capitalize())

        # Extract insights
        key_insights = [line.strip() for line in full_response.split("\n") if "💡" in line][:3]

        return AnalyzeResponse(
            analysis=full_response,
            themes=themes[:5],
            key_insights=key_insights
        )

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export router
__all__ = ["router"]
