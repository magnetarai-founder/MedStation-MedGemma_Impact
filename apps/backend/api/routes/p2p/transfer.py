"""
P2P Chunked File Transfer Endpoints (skeleton).

Endpoints (to implement):
- POST /api/v1/p2p/transfer/init
- POST /api/v1/p2p/transfer/upload-chunk
- POST /api/v1/p2p/transfer/commit
- GET  /api/v1/p2p/transfer/status/{transfer_id}

Notes:
- Store temp chunks under PATHS.shared_files_dir / "temp" / {transfer_id}
- Enforce auth via Depends(get_current_user)
- Add per-chunk SHA-256 and final integrity verification
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.auth_middleware import get_current_user
from api.config_paths import PATHS


router = APIRouter(prefix="/api/v1/p2p/transfer", tags=["p2p-transfer"], dependencies=[Depends(get_current_user)])


class InitRequest(BaseModel):
    filename: str
    size_bytes: int = Field(ge=0)
    mime_type: Optional[str] = None


class InitResponse(BaseModel):
    transfer_id: str
    chunk_size: int


@router.post("/init", response_model=InitResponse)
async def init_transfer(body: InitRequest):
    """Initialize a new transfer and allocate a temp directory.

    TODO: generate transfer_id, create temp dir, persist metadata.
    """
    return InitResponse(transfer_id="TBD", chunk_size=4 * 1024 * 1024)


@router.post("/upload-chunk")
async def upload_chunk(
    transfer_id: str = Form(...),
    index: int = Form(...),
    checksum: str = Form(...),
    chunk: UploadFile = File(...),
):
    """Upload a chunk for a given transfer.

    TODO: write to PATHS.shared_files_dir / temp / {transfer_id} / chunk_{index}
    TODO: verify checksum and return status; handle resume.
    """
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})


class CommitRequest(BaseModel):
    transfer_id: str
    expected_sha256: Optional[str] = None


@router.post("/commit")
async def commit_transfer(body: CommitRequest):
    """Commit a transfer: verify chunks, merge, compute final hash.

    TODO: merge, compute SHA-256, compare expected, move to final location.
    """
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})


@router.get("/status/{transfer_id}")
async def get_status(transfer_id: str):
    """Return transfer status and missing chunks list.

    TODO: read metadata, return uploaded indices and next missing.
    """
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})

