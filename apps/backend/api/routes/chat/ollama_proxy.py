"""
Ollama proxy routes for MedStation native app.

Forwards /ollama/generate and /ollama/models to the local Ollama server.
"""

import logging

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ollama")

OLLAMA_BASE = "http://localhost:11434"


@router.get("/models")
async def list_models():
    """Proxy Ollama /api/tags to list available models."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{OLLAMA_BASE}/api/tags")
            data = resp.json()
            # Return the models array directly (native app expects [OllamaModelInfo])
            return data.get("models", [])
        except Exception as e:
            logger.warning(f"Ollama unreachable: {e}")
            return JSONResponse([], status_code=200)


@router.post("/generate")
async def generate(request: Request):
    """Proxy Ollama /api/generate for medical inference."""
    body = await request.json()
    stream = body.get("stream", False)

    if stream:
        return StreamingResponse(
            _stream_generate(body),
            media_type="application/x-ndjson",
        )

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{OLLAMA_BASE}/api/generate", json=body)
        return resp.json()


async def _stream_generate(body: dict):
    """Stream tokens from Ollama generate endpoint."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", f"{OLLAMA_BASE}/api/generate", json=body) as resp:
            async for line in resp.aiter_lines():
                if line:
                    yield line + "\n"


@router.get("/version")
async def ollama_version():
    """Proxy Ollama version check."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(f"{OLLAMA_BASE}/api/version")
            return resp.json()
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=503)
