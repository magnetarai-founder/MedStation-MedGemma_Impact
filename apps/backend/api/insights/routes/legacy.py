"""
Insights Lab Legacy Routes

Legacy endpoints kept for backward compatibility.
"""

import asyncio
import logging
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, UploadFile, File, Request
from pydantic import BaseModel

from api.utils import sanitize_filename
from api.errors import http_400, http_500
from ..database import INSIGHTS_DIR
from ..transcription import transcribe_audio_with_whisper

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Legacy"])


class TranscribeResponse(BaseModel):
    transcript: str
    duration_seconds: float | None = None
    language: str | None = None


class AnalyzeRequest(BaseModel):
    transcript: str
    document_title: str | None = None


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
        raise http_400(f"Unsupported audio format. Supported: {', '.join(valid_extensions)}")

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
        raise http_400("Transcript is too short (minimum 10 characters)")

    system_prompt = """You are a thoughtful theological reflection assistant.
Organize scattered thoughts, surface key insights, connect ideas to Scripture,
and suggest probing questions for deeper study.
Highlight profound insights with a lightbulb emoji.
Maintain reverence for the sacred nature of spiritual growth."""

    user_prompt = f"""Analyze this theological reflection{f" titled '{request.document_title}'" if request.document_title else ""}:

{request.transcript}

Provide a thoughtful analysis that helps organize these thoughts and surface the key spiritual insights."""

    try:
        from api.services.chat import get_ollama_client
        ollama_client = get_ollama_client()

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
        raise http_500("Analysis failed")


__all__ = ["router"]
