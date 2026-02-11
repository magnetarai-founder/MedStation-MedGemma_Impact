"""
Chat routes package for MedStation.

Only includes MedGemma inference and Ollama proxy (fallback).
"""

__all__ = ["router", "public_router"]

from fastapi import APIRouter

from . import ollama_proxy, medgemma

# Authenticated router (unused for now, kept for structure)
router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat"],
)

# Public router (native app calls directly)
public_router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat-public"]
)

# Ollama proxy is public (native app calls directly)
public_router.include_router(ollama_proxy.router)

# MedGemma routes (public — native app calls directly)
public_router.include_router(medgemma.router)
