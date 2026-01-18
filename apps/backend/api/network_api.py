"""
Minimal Network API Server

Standalone FastAPI server for LAN Discovery and P2P Mesh
Can run independently of main.py

Usage:
    python3 -m uvicorn api.network_api:app --reload --port 8001
"""

from typing import Any, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MagnetarStudio Network API",
    description="LAN Discovery and P2P Mesh networking for MagnetarStudio",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load LAN Discovery Service
try:
    from api.lan_discovery import router as lan_router
    app.include_router(lan_router)
    logger.info("✓ LAN Discovery service loaded")
except Exception as e:
    logger.warning(f"✗ LAN Discovery not available: {e}")

# Load P2P Mesh Service
try:
    from api.p2p_mesh_service import router as p2p_mesh_router
    app.include_router(p2p_mesh_router)
    logger.info("✓ P2P Mesh service loaded")
except Exception as e:
    logger.warning(f"✗ P2P Mesh not available: {e}")


@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "service": "ElohimOS Network API",
        "status": "running",
        "endpoints": {
            "lan": "/api/v1/lan",
            "p2p": "/api/v1/p2p"
        }
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
