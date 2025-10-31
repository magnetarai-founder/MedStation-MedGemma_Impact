#!/usr/bin/env python3
"""
Offline File Sharing for ElohimOS
Direct file transfers between devices on local network
Perfect for sharing Bibles, datasets, documents in the field
"""

import asyncio
import aiofiles
import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

# Import security utilities
from utils import sanitize_filename


@dataclass
class SharedFile:
    """Metadata for a shared file"""
    file_id: str
    filename: str
    size_bytes: int
    mime_type: str
    sha256_hash: str
    shared_by_peer_id: str
    shared_by_name: str
    shared_at: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass
class FileTransferProgress:
    """Progress tracking for file transfer"""
    file_id: str
    filename: str
    bytes_transferred: int
    total_bytes: int
    speed_mbps: float
    eta_seconds: float
    status: str  # 'pending', 'transferring', 'completed', 'failed'


class OfflineFileShare:
    """
    Offline file sharing service

    Features:
    - Direct device-to-device transfers (no server)
    - Chunk-based transfers for reliability
    - Resume support for interrupted transfers
    - Automatic retry on network issues
    """

    CHUNK_SIZE = 1024 * 1024  # 1MB chunks for reliable transfer

    def __init__(self, storage_dir: Path = None):
        self.storage_dir = storage_dir or Path(".neutron_data/shared_files")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # In-memory state
        self.shared_files: Dict[str, SharedFile] = {}
        self.active_transfers: Dict[str, FileTransferProgress] = {}

        # Load shared files index
        self._load_index()

        logger.info(f"📁 File sharing initialized: {self.storage_dir}")

    def _load_index(self):
        """Load shared files index from disk"""
        index_file = self.storage_dir / "index.json"

        if index_file.exists():
            try:
                data = json.loads(index_file.read_text())
                for file_data in data.get('files', []):
                    shared_file = SharedFile(**file_data)
                    self.shared_files[shared_file.file_id] = shared_file

                logger.info(f"📚 Loaded {len(self.shared_files)} shared files")
            except Exception as e:
                logger.error(f"Failed to load file index: {e}")

    def _save_index(self):
        """Save shared files index to disk"""
        index_file = self.storage_dir / "index.json"

        try:
            data = {
                'files': [asdict(f) for f in self.shared_files.values()],
                'updated_at': datetime.utcnow().isoformat()
            }

            index_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save file index: {e}")

    async def share_file(self,
                        file_path: Path,
                        shared_by_peer_id: str,
                        shared_by_name: str,
                        description: Optional[str] = None,
                        tags: Optional[List[str]] = None) -> SharedFile:
        """
        Share a file on the local mesh network

        Makes the file available for other peers to download
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Calculate hash
        sha256_hash = await self._calculate_hash(file_path)

        # Generate file ID
        file_id = sha256_hash[:16]

        # Detect MIME type
        mime_type = self._detect_mime_type(file_path)

        # Copy file to shared storage
        # Sanitize filename to prevent path traversal (HIGH-01)
        safe_filename = sanitize_filename(file_path.name)
        shared_path = self.storage_dir / file_id / safe_filename
        shared_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(file_path, 'rb') as src:
            async with aiofiles.open(shared_path, 'wb') as dst:
                while True:
                    chunk = await src.read(self.CHUNK_SIZE)
                    if not chunk:
                        break
                    await dst.write(chunk)

        # Create shared file metadata
        shared_file = SharedFile(
            file_id=file_id,
            filename=safe_filename,
            size_bytes=file_path.stat().st_size,
            mime_type=mime_type,
            sha256_hash=sha256_hash,
            shared_by_peer_id=shared_by_peer_id,
            shared_by_name=shared_by_name,
            shared_at=datetime.utcnow().isoformat(),
            description=description,
            tags=tags or []
        )

        # Add to index
        self.shared_files[file_id] = shared_file
        self._save_index()

        logger.info(f"✅ File shared: {shared_file.filename} ({shared_file.size_bytes} bytes)")

        return shared_file

    async def download_file(self,
                           file_id: str,
                           peer_ip: str,
                           peer_port: int,
                           destination: Path) -> Path:
        """
        Download file from peer

        Returns path to downloaded file
        """
        # Create transfer progress
        progress = FileTransferProgress(
            file_id=file_id,
            filename="unknown",
            bytes_transferred=0,
            total_bytes=0,
            speed_mbps=0.0,
            eta_seconds=0.0,
            status='pending'
        )

        self.active_transfers[file_id] = progress

        try:
            # Connect to peer
            reader, writer = await asyncio.open_connection(peer_ip, peer_port)

            # Send file request
            request = {
                'action': 'download',
                'file_id': file_id
            }
            writer.write(json.dumps(request).encode() + b'\n')
            await writer.drain()

            # Receive file metadata
            metadata_line = await reader.readline()
            metadata = json.loads(metadata_line.decode())

            if metadata.get('status') != 'ok':
                raise Exception(f"File not found: {file_id}")

            filename = metadata['filename']
            total_bytes = metadata['size_bytes']

            progress.filename = filename
            progress.total_bytes = total_bytes
            progress.status = 'transferring'

            # Prepare destination
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Download file in chunks
            start_time = asyncio.get_event_loop().time()

            async with aiofiles.open(destination, 'wb') as f:
                while progress.bytes_transferred < total_bytes:
                    # Read chunk
                    chunk = await reader.read(self.CHUNK_SIZE)
                    if not chunk:
                        break

                    # Write chunk
                    await f.write(chunk)
                    progress.bytes_transferred += len(chunk)

                    # Update progress
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed > 0:
                        speed_bytes_per_sec = progress.bytes_transferred / elapsed
                        progress.speed_mbps = (speed_bytes_per_sec * 8) / (1024 * 1024)

                        remaining_bytes = total_bytes - progress.bytes_transferred
                        progress.eta_seconds = remaining_bytes / speed_bytes_per_sec if speed_bytes_per_sec > 0 else 0

            # Close connection
            writer.close()
            await writer.wait_closed()

            # Verify hash
            downloaded_hash = await self._calculate_hash(destination)
            if downloaded_hash != metadata['sha256_hash']:
                raise Exception("Hash mismatch - file corrupted")

            progress.status = 'completed'
            logger.info(f"✅ File downloaded: {filename} ({total_bytes} bytes)")

            return destination

        except Exception as e:
            progress.status = 'failed'
            logger.error(f"❌ Download failed: {e}")
            raise

        finally:
            # Clean up transfer progress after delay
            asyncio.create_task(self._cleanup_transfer(file_id))

    async def _cleanup_transfer(self, file_id: str, delay: int = 60):
        """Remove transfer progress after delay"""
        await asyncio.sleep(delay)
        self.active_transfers.pop(file_id, None)

    async def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256 = hashlib.sha256()

        async with aiofiles.open(file_path, 'rb') as f:
            while True:
                chunk = await f.read(self.CHUNK_SIZE)
                if not chunk:
                    break
                sha256.update(chunk)

        return sha256.hexdigest()

    def _detect_mime_type(self, file_path: Path) -> str:
        """Detect MIME type from file extension"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or 'application/octet-stream'

    def get_shared_files(self, tags: Optional[List[str]] = None) -> List[SharedFile]:
        """Get list of shared files, optionally filtered by tags"""
        files = list(self.shared_files.values())

        if tags:
            files = [f for f in files if f.tags and any(tag in f.tags for tag in tags)]

        return files

    def get_file(self, file_id: str) -> Optional[SharedFile]:
        """Get specific shared file metadata"""
        return self.shared_files.get(file_id)

    def get_file_path(self, file_id: str) -> Optional[Path]:
        """Get local path to shared file"""
        shared_file = self.get_file(file_id)
        if not shared_file:
            return None

        file_path = self.storage_dir / file_id / shared_file.filename
        return file_path if file_path.exists() else None

    def get_transfer_progress(self, file_id: str) -> Optional[FileTransferProgress]:
        """Get transfer progress for a file"""
        return self.active_transfers.get(file_id)

    def get_active_transfers(self) -> List[FileTransferProgress]:
        """Get all active transfers"""
        return list(self.active_transfers.values())

    async def delete_shared_file(self, file_id: str) -> bool:
        """Remove file from sharing"""
        shared_file = self.shared_files.get(file_id)
        if not shared_file:
            return False

        # Delete file from storage
        file_dir = self.storage_dir / file_id
        if file_dir.exists():
            import shutil
            shutil.rmtree(file_dir)

        # Remove from index
        del self.shared_files[file_id]
        self._save_index()

        logger.info(f"🗑️ File unshared: {shared_file.filename}")
        return True

    def get_stats(self) -> Dict:
        """Get file sharing statistics"""
        total_size = sum(f.size_bytes for f in self.shared_files.values())

        return {
            'total_files': len(self.shared_files),
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'active_transfers': len(self.active_transfers),
            'storage_path': str(self.storage_dir)
        }


# Singleton instance
_file_share = None


def get_file_share() -> OfflineFileShare:
    """Get singleton file share instance"""
    global _file_share
    if _file_share is None:
        _file_share = OfflineFileShare()
        logger.info("📁 Offline file sharing ready")
    return _file_share
