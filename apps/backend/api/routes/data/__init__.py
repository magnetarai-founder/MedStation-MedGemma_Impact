"""Data routes - NLQ, Pattern Discovery, Semantic Search, etc."""

__all__ = ["router"]

from fastapi import APIRouter

# Import sub-routers
from . import nlq, profiler, semantic_search

router = APIRouter(
    prefix="/api/v1/data",
    tags=["Data"]
)

# Include all sub-routers
router.include_router(nlq.router)
router.include_router(profiler.router)
router.include_router(semantic_search.router)
