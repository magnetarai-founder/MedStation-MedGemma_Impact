"""
Encrypted Audit Logger - AES-256-GCM Encryption at Rest

Wraps the standard audit logger with transparent encryption/decryption.
All audit logs are encrypted before being written to disk.

Security Features:
- AES-256-GCM authenticated encryption
- Each log entry encrypted with unique nonce
- Encryption key derived from environment variable
- Tamper detection via GCM authentication tags

Usage:
    # Set environment variable:
    # export ELOHIMOS_AUDIT_ENCRYPTION_KEY=$(openssl rand -hex 32)

    from encrypted_audit_logger import get_encrypted_audit_logger

    logger = get_encrypted_audit_logger()
    logger.log(user_id="user_123", action=AuditAction.USER_LOGIN)
"""

import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any, List
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets
import logging

logger = logging.getLogger(__name__)


class EncryptedAuditLogger:
    """
    Audit logger with AES-256-GCM encryption for all entries

    Each audit log entry's sensitive fields (user_id, action, details, ip_address)
    are encrypted with a unique nonce before storage.
    """

    def __init__(self, db_path: Optional[Path] = None, encryption_key: Optional[bytes] = None):
        """
        Initialize encrypted audit logger

        Args:
            db_path: Path to audit database (defaults to data dir)
            encryption_key: 32-byte encryption key (defaults to env var)
        """
        if db_path is None:
            try:
                from api.config_paths import get_data_dir
            except ImportError:
                from config_paths import get_data_dir
            data_dir = get_data_dir()
            db_path = data_dir / "audit_encrypted.db"

        self.db_path = db_path

        # Get or generate encryption key
        if encryption_key is None:
            encryption_key = self._get_encryption_key()

        self.encryption_key = encryption_key
        self.aesgcm = AESGCM(self.encryption_key)

        self._init_db()

        logger.info(f"Encrypted audit logger initialized: {self.db_path}")

    def _get_encryption_key(self) -> bytes:
        """
        Get encryption key from environment or generate new one

        Returns:
            32-byte AES-256 key
        """
        # Try to get from environment
        key_hex = os.getenv('ELOHIMOS_AUDIT_ENCRYPTION_KEY')

        if key_hex:
            try:
                key = bytes.fromhex(key_hex)
                if len(key) == 32:
                    logger.info("Using audit encryption key from environment")
                    return key
                else:
                    logger.warning(f"Invalid key length from environment: {len(key)} bytes, expected 32")
            except ValueError:
                logger.warning("Invalid hex format for ELOHIMOS_AUDIT_ENCRYPTION_KEY")

        # Generate new key and warn
        logger.warning("⚠️  SECURITY WARNING: No encryption key found in environment!")
        logger.warning("⚠️  Generating temporary key. Set ELOHIMOS_AUDIT_ENCRYPTION_KEY for production!")
        logger.warning("⚠️  Generate with: openssl rand -hex 32")

        new_key = secrets.token_bytes(32)
        logger.warning(f"⚠️  Temporary key (DO NOT USE IN PRODUCTION): {new_key.hex()}")

        return new_key

    def _init_db(self) -> None:
        """Initialize encrypted audit database schema"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Schema stores encrypted fields as BLOB
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log_encrypted (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                encrypted_user_id BLOB NOT NULL,
                encrypted_action BLOB NOT NULL,
                encrypted_resource BLOB,
                encrypted_resource_id BLOB,
                encrypted_ip_address BLOB,
                encrypted_user_agent BLOB,
                timestamp TEXT NOT NULL,
                encrypted_details BLOB,
                nonce_user_id BLOB NOT NULL,
                nonce_action BLOB NOT NULL,
                nonce_resource BLOB,
                nonce_resource_id BLOB,
                nonce_ip_address BLOB,
                nonce_user_agent BLOB,
                nonce_details BLOB
            )
        """)

        # Index on timestamp only (can't index encrypted fields)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_encrypted_audit_timestamp
            ON audit_log_encrypted(timestamp)
        """)

        conn.commit()
        conn.close()

    def _encrypt_field(self, value: Optional[str]) -> Optional[tuple[bytes, bytes]]:
        """
        Encrypt a field value with AES-256-GCM

        Args:
            value: Plain text value

        Returns:
            Tuple of (ciphertext, nonce) or None if value is None
        """
        if value is None:
            return None

        # Generate unique nonce for this field
        nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM

        # Encrypt with authentication
        plaintext = value.encode('utf-8')
        ciphertext = self.aesgcm.encrypt(nonce, plaintext, None)

        return (ciphertext, nonce)

    def _decrypt_field(self, ciphertext: Optional[bytes], nonce: Optional[bytes]) -> Optional[str]:
        """
        Decrypt a field value

        Args:
            ciphertext: Encrypted bytes
            nonce: Nonce used for encryption

        Returns:
            Decrypted string or None
        """
        if ciphertext is None or nonce is None:
            return None

        try:
            plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decrypt audit field: {e}")
            return "[DECRYPTION_FAILED]"

    def log(
        self,
        user_id: str,
        action: str,
        resource: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Log an encrypted audit event

        Args:
            user_id: User performing the action
            action: Action being performed
            resource: Resource type
            resource_id: Specific resource identifier
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional context as JSON

        Returns:
            ID of created audit log entry
        """
        try:
            # Import sanitization utility
            try:
                from .utils import sanitize_for_log
            except ImportError:
                from utils import sanitize_for_log

            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            timestamp = datetime.now(UTC).isoformat()

            # Sanitize details before encrypting
            sanitized_details = sanitize_for_log(details) if details else None
            details_json = json.dumps(sanitized_details) if sanitized_details else None

            # Encrypt all sensitive fields
            enc_user_id = self._encrypt_field(user_id)
            enc_action = self._encrypt_field(action)
            enc_resource = self._encrypt_field(resource)
            enc_resource_id = self._encrypt_field(resource_id)
            enc_ip_address = self._encrypt_field(ip_address)
            enc_user_agent = self._encrypt_field(user_agent)
            enc_details = self._encrypt_field(details_json)

            cursor.execute("""
                INSERT INTO audit_log_encrypted
                (encrypted_user_id, encrypted_action, encrypted_resource,
                 encrypted_resource_id, encrypted_ip_address, encrypted_user_agent,
                 timestamp, encrypted_details,
                 nonce_user_id, nonce_action, nonce_resource,
                 nonce_resource_id, nonce_ip_address, nonce_user_agent, nonce_details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                enc_user_id[0] if enc_user_id else None,
                enc_action[0] if enc_action else None,
                enc_resource[0] if enc_resource else None,
                enc_resource_id[0] if enc_resource_id else None,
                enc_ip_address[0] if enc_ip_address else None,
                enc_user_agent[0] if enc_user_agent else None,
                timestamp,
                enc_details[0] if enc_details else None,
                enc_user_id[1] if enc_user_id else None,
                enc_action[1] if enc_action else None,
                enc_resource[1] if enc_resource else None,
                enc_resource_id[1] if enc_resource_id else None,
                enc_ip_address[1] if enc_ip_address else None,
                enc_user_agent[1] if enc_user_agent else None,
                enc_details[1] if enc_details else None,
            ))

            audit_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.debug(f"Encrypted audit log created: ID {audit_id}")
            return audit_id

        except Exception as e:
            logger.error(f"Failed to create encrypted audit log: {e}")
            # Don't raise - audit failures shouldn't break the app
            return -1

    def get_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Query and decrypt audit logs

        Note: Filtering by encrypted fields (user_id, action) is not supported.
        Only timestamp filtering is available.

        Args:
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of decrypted audit entries
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Build query for timestamp filtering only
            query = "SELECT * FROM audit_log_encrypted WHERE 1=1"
            params = []

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())

            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            # Decrypt and return entries
            entries = []
            for row in rows:
                # Decrypt all fields
                user_id = self._decrypt_field(row[1], row[9])
                action = self._decrypt_field(row[2], row[10])
                resource = self._decrypt_field(row[3], row[11])
                resource_id = self._decrypt_field(row[4], row[12])
                ip_address = self._decrypt_field(row[5], row[13])
                user_agent = self._decrypt_field(row[6], row[14])
                details_json = self._decrypt_field(row[8], row[15])

                details = None
                if details_json and details_json != "[DECRYPTION_FAILED]":
                    try:
                        details = json.loads(details_json)
                    except (json.JSONDecodeError, ValueError):
                        pass

                entries.append({
                    'id': row[0],
                    'user_id': user_id,
                    'action': action,
                    'resource': resource,
                    'resource_id': resource_id,
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'timestamp': row[7],
                    'details': details
                })

            return entries

        except Exception as e:
            logger.error(f"Failed to query encrypted audit logs: {e}")
            return []

    def count_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Count audit logs (only supports timestamp filtering)

        Args:
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            Count of matching entries
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            query = "SELECT COUNT(*) FROM audit_log_encrypted WHERE 1=1"
            params = []

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())

            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())

            cursor.execute(query, params)
            count = cursor.fetchone()[0]
            conn.close()

            return count

        except Exception as e:
            logger.error(f"Failed to count encrypted audit logs: {e}")
            return 0

    def cleanup_old_logs(self, retention_days: int = 90) -> int:
        """
        Delete encrypted audit logs older than retention period

        Args:
            retention_days: Number of days to keep (default: 90)

        Returns:
            Number of logs deleted
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)

            cursor.execute("""
                DELETE FROM audit_log_encrypted
                WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))

            deleted = cursor.rowcount
            conn.commit()
            conn.close()

            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old encrypted audit logs")

            return deleted

        except Exception as e:
            logger.error(f"Failed to cleanup encrypted audit logs: {e}")
            return 0


# Global encrypted audit logger instance
_encrypted_audit_logger: Optional[EncryptedAuditLogger] = None


def get_encrypted_audit_logger() -> EncryptedAuditLogger:
    """
    Get or create global encrypted audit logger instance

    Returns:
        EncryptedAuditLogger instance
    """
    global _encrypted_audit_logger

    if _encrypted_audit_logger is None:
        _encrypted_audit_logger = EncryptedAuditLogger()

    return _encrypted_audit_logger
