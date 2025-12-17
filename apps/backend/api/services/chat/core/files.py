"""
Chat service - File management operations.

Handles file uploads to chat sessions with:
- File text extraction
- RAG chunk creation
- Embedding generation
"""

import uuid
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, UTC

from .lazy_init import _get_memory, _get_chat_uploads_dir

logger = logging.getLogger(__name__)


async def upload_file_to_chat(chat_id: str, filename: str, content: bytes, content_type: str) -> Dict[str, Any]:
    """Upload a file to a chat session"""
    from api.chat_enhancements import FileTextExtractor, DocumentChunker
    try:
        from api.utils import sanitize_filename, sanitize_for_log
    except ImportError:
        from utils import sanitize_filename, sanitize_for_log
    import aiofiles

    memory = _get_memory()
    uploads_dir = _get_chat_uploads_dir()

    # Sanitize filename
    safe_filename = sanitize_filename(filename)

    # Generate unique filename
    file_id = uuid.uuid4().hex[:12]
    file_ext = Path(safe_filename).suffix
    stored_filename = f"{chat_id}_{file_id}{file_ext}"
    file_path = uploads_dir / stored_filename

    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)

    # Extract text if possible
    file_info = {
        "id": file_id,
        "original_name": safe_filename,
        "stored_name": stored_filename,
        "size": len(content),
        "type": content_type,
        "uploaded_at": datetime.now(UTC).isoformat()
    }

    # Try to extract text for RAG
    extracted_text = None
    try:
        extracted_text = await asyncio.to_thread(
            FileTextExtractor.extract,
            file_path,
            content_type
        )

        if extracted_text:
            file_info["text_preview"] = extracted_text[:1000]
            file_info["text_extracted"] = True

            # Create chunks and embeddings for RAG
            chunks = await asyncio.to_thread(
                DocumentChunker.create_chunks_with_metadata,
                extracted_text,
                file_info
            )

            # Store chunks in memory
            await asyncio.to_thread(memory.store_document_chunks, chat_id, chunks)

            file_info["chunks_created"] = len(chunks)
            safe_name = sanitize_for_log(filename)
            logger.info(f"Created {len(chunks)} chunks for file {safe_name}")
        else:
            file_info["text_preview"] = "[Text extraction not supported for this file type]"
            file_info["text_extracted"] = False

    except Exception as e:
        logger.warning(f"Failed to extract text from file: {e}")
        file_info["text_preview"] = f"[Extraction error: {str(e)}]"
        file_info["text_extracted"] = False

    return file_info
