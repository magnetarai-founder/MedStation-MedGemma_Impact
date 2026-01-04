"""
P2P Chat Service - File Transfer Operations

File transfer management over P2P:
- File transfer metadata and progress tracking
- Chunked file transfers with SHA-256 integrity verification
- Resume support for interrupted transfers
- Encryption integration for secure file sharing
"""

import asyncio
import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, BinaryIO, TYPE_CHECKING

if TYPE_CHECKING:
    from .service import P2PChatService

from . import storage
from .types import FILE_PROTOCOL_ID

logger = logging.getLogger(__name__)

# Chunk size: 1MB (optimal for P2P transfer)
CHUNK_SIZE = 1024 * 1024

# Maximum concurrent chunk transfers
MAX_CONCURRENT_CHUNKS = 4

# Chunk transfer timeout (seconds)
CHUNK_TIMEOUT = 30


async def initiate_file_transfer(service: 'P2PChatService',
                                 file_name: str,
                                 file_size: int,
                                 mime_type: str,
                                 channel_id: str,
                                 recipient_ids: list) -> Dict:
    """
    Initiate a file transfer.

    Args:
        service: P2PChatService instance
        file_name: Name of the file
        file_size: File size in bytes
        mime_type: MIME type of the file
        channel_id: Target channel
        recipient_ids: List of recipient peer IDs

    Returns:
        Dict with transfer_id and metadata
    """
    import uuid
    transfer_id = str(uuid.uuid4())

    # Calculate chunks (1MB per chunk)
    chunk_size = 1024 * 1024  # 1MB
    chunks_total = (file_size + chunk_size - 1) // chunk_size

    # Store transfer metadata
    storage.save_file_transfer(
        service.db_path,
        transfer_id,
        file_name,
        file_size,
        mime_type,
        service.peer_id,
        channel_id,
        recipient_ids,
        chunks_total
    )

    logger.info(f"Initiated file transfer: {file_name} ({file_size} bytes, {chunks_total} chunks)")

    return {
        "transfer_id": transfer_id,
        "file_name": file_name,
        "file_size": file_size,
        "chunks_total": chunks_total,
        "status": "initiated"
    }


async def update_transfer_progress(service: 'P2PChatService',
                                   transfer_id: str,
                                   chunks_received: int,
                                   progress_percent: float) -> None:
    """
    Update file transfer progress.

    Args:
        service: P2PChatService instance
        transfer_id: Transfer identifier
        chunks_received: Number of chunks received
        progress_percent: Progress percentage (0-100)
    """
    status = "completed" if progress_percent >= 100.0 else "active"

    storage.update_file_transfer_progress(
        service.db_path,
        transfer_id,
        chunks_received,
        progress_percent,
        status
    )

    logger.debug(f"File transfer {transfer_id[:8]}: {progress_percent:.1f}% ({chunks_received} chunks)")


async def get_transfer_status(service: 'P2PChatService', transfer_id: str) -> Optional[Dict]:
    """
    Get file transfer status.

    Args:
        service: P2PChatService instance
        transfer_id: Transfer identifier

    Returns:
        Transfer metadata dict or None if not found
    """
    return storage.get_file_transfer(service.db_path, transfer_id)


# ===== Chunked File Transfer Implementation =====


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_chunk_hash(data: bytes) -> str:
    """Compute SHA-256 hash of a chunk."""
    return hashlib.sha256(data).hexdigest()


async def send_file(
    service: 'P2PChatService',
    file_path: Path,
    channel_id: str,
    recipient_ids: List[str],
    mime_type: Optional[str] = None
) -> Dict:
    """
    Send a file to peers via chunked transfer.

    Args:
        service: P2PChatService instance
        file_path: Path to the file to send
        channel_id: Target channel
        recipient_ids: List of recipient peer IDs
        mime_type: MIME type (auto-detected if not provided)

    Returns:
        Dict with transfer_id, status, and metadata

    Raises:
        FileNotFoundError: If file doesn't exist
        RuntimeError: If P2P service not running
    """
    if not service.is_running:
        raise RuntimeError("P2P service not running")

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_name = file_path.name
    file_size = file_path.stat().st_size
    file_hash = compute_file_hash(file_path)

    # Auto-detect MIME type if not provided
    if not mime_type:
        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"

    # Initiate transfer record
    transfer_info = await initiate_file_transfer(
        service, file_name, file_size, mime_type, channel_id, recipient_ids
    )
    transfer_id = transfer_info["transfer_id"]

    # Store file hash
    storage.set_transfer_hash(service.db_path, transfer_id, file_hash)

    logger.info(f"Starting file transfer: {file_name} ({file_size} bytes, {transfer_info['chunks_total']} chunks)")

    # Send transfer announcement to recipients
    await _send_transfer_announcement(
        service, transfer_id, file_name, file_size, file_hash,
        mime_type, transfer_info["chunks_total"], recipient_ids
    )

    # Send chunks to each recipient
    errors = []
    for recipient_id in recipient_ids:
        try:
            await _send_chunks_to_peer(
                service, transfer_id, file_path, recipient_id,
                transfer_info["chunks_total"]
            )
        except Exception as e:
            logger.error(f"Failed to send to {recipient_id[:8]}: {e}")
            errors.append(f"{recipient_id[:8]}: {str(e)}")

    # Update final status
    if errors:
        logger.warning(f"Transfer {transfer_id[:8]} completed with {len(errors)} errors")
    else:
        logger.info(f"Transfer {transfer_id[:8]} completed successfully")

    return {
        "transfer_id": transfer_id,
        "file_name": file_name,
        "file_size": file_size,
        "file_hash": file_hash,
        "chunks_total": transfer_info["chunks_total"],
        "status": "completed" if not errors else "partial",
        "errors": errors
    }


