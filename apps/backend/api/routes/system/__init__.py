"""System routes for admin monitoring"""

from fastapi import APIRouter
from . import db_health

router = APIRouter(prefix="/system", tags=["system"])
router.include_router(db_health.router)
