"""
Insights Lab Transcription Module

Whisper transcription logic for audio files.
"""

import logging
import subprocess
from pathlib import Path

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def transcribe_audio_with_whisper(audio_path: Path) -> dict:
    """
    Transcribe audio using Whisper (local)
    Tries whisper.cpp first, falls back to Python whisper with Metal 4.
    """
    try:
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
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


__all__ = ["transcribe_audio_with_whisper", "get_audio_duration"]
