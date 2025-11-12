"""
File upload utilities for session-based file handling.

Contains helpers for secure file upload, validation, and storage.
"""

import uuid
from pathlib import Path
from fastapi import UploadFile
import aiofiles


async def save_upload(upload_file: UploadFile) -> Path:
    """Save uploaded file to temp directory"""
    # Import here to avoid circular dependency
    from api.utils import sanitize_filename

    # Get the directory where the API module is located
    api_dir = Path(__file__).parent.parent
    temp_dir = api_dir / "temp_uploads"
    temp_dir.mkdir(exist_ok=True)

    # Sanitize filename to prevent path traversal (HIGH-01)
    safe_filename = sanitize_filename(upload_file.filename)
    file_path = temp_dir / f"{uuid.uuid4()}_{safe_filename}"

    # Stream upload to disk in chunks to avoid memory spikes
    chunk_size = 16 * 1024 * 1024  # 16MB
    async with aiofiles.open(file_path, 'wb') as f:
        while True:
            chunk = await upload_file.read(chunk_size)
            if not chunk:
                break
            await f.write(chunk)

    return file_path
