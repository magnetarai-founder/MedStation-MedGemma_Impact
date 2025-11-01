"""
Insights Lab Service

"The Lord is my rock, my firm foundation." - Psalm 18:2

Voice transcription and AI analysis for theological reflections.
Designed for missionaries to capture and analyze their spiritual journey.
"""

import os
import asyncio
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime
import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from pydantic import BaseModel
import aiofiles

logger = logging.getLogger(__name__)

# Storage paths
from config_paths import get_config_paths
PATHS = get_config_paths()
INSIGHTS_UPLOADS_DIR = PATHS.data_dir / "insights" / "audio"
INSIGHTS_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

from fastapi import Depends
from auth_middleware import get_current_user

router = APIRouter(
    prefix="/api/v1/insights",
    tags=["Insights"],
    dependencies=[Depends(get_current_user)]  # Require auth
)


# ===== Models =====

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


# ===== Whisper Integration =====

def transcribe_audio_with_whisper(audio_path: Path) -> dict:
    """
    Transcribe audio using Whisper (local)

    This uses whisper.cpp or the Python whisper library.
    Falls back to Ollama if Whisper is not available.
    """
    try:
        # Try whisper.cpp first (faster, C++ implementation)
        import subprocess

        # Check if whisper.cpp is available
        whisper_cpp_path = Path.home() / "whisper.cpp" / "main"

        if whisper_cpp_path.exists():
            logger.info("Using whisper.cpp for transcription")

            # Run whisper.cpp
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
                # Read the output text file
                txt_path = audio_path.with_suffix('.txt')
                if txt_path.exists():
                    transcript = txt_path.read_text().strip()
                    txt_path.unlink()  # Clean up

                    return {
                        "transcript": transcript,
                        "language": "en",
                        "method": "whisper.cpp"
                    }

        # Fall back to Python whisper library with Metal 4 acceleration
        try:
            import whisper
            import torch
            from metal4_engine import get_metal4_engine

            logger.info("Using Python whisper library for transcription")

            # ===== METAL 4 TICK FLOW =====
            # Use Metal 4 engine for optimal device selection and tick flow
            metal4_engine = get_metal4_engine()

            # Kick frame to start tick (enables parallel operations)
            metal4_engine.kick_frame()

            device = metal4_engine.get_device()

            # Get Metal 4 optimization settings for inference
            optimization_settings = metal4_engine.optimize_for_operation('inference')

            logger.info(f"✓ Using device: {device}")
            logger.info(f"   Metal version: {metal4_engine.capabilities.version.value}")
            logger.info(f"   FP16: {optimization_settings['use_fp16']}")
            logger.info(f"   ANE: {optimization_settings.get('use_ane', False)}")
            logger.info(f"   Frame: {metal4_engine.frame_counter}")

            import time
            transcribe_start = time.time()

            model = whisper.load_model("base", device=device)
            result = model.transcribe(
                str(audio_path),
                fp16=optimization_settings['use_fp16'],  # Use Metal 4 optimized FP16
                language="en"  # Optimize by specifying English
            )

            transcribe_elapsed = (time.time() - transcribe_start) * 1000
            logger.info(f"⚡ Whisper transcription: {transcribe_elapsed:.2f}ms")

            # Record operation in diagnostics
            try:
                from metal4_diagnostics import get_diagnostics
                diag = get_diagnostics()
                if diag:
                    diag.record_operation('transcriptions', transcribe_elapsed, 'ml')
            except:
                pass
            # ===== END METAL 4 TICK FLOW =====

            return {
                "transcript": result["text"].strip(),
                "language": result.get("language", "en"),
                "method": f"whisper-python-{device}"
            }

        except ImportError as e:
            logger.warning(f"Whisper not available: {e}")

    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}", exc_info=True)

    # Final fallback: Use Ollama with a transcription-capable model
    # (This requires a model that can process audio, which most don't support yet)
    raise HTTPException(
        status_code=503,
        detail="Whisper transcription not available. Please install whisper.cpp or Python whisper library."
    )


# ===== AI Analysis =====

