"""
Insights Lab Recording Routes

CRUD endpoints for voice recordings.
"""

import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Any, Dict
from datetime import datetime, UTC
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile, File, Request, Form, Depends
from api.errors import http_400, http_404, http_500

from api.auth_middleware import get_current_user
from api.utils import sanitize_filename, get_user_id
from api.schemas.insights_models import (
    Recording, CreateRecordingResponse, RecordingListResponse, UpdateRecordingRequest
)

from ..database import (
    get_db, build_safe_update, RECORDINGS_DIR, RECORDING_UPDATE_COLUMNS
)
from ..transcription import transcribe_audio_with_whisper, get_audio_duration
from ..template_engine import auto_apply_default_templates

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Recordings"])


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
    user_id = get_user_id(current_user)

    # Validate file type
    safe_filename = sanitize_filename(audio_file.filename or "audio")
    valid_extensions = ['.m4a', '.mp3', '.wav', '.webm', '.mp4', '.ogg']
    file_ext = Path(safe_filename).suffix.lower()

    if file_ext not in valid_extensions:
        raise http_400(f"Unsupported audio format. Supported: {', '.join(valid_extensions)}")

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
        raise http_500(str(e))


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
    user_id = get_user_id(current_user)

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
) -> Dict[str, Any]:
    """Get a single recording with all its formatted outputs"""
    from api.schemas.insights_models import FormattedOutput, OutputFormat

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM recordings WHERE id = ?", (recording_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise http_404("Recording not found", resource="recording")

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
) -> Dict[str, str]:
    """Update recording metadata"""
    conn = get_db()
    cursor = conn.cursor()

    # Check exists
    cursor.execute("SELECT id FROM recordings WHERE id = ?", (recording_id,))
    if not cursor.fetchone():
        conn.close()
        raise http_404("Recording not found", resource="recording")

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
) -> Dict[str, str]:
    """Delete a recording and its outputs"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT file_path FROM recordings WHERE id = ?", (recording_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise http_404("Recording not found", resource="recording")

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


__all__ = ["router"]
