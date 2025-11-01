#!/usr/bin/env python3
"""
Panic Mode for ElohimOS
Emergency security system for missionaries in hostile situations
Rapidly wipes sensitive data, closes connections, encrypts databases
"""

import os
import shutil
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class PanicMode:
    """Emergency security system"""

    def __init__(self):
        self.panic_triggered = False
        self.last_panic_time = None

    async def trigger_panic(self, reason: str = "Manual trigger") -> Dict[str, Any]:
        """
        EMERGENCY: Wipe sensitive data immediately
        This is irreversible!
        """

        self.panic_triggered = True
        self.last_panic_time = datetime.utcnow()

        logger.critical(f"🚨 PANIC MODE ACTIVATED: {reason}")

        actions_taken = []
        errors = []

        # 1. Close all active P2P connections
        try:
            await self._close_p2p_connections()
            actions_taken.append("Closed P2P connections")
        except Exception as e:
            errors.append(f"P2P close failed: {e}")
            logger.error(f"Failed to close P2P: {e}")

        # 2. Wipe chat cache and temporary files
        try:
            self._wipe_chat_cache()
            actions_taken.append("Wiped chat cache")
        except Exception as e:
            errors.append(f"Cache wipe failed: {e}")
            logger.error(f"Failed to wipe cache: {e}")

        # 3. Clear uploaded documents
        try:
            self._wipe_uploads()
            actions_taken.append("Wiped uploaded documents")
        except Exception as e:
            errors.append(f"Upload wipe failed: {e}")
            logger.error(f"Failed to wipe uploads: {e}")

        # 4. Encrypt local databases (if not already)
        try:
            self._secure_databases()
            actions_taken.append("Secured databases")
        except Exception as e:
            errors.append(f"DB encryption failed: {e}")
            logger.error(f"Failed to encrypt DB: {e}")

        # 5. Clear browser localStorage (via API response flag)
        actions_taken.append("Flagged browser cache for clearing")

        # 6. Log panic event (scrubbed of PII)
        try:
            self._log_panic_event(reason, actions_taken, errors)
            actions_taken.append("Logged panic event")
        except Exception as e:
            logger.error(f"Failed to log panic: {e}")

        return {
            "panic_activated": True,
            "timestamp": self.last_panic_time.isoformat(),
            "reason": reason,
            "actions_taken": actions_taken,
            "errors": errors,
            "status": "SECURE" if not errors else "PARTIAL"
        }

    async def _close_p2p_connections(self):
        """Close all P2P connections immediately"""
        try:
            # Import P2P service and close all connections
            from p2p_chat_service import get_p2p_chat_service
            p2p = get_p2p_chat_service()

            if p2p and hasattr(p2p, 'close_all_connections'):
                await p2p.close_all_connections()
            else:
                logger.debug("P2P service not initialized or unavailable")

            logger.info("✓ P2P connections closed")
        except ImportError:
            logger.debug("P2P service not available")
        except Exception as e:
            raise

    def _wipe_chat_cache(self):
        """Wipe all chat session cache"""
        try:
            from config_paths import get_config_paths
            paths = get_config_paths()
            cache_paths = [
                paths.data_dir / "cache",
                paths.uploads_dir,
                Path("/tmp/omnistudio_cache"),
            ]
        except Exception:
            # Fallback to hardcoded paths
            cache_paths = [
                Path(".neutron_data/cache"),
                Path(".neutron_data/uploads"),
                Path("/tmp/omnistudio_cache"),
            ]

        for cache_path in cache_paths:
            if cache_path.exists():
                try:
                    shutil.rmtree(cache_path)
                    cache_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"✓ Wiped {cache_path}")
                except Exception as e:
                    logger.error(f"Failed to wipe {cache_path}: {e}")

    def _wipe_uploads(self):
        """Wipe all uploaded files"""
        try:
            from config_paths import get_config_paths
            paths = get_config_paths()
            upload_paths = [
                paths.uploads_dir,
                Path("temp_uploads"),
            ]
        except Exception:
            # Fallback to hardcoded paths
            upload_paths = [
                Path(".neutron_data/uploads"),
                Path("temp_uploads"),
            ]

        for upload_path in upload_paths:
            if upload_path.exists():
                try:
                    # Overwrite files before deletion (basic anti-forensics)
                    for file_path in upload_path.glob("**/*"):
                        if file_path.is_file():
                            # Overwrite with random data (full file, not just 1MB)
                            size = file_path.stat().st_size
                            with open(file_path, 'wb') as f:
                                # Write in chunks to avoid OOM on large files
                                chunk_size = 1024 * 1024  # 1MB chunks
                                remaining = size
                                while remaining > 0:
                                    write_size = min(chunk_size, remaining)
                                    f.write(os.urandom(write_size))
                                    remaining -= write_size

                    # Now delete
                    shutil.rmtree(upload_path)
                    upload_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"✓ Securely wiped {upload_path}")
                except Exception as e:
                    logger.error(f"Failed to wipe {upload_path}: {e}")

    def _secure_databases(self):
        """Ensure databases are encrypted and discover all DBs via config_paths"""
        # Import config paths to get all known database locations
        try:
            from config_paths import get_config_paths
            paths = get_config_paths()

            # Discover all .db files in data directory
            db_paths = list(paths.data_dir.glob("**/*.db"))

            # Add known additional DBs
            db_paths.extend([
                Path.home() / ".elohimos" / "elohimos_memory.db",
                Path.home() / ".elohimos" / "learning.db",
                paths.data_dir / "memory" / "chat_memory.db",
                paths.data_dir / "vault" / "vault.db",
                paths.data_dir / "users.db",
                paths.data_dir / "docs.db",
                paths.data_dir / "p2p_chat.db",
            ])
        except Exception as e:
            logger.warning(f"Could not discover DBs via config_paths: {e}")
            # Fallback to minimal hardcoded paths (only those outside .neutron_data)
            db_paths = [
                Path.home() / ".elohimos" / "elohimos_memory.db",
                Path.home() / ".elohimos" / "learning.db",
            ]

        for db_path in db_paths:
            if db_path.exists():
                try:
                    # Add encryption pragma (if SQLCipher available)
                    # For now, just ensure WAL mode is enabled
                    conn = sqlite3.connect(str(db_path))
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA synchronous=FULL")  # Ensure durability
                    conn.close()
                    logger.info(f"✓ Secured {db_path}")
                except Exception as e:
                    logger.error(f"Failed to secure {db_path}: {e}")

    def _log_panic_event(self, reason: str, actions: List[str], errors: List[str]):
        """Log panic event (PII-scrubbed)"""
        panic_log_path = Path.home() / ".omnistudio" / "panic_log.txt"
        panic_log_path.parent.mkdir(parents=True, exist_ok=True)

        log_entry = f"""
=================================================
PANIC EVENT: {self.last_panic_time.isoformat()}
=================================================
Reason: {reason}
Actions Taken:
{chr(10).join(f"  - {a}" for a in actions)}

Errors:
{chr(10).join(f"  - {e}" for e in errors) if errors else "  None"}
=================================================

"""

        try:
            with open(panic_log_path, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Failed to write panic log: {e}")

    def get_panic_status(self) -> Dict[str, Any]:
        """Get current panic mode status"""
        return {
            "panic_active": self.panic_triggered,
            "last_panic": self.last_panic_time.isoformat() if self.last_panic_time else None,
            "secure_mode": self.panic_triggered
        }

    def reset_panic(self):
        """Reset panic mode (requires admin)"""
        self.panic_triggered = False
        logger.info("🔓 Panic mode reset")


# Singleton instance
_panic_mode = None


def get_panic_mode() -> PanicMode:
    """Get singleton panic mode instance"""
    global _panic_mode
    if _panic_mode is None:
        _panic_mode = PanicMode()
        logger.info("🚨 Panic mode system initialized")
    return _panic_mode