async def analyze_transcript_with_ai(transcript: str, title: Optional[str] = None) -> dict:
    """
    Analyze theological reflection transcript with AI

    Uses specialized prompt for organizing scattered thoughts,
    surfacing key insights, and connecting ideas.
    """
    try:
        from chat_service import ollama_client

        # Specialized system prompt for theological reflection analysis
        system_prompt = """You are a thoughtful theological reflection assistant designed to help missionaries and spiritual seekers organize and deepen their understanding of Scripture and spiritual experiences.

Your role is to:
1. **Organize scattered thoughts** - Take stream-of-consciousness reflections and structure them coherently
2. **Surface key insights** - Identify the most profound spiritual revelations, even if they seem hidden
3. **Connect ideas** - Find theological connections between different thoughts and Scripture passages
4. **Ask probing questions** - Suggest deeper questions for further reflection
5. **Maintain reverence** - Approach all reflections with respect for the sacred nature of spiritual growth

When analyzing a reflection:
- Start with a brief summary of the main themes
- Organize thoughts into clear categories (Scripture insights, personal applications, questions, action items)
- Highlight any particularly profound insights with 💡
- Note connections to broader theological themes
- Suggest 2-3 follow-up questions for deeper study
- Keep the tone warm, encouraging, and spiritually sensitive

Remember: You're not preaching or teaching, but helping someone process their own spiritual journey."""

        user_prompt = f"""Please analyze this theological reflection{f" titled '{title}'" if title else ""}:

---
{transcript}
---

Provide a thoughtful analysis that helps organize these thoughts and surface the key spiritual insights."""

        # Build messages for Ollama
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Stream response from Ollama
        full_response = ""
        async for chunk in ollama_client.chat(
            model="qwen2.5-coder:7b-instruct",  # Use default model
            messages=messages,
            temperature=0.7,
            top_p=0.9
        ):
            full_response += chunk

        # Extract themes and insights (simple keyword extraction)
        themes = []
        key_insights = []

        # Look for common theological themes
        theme_keywords = ["grace", "faith", "love", "mercy", "salvation", "redemption", "forgiveness", "hope", "prayer", "worship"]
        for keyword in theme_keywords:
            if keyword.lower() in transcript.lower():
                themes.append(keyword.capitalize())

        # Look for insight markers in the analysis
        if "💡" in full_response:
            lines = full_response.split("\n")
            for line in lines:
                if "💡" in line:
                    key_insights.append(line.strip())

        return {
            "analysis": full_response,
            "themes": themes[:5],  # Limit to top 5
            "key_insights": key_insights[:3]  # Limit to top 3
        }

    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI analysis failed: {str(e)}"
        )


# ===== Endpoints =====

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(request: Request, audio_file: UploadFile = File(...)):
    """
    Transcribe audio file using Whisper (local)

    Supports: .m4a, .mp3, .wav, .webm, .mp4
    """
    # Validate file type
    valid_extensions = ['.m4a', '.mp3', '.wav', '.webm', '.mp4', '.ogg']
    file_ext = Path(audio_file.filename).suffix.lower()

    if file_ext not in valid_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format. Supported: {', '.join(valid_extensions)}"
        )

    # Save uploaded file
    file_id = uuid.uuid4().hex[:12]
    audio_path = INSIGHTS_UPLOADS_DIR / f"{file_id}{file_ext}"

    try:
        async with aiofiles.open(audio_path, 'wb') as f:
            content = await audio_file.read()
            await f.write(content)

        logger.info(f"Transcribing audio file: {audio_file.filename} ({len(content)} bytes)")

        # Transcribe with Whisper
        result = await asyncio.to_thread(transcribe_audio_with_whisper, audio_path)

        logger.info(f"Transcription complete: {len(result['transcript'])} characters")

        return TranscribeResponse(
            transcript=result["transcript"],
            language=result.get("language")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up audio file
        if audio_path.exists():
            audio_path.unlink()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_transcript(req: Request, request: AnalyzeRequest):
    """
    Analyze theological reflection transcript with AI

    Organizes scattered thoughts, surfaces key insights,
    and provides spiritual analysis.
    """
    if not request.transcript or len(request.transcript.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Transcript is too short (minimum 10 characters)"
        )

    try:
        logger.info(f"Analyzing transcript: {len(request.transcript)} characters")

        result = await analyze_transcript_with_ai(
            request.transcript,
            request.document_title
        )

        logger.info("Analysis complete")

        return AnalyzeResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export router
__all__ = ["router"]