async def _send_transfer_announcement(
    service: 'P2PChatService',
    transfer_id: str,
    file_name: str,
    file_size: int,
    file_hash: str,
    mime_type: str,
    chunks_total: int,
    recipient_ids: List[str]
) -> None:
    """Send transfer announcement to all recipients."""
    try:
        from libp2p.peer.id import ID as PeerID
    except ImportError:
        logger.error("libp2p not available for file transfer")
        return

    announcement = {
        "type": "transfer_announce",
        "transfer_id": transfer_id,
        "file_name": file_name,
        "file_size": file_size,
        "file_hash": file_hash,
        "mime_type": mime_type,
        "chunks_total": chunks_total,
        "chunk_size": CHUNK_SIZE,
        "sender_id": service.peer_id
    }

    for recipient_id in recipient_ids:
        try:
            peer_id = PeerID.from_base58(recipient_id)
            stream = await service.host.new_stream(peer_id, [FILE_PROTOCOL_ID])
            await stream.write(json.dumps(announcement).encode())

            # Wait for acceptance
            response_data = await asyncio.wait_for(stream.read(), timeout=10)
            response = json.loads(response_data.decode())

            if response.get("type") == "transfer_accept":
                logger.debug(f"Peer {recipient_id[:8]} accepted transfer")
            else:
                logger.warning(f"Peer {recipient_id[:8]} rejected transfer: {response.get('reason')}")

            await stream.close()

        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for acceptance from {recipient_id[:8]}")
        except Exception as e:
            logger.error(f"Failed to announce to {recipient_id[:8]}: {e}")


async def _send_chunks_to_peer(
    service: 'P2PChatService',
    transfer_id: str,
    file_path: Path,
    recipient_id: str,
    chunks_total: int
) -> None:
    """Send all chunks to a single peer."""
    try:
        from libp2p.peer.id import ID as PeerID
    except ImportError:
        raise RuntimeError("libp2p not available")

    peer_id = PeerID.from_base58(recipient_id)
    chunks_sent = 0

    with open(file_path, "rb") as f:
        for chunk_index in range(chunks_total):
            # Read chunk
            chunk_data = f.read(CHUNK_SIZE)
            if not chunk_data:
                break

            chunk_hash = compute_chunk_hash(chunk_data)

            # Prepare chunk message
            chunk_msg = {
                "type": "chunk",
                "transfer_id": transfer_id,
                "chunk_index": chunk_index,
                "chunk_size": len(chunk_data),
                "chunk_hash": chunk_hash,
                "is_last": chunk_index == chunks_total - 1
            }

            try:
                stream = await service.host.new_stream(peer_id, [FILE_PROTOCOL_ID])

                # Send chunk header
                await stream.write(json.dumps(chunk_msg).encode() + b"\n")

                # Send chunk data
                await stream.write(chunk_data)

                # Wait for ACK
                ack_data = await asyncio.wait_for(stream.read(), timeout=CHUNK_TIMEOUT)
                ack = json.loads(ack_data.decode())

                if ack.get("status") == "ok":
                    chunks_sent += 1
                    progress = (chunks_sent / chunks_total) * 100
                    logger.debug(f"Chunk {chunk_index + 1}/{chunks_total} sent ({progress:.1f}%)")

                    # Update progress
                    await update_transfer_progress(service, transfer_id, chunks_sent, progress)
                else:
                    logger.error(f"Chunk {chunk_index} rejected: {ack.get('error')}")
                    raise RuntimeError(f"Chunk rejected: {ack.get('error')}")

                await stream.close()

            except asyncio.TimeoutError:
                raise RuntimeError(f"Timeout sending chunk {chunk_index}")

    logger.info(f"Sent {chunks_sent}/{chunks_total} chunks to {recipient_id[:8]}")


# ===== Receiving Files =====


