"""
MedGemma inference routes.

Provides /medgemma/generate and /medgemma/status endpoints for the
native app to call MedGemma directly via HuggingFace Transformers.
"""

import json
import logging
import base64
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/medgemma")


class GenerateRequest(BaseModel):
    prompt: str
    system: Optional[str] = "You are an expert medical AI assistant."
    image_base64: Optional[str] = None
    max_tokens: Optional[int] = 1024
    temperature: Optional[float] = 0.3
    stream: Optional[bool] = False


@router.get("/status")
async def medgemma_status():
    """Check if MedGemma model is loaded and ready."""
    from api.services.medgemma import get_medgemma

    svc = get_medgemma()
    return {
        "loaded": svc.loaded,
        "device": svc.device if svc.loaded else None,
        "model": "google/medgemma-1.5-4b-it",
    }


@router.post("/load")
async def medgemma_load():
    """Explicitly load the MedGemma model into memory."""
    from api.services.medgemma import get_medgemma

    svc = get_medgemma()
    ok = await svc.load()
    if ok:
        return {"status": "loaded", "device": svc.device}
    return JSONResponse(
        {"status": "error", "message": "Failed to load model. Check server logs."},
        status_code=500,
    )


@router.post("/generate")
async def medgemma_generate(req: GenerateRequest):
    """Generate a response from MedGemma."""
    from api.services.medgemma import get_medgemma

    svc = get_medgemma()

    # Decode image if provided
    image = None
    if req.image_base64:
        try:
            from PIL import Image

            img_bytes = base64.b64decode(req.image_base64)
            image = Image.open(BytesIO(img_bytes)).convert("RGB")
        except Exception as e:
            return JSONResponse(
                {"error": f"Invalid image: {e}"}, status_code=400
            )

    if req.stream:
        return StreamingResponse(
            _stream_response(svc, req, image),
            media_type="application/x-ndjson",
        )

    response = await svc.generate(
        prompt=req.prompt,
        system_prompt=req.system,
        image=image,
        max_new_tokens=req.max_tokens,
        temperature=req.temperature,
    )

    return {"response": response, "model": "medgemma-1.5-4b-it"}


async def _stream_response(svc, req: GenerateRequest, image):
    """Stream tokens as newline-delimited JSON."""
    async for token in svc.stream_generate(
        prompt=req.prompt,
        system_prompt=req.system,
        image=image,
        max_new_tokens=req.max_tokens,
        temperature=req.temperature,
    ):
        yield json.dumps({"token": token}) + "\n"
    yield json.dumps({"done": True}) + "\n"
