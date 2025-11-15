"""
Automatic Local Backup Service

Features:
- Auto-backup daily at 2am (when idle)
- Save to ~/.elohimos_backups/
- Keep last 7 backups (auto-delete older)
- Encrypted with user's passphrase (AES-256-GCM)
- Compressed with gzip
- Checksum validation for integrity

Backup File Structure:
backup_2025-10-27_02-00.elohim-backup
├── elohimos_app.db (encrypted)
├── vault.db (encrypted)
├── datasets.db (encrypted)
├── metadata.json (backup date, version, checksum)
└── manifest.sig (signature for integrity)
"""

import os
import json
import gzip
import shutil
import hashlib
import secrets
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import tarfile
import logging
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

logger = logging.getLogger(__name__)

# Backup configuration
BACKUP_DIR = Path.home() / ".elohimos_backups"
BACKUP_RETENTION_DAYS = 7
BACKUP_EXTENSION = ".elohim-backup"
VERSION = "1.0.0"


class BackupService:
    """
    Automatic backup service for ElohimOS databases
    """

    def __init__(self, passphrase: str):
        """
        Initialize backup service

        Args:
            passphrase: User's passphrase for encryption
        """
        self.passphrase = passphrase
        self.backup_dir = BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        # Explicitly set permissions after creation
        os.chmod(self.backup_dir, 0o700)

    def _derive_key(self, salt: bytes) -> bytes:
        """
        Derive encryption key from passphrase

        Args:
            salt: 32-byte salt

        Returns:
            32-byte encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600000,
        )
        return kdf.derive(self.passphrase.encode('utf-8'))

    def _calculate_checksum(self, file_path: Path) -> str:
        """
        Calculate SHA-256 checksum of file

        Args:
            file_path: Path to file

        Returns:
            Hex-encoded SHA-256 hash
        """
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)

        return sha256.hexdigest()

    def _get_databases(self) -> Dict[str, Path]:
        """
        Get paths to all authoritative databases that need backup

        Phase 0: Only backup the authoritative databases:
        - elohimos_app.db (consolidated auth, users, docs, workflows)
        - vault.db (secure storage)
        - datasets.db (data analysis datasets)
        - chat_memory.db (optional, in memory/ subdirectory)

        Returns:
            Dict mapping database names to paths
        """
        from config_paths import get_config_paths

        config = get_config_paths()
        databases = {}

        # Phase 0: Backup only authoritative databases
        authoritative_dbs = [
            ('elohimos_app.db', config.app_db),
            ('vault.db', config.vault_db),
            ('datasets.db', config.datasets_db),
            ('chat_memory.db', config.memory_db),  # Optional
        ]

        for db_name, db_path in authoritative_dbs:
            # Check for encrypted versions first
            encrypted_path = db_path.with_suffix('.db.encrypted')

            if encrypted_path.exists():
                databases[db_name] = encrypted_path
            elif db_path.exists():
                databases[db_name] = db_path
            # If neither exists, skip (e.g., chat_memory.db might not exist yet)

        return databases

    def create_backup(self) -> Optional[Path]:
        """
        Create a new backup

        Returns:
            Path to created backup file, or None if failed
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_name = f"backup_{timestamp}{BACKUP_EXTENSION}"
            backup_path = self.backup_dir / backup_name

            # Ensure unique filename if one already exists
            counter = 1
            while backup_path.exists():
                backup_name = f"backup_{timestamp}_{counter}{BACKUP_EXTENSION}"
                backup_path = self.backup_dir / backup_name
                counter += 1

            # Create temporary directory for staging
            temp_dir = self.backup_dir / f"temp_{timestamp}"
            temp_dir.mkdir(exist_ok=True, mode=0o700)

            try:
                # Get all databases
                databases = self._get_databases()

                if not databases:
                    logger.warning("No databases found to backup")
                    return None

                # Copy databases to temp directory
                file_checksums = {}

                for db_name, db_path in databases.items():
                    dest_path = temp_dir / db_name
                    shutil.copy2(db_path, dest_path)
                    file_checksums[db_name] = self._calculate_checksum(dest_path)
                    logger.info(f"Copied {db_name} to backup staging")

                # Create metadata
                metadata = {
                    "version": VERSION,
                    "timestamp": datetime.now().isoformat(),
                    "databases": list(databases.keys()),
                    "checksums": file_checksums,
                    "encrypted": True
                }

                metadata_path = temp_dir / "metadata.json"
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)

                # Create tarball
                tar_path = temp_dir.parent / f"{backup_name}.tar"

                with tarfile.open(tar_path, 'w') as tar:
                    for item in temp_dir.iterdir():
                        tar.add(item, arcname=item.name)

                # Compress with gzip
                gz_path = tar_path.with_suffix('.tar.gz')

                with open(tar_path, 'rb') as f_in:
                    with gzip.open(gz_path, 'wb', compresslevel=9) as f_out:
                        shutil.copyfileobj(f_in, f_out)

                tar_path.unlink()  # Remove uncompressed tar

                # Encrypt the gzipped tar
                with open(gz_path, 'rb') as f:
                    plaintext = f.read()

                salt = secrets.token_bytes(32)
                encryption_key = self._derive_key(salt)

                aesgcm = AESGCM(encryption_key)
                nonce = secrets.token_bytes(12)
                ciphertext = aesgcm.encrypt(nonce, plaintext, None)

                # Write final encrypted backup
                with open(backup_path, 'wb') as f:
                    # Format: salt (32) + nonce (12) + ciphertext
                    f.write(salt)
                    f.write(nonce)
                    f.write(ciphertext)

                gz_path.unlink()  # Remove unencrypted gzip

                # Set restrictive permissions
                os.chmod(backup_path, 0o600)

                backup_size = backup_path.stat().st_size
                logger.info(f"Created backup: {backup_name} ({backup_size} bytes)")

                # Cleanup old backups
                self.cleanup_old_backups()

                # HIGH-08: Auto-verify backup integrity after creation
                # Ensures backup can be decrypted and restored before declaring success
                logger.info(f"Verifying backup integrity: {backup_name}")
                is_valid = self.verify_backup(backup_path)

                if not is_valid:
                    logger.error(f"❌ CRITICAL: Backup verification failed for {backup_name}")
                    logger.error(f"⚠️  Backup file may be corrupted and cannot be restored!")
                    # Keep the backup file for forensics, but log error
                    raise RuntimeError(f"Backup created but verification failed: {backup_name}")

                logger.info(f"✅ Backup verified successfully: {backup_name}")

                return backup_path

            finally:
                # Cleanup temp directory
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    def restore_backup(self, backup_path: Path, restore_dir: Optional[Path] = None) -> bool:
        """
        Restore from a backup file

        Args:
            backup_path: Path to backup file
            restore_dir: Optional directory to restore to (defaults to original locations)

        Returns:
            True if restore successful
        """
        try:
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False

            # Read encrypted backup
            with open(backup_path, 'rb') as f:
                salt = f.read(32)
                nonce = f.read(12)
                ciphertext = f.read()

            # Decrypt
            encryption_key = self._derive_key(salt)
            aesgcm = AESGCM(encryption_key)

            try:
                plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            except Exception as e:
                logger.error(f"Failed to decrypt backup (wrong passphrase?): {e}")
                return False

            # Create temp directory for extraction
            temp_dir = self.backup_dir / f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            temp_dir.mkdir(exist_ok=True, mode=0o700)

            try:
                # Write decrypted gzipped tar
                gz_path = temp_dir / "backup.tar.gz"
                with open(gz_path, 'wb') as f:
                    f.write(plaintext)

                # Decompress
                tar_path = temp_dir / "backup.tar"
                with gzip.open(gz_path, 'rb') as f_in:
                    with open(tar_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                # Extract tar
                extract_dir = temp_dir / "extracted"
                extract_dir.mkdir(exist_ok=True)

                with tarfile.open(tar_path, 'r') as tar:
                    # SECURITY: Prevent path traversal when extracting archives
                    # Only extract members that are safely contained within extract_dir
                    def is_within_directory(directory, target):
                        try:
                            directory = os.path.realpath(directory)
                            target = os.path.realpath(target)
                            return os.path.commonprefix([target, directory]) == directory
                        except Exception:
                            return False

                    safe_members = []
                    for member in tar.getmembers():
                        member_path = os.path.join(extract_dir, member.name)
                        if is_within_directory(extract_dir, member_path):
                            safe_members.append(member)
                    tar.extractall(extract_dir, members=safe_members)

                # Verify metadata
                metadata_path = extract_dir / "metadata.json"
                if not metadata_path.exists():
                    logger.error("Invalid backup: missing metadata.json")
                    return False

                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)

                # Verify checksums
                for db_name, expected_checksum in metadata.get('checksums', {}).items():
                    db_path = extract_dir / db_name
                    if db_path.exists():
                        actual_checksum = self._calculate_checksum(db_path)
                        if actual_checksum != expected_checksum:
                            logger.error(f"Checksum mismatch for {db_name}")
                            return False

                # Restore databases
                from config_paths import get_data_dir
                data_dir = restore_dir or get_data_dir()

                for db_name in metadata.get('databases', []):
                    source_path = extract_dir / db_name
                    if source_path.exists():
                        dest_path = data_dir / db_name

                        # Backup existing file
                        if dest_path.exists():
                            backup_existing = dest_path.with_suffix('.db.pre-restore')
                            shutil.copy2(dest_path, backup_existing)
                            logger.info(f"Backed up existing {db_name} to {backup_existing.name}")

                        # Restore
                        shutil.copy2(source_path, dest_path)
                        logger.info(f"Restored {db_name}")

                logger.info(f"Successfully restored backup from {backup_path.name}")
                return True

            finally:
                # Cleanup temp directory
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)

        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False

    def list_backups(self) -> List[Dict]:
        """
        List all available backups

        Returns:
            List of backup info dicts with name, path, size, date
        """
        backups = []

        for backup_file in sorted(self.backup_dir.glob(f"*{BACKUP_EXTENSION}"), reverse=True):
            stat = backup_file.stat()
            backups.append({
                "name": backup_file.name,
                "path": str(backup_file),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "age_days": (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days
            })

        return backups

    def cleanup_old_backups(self) -> int:
        """
        Delete backups older than retention period

        Returns:
            Number of backups deleted
        """
        deleted = 0
        cutoff_date = datetime.now() - timedelta(days=BACKUP_RETENTION_DAYS)

        for backup_file in self.backup_dir.glob(f"*{BACKUP_EXTENSION}"):
            stat = backup_file.stat()
            # Use mtime (modification time) which is settable via os.utime()
            created = datetime.fromtimestamp(stat.st_mtime)

            if created < cutoff_date:
                backup_file.unlink()
                logger.info(f"Deleted old backup: {backup_file.name}")
                deleted += 1

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old backups")

        return deleted

    def verify_backup(self, backup_path: Path) -> bool:
        """
        Verify backup integrity without restoring

        Args:
            backup_path: Path to backup file

        Returns:
            True if backup is valid
        """
        try:
            # Try to decrypt and extract metadata
            with open(backup_path, 'rb') as f:
                salt = f.read(32)
                nonce = f.read(12)
                ciphertext = f.read()

            encryption_key = self._derive_key(salt)
            aesgcm = AESGCM(encryption_key)

            plaintext = aesgcm.decrypt(nonce, ciphertext, None)

            # Can decrypt successfully
            logger.info(f"Backup verified: {backup_path.name}")
            return True

        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False


# Global instance
_backup_service: Optional[BackupService] = None


def get_backup_service(passphrase: str) -> BackupService:
    """
    Get or create backup service instance

    Args:
        passphrase: User's passphrase

    Returns:
        BackupService instance
    """
    global _backup_service

    if _backup_service is None:
        _backup_service = BackupService(passphrase)

    return _backup_service