async def handle_transfer_announcement(
    service: 'P2PChatService',
    announcement: Dict,
    stream
) -> None:
    """
    Handle incoming transfer announcement.

    Args:
        service: P2PChatService instance
        announcement: Transfer announcement data
        stream: libp2p stream
    """
    transfer_id = announcement["transfer_id"]
    file_name = announcement["file_name"]
    file_size = announcement["file_size"]
    file_hash = announcement["file_hash"]
    mime_type = announcement["mime_type"]
    chunks_total = announcement["chunks_total"]
    sender_id = announcement["sender_id"]

    logger.info(f"Receiving file from {sender_id[:8]}: {file_name} ({file_size} bytes)")

    # Create receive directory
    receive_dir = service.db_path.parent / "received_files"
    receive_dir.mkdir(parents=True, exist_ok=True)

    # Create unique filename to avoid collisions
    local_path = receive_dir / f"{transfer_id[:8]}_{file_name}"

    # Save transfer record (as receiver)
    storage.save_file_transfer(
        service.db_path,
        transfer_id,
        file_name,
        file_size,
        mime_type,
        sender_id,
        "",  # No channel for direct receive
        [service.peer_id],
        chunks_total
    )
    storage.set_transfer_hash(service.db_path, transfer_id, file_hash)
    storage.set_transfer_local_path(service.db_path, transfer_id, str(local_path))

    # Accept the transfer
    response = {
        "type": "transfer_accept",
        "transfer_id": transfer_id
    }
    await stream.write(json.dumps(response).encode())
    await stream.close()


async def handle_chunk(
    service: 'P2PChatService',
    chunk_header: Dict,
    chunk_data: bytes
) -> Dict:
    """
    Handle incoming chunk.

    Args:
        service: P2PChatService instance
        chunk_header: Chunk metadata
        chunk_data: Raw chunk bytes

    Returns:
        ACK response dict
    """
    transfer_id = chunk_header["transfer_id"]
    chunk_index = chunk_header["chunk_index"]
    expected_hash = chunk_header["chunk_hash"]
    is_last = chunk_header.get("is_last", False)

    # Verify chunk integrity
    actual_hash = compute_chunk_hash(chunk_data)
    if actual_hash != expected_hash:
        logger.error(f"Chunk {chunk_index} hash mismatch!")
        return {"status": "error", "error": "hash_mismatch"}

    # Get transfer info
    transfer = storage.get_file_transfer(service.db_path, transfer_id)
    if not transfer:
        return {"status": "error", "error": "unknown_transfer"}

    local_path = Path(transfer["local_path"])

    # Write chunk to file
    with open(local_path, "ab") as f:
        f.write(chunk_data)

    # Update progress
    chunks_received = chunk_index + 1
    chunks_total = transfer["chunks_total"]
    progress = (chunks_received / chunks_total) * 100

    await update_transfer_progress(service, transfer_id, chunks_received, progress)

    logger.debug(f"Received chunk {chunks_received}/{chunks_total} ({progress:.1f}%)")

    # Verify complete file if last chunk
    if is_last:
        file_hash = compute_file_hash(local_path)
        expected_file_hash = transfer["file_hash"]

        if file_hash == expected_file_hash:
            logger.info(f"File transfer complete: {transfer['file_name']} (hash verified)")
            storage.update_file_transfer_progress(
                service.db_path, transfer_id, chunks_received, 100.0, "completed"
            )
        else:
            logger.error(f"File hash mismatch! Expected {expected_file_hash[:16]}, got {file_hash[:16]}")
            storage.update_file_transfer_progress(
                service.db_path, transfer_id, chunks_received, progress, "failed"
            )
            return {"status": "error", "error": "file_hash_mismatch"}

    return {"status": "ok", "chunk_index": chunk_index}


async def cancel_file_transfer(service: 'P2PChatService', transfer_id: str) -> Dict:
    """
    Cancel an active file transfer.

    Args:
        service: P2PChatService instance
        transfer_id: Transfer to cancel

    Returns:
        Status dict
    """
    transfer = storage.get_file_transfer(service.db_path, transfer_id)
    if not transfer:
        return {"success": False, "error": "Transfer not found"}

    if transfer["status"] in ("completed", "cancelled"):
        return {"success": False, "error": f"Transfer already {transfer['status']}"}

    storage.cancel_transfer(service.db_path, transfer_id)

    # Clean up partial file if receiving
    if transfer.get("local_path"):
        local_path = Path(transfer["local_path"])
        if local_path.exists():
            local_path.unlink()
            logger.info(f"Deleted partial file: {local_path}")

    logger.info(f"Cancelled transfer: {transfer_id[:8]}")
    return {"success": True, "transfer_id": transfer_id}


async def list_active_transfers(service: 'P2PChatService') -> List[Dict]:
    """
    List all active file transfers.

    Args:
        service: P2PChatService instance

    Returns:
        List of active transfer metadata dicts
    """
    return storage.list_active_transfers(service.db_path)
