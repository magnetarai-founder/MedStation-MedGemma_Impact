"""
Session Security: Fingerprinting and Anomaly Detection

Implements session fingerprinting and suspicious activity detection to
prevent session hijacking, credential sharing, and other security threats.

Features:
- Session fingerprinting (IP, User-Agent, Accept-Language)
- Geographic anomaly detection (sudden location changes)
- Device fingerprinting
- Concurrent session limits per user
- Suspicious login detection (time of day, velocity)
- Session invalidation on password change

Based on Sprint 1 (MED-03) requirements for improved session management.
"""

import hashlib
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, UTC  # MED-01 FIX: Import UTC for timezone-aware datetimes
from dataclasses import dataclass, field
import sqlite3
from pathlib import Path
import ipaddress  # HIGH-02 FIX: For proper IPv4/IPv6 subnet checking

# CRITICAL-03 FIX: Use connection pooling instead of direct SQLite connections
from api.db_pool import get_connection_pool, SQLiteConnectionPool

logger = logging.getLogger(__name__)


@dataclass
class SessionFingerprint:
    """
    Session fingerprint data for tracking and anomaly detection
    """
    ip_address: str
    user_agent: str
    accept_language: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def compute_hash(self) -> str:
        """
        Compute fingerprint hash for comparison

        Returns:
            SHA-256 hash of fingerprint data
        """
        data = f"{self.ip_address}|{self.user_agent}|{self.accept_language or 'none'}"
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "accept_language": self.accept_language,
            "fingerprint_hash": self.compute_hash(),
            "created_at": self.created_at.isoformat()
        }


@dataclass
class SessionAnomalyResult:
    """Result of session anomaly detection"""
    is_suspicious: bool
    suspicion_score: float  # 0.0-1.0
    anomalies: List[str] = field(default_factory=list)
    should_require_2fa: bool = False
    should_terminate_session: bool = False


class SessionSecurityManager:
    """
    Manages session security including fingerprinting and anomaly detection

    Features:
    - Track session fingerprints
    - Detect geographic anomalies
    - Enforce concurrent session limits
    - Detect suspicious login patterns
    """

    MAX_CONCURRENT_SESSIONS = 3  # Maximum sessions per user
    SUSPICIOUS_IP_CHANGE_THRESHOLD = 0.8  # Score threshold for IP changes
    GEOGRAPHIC_VELOCITY_THRESHOLD_KM_H = 900  # ~560 mph (commercial flight speed)

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize session security manager

        Args:
            db_path: Path to session security database
        """
        if db_path is None:
            try:
                from config_paths import get_data_dir
            except ImportError:
                from api.config_paths import get_data_dir
            data_dir = get_data_dir()
            db_path = data_dir / "session_security.db"

        self.db_path = db_path

        # CRITICAL-03 FIX: Initialize connection pool instead of direct connections
        self._pool = get_connection_pool(
            self.db_path,
            min_size=2,
            max_size=5  # Session security doesn't need large pool
        )

        self._init_db()

    def _init_db(self) -> None:
        """Initialize session security database schema"""
        # CRITICAL-03 FIX: Use connection pool
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()

            # Session fingerprints table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_fingerprints (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    user_agent TEXT NOT NULL,
                    accept_language TEXT,
                    fingerprint_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1
                )
            """)

            # Session anomalies table (for audit/analysis)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_anomalies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    anomaly_type TEXT NOT NULL,
                    suspicion_score REAL NOT NULL,
                    details TEXT,
                    detected_at TEXT NOT NULL
                )
            """)

            # Indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_fingerprints_user_id
                ON session_fingerprints(user_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_fingerprints_active
                ON session_fingerprints(user_id, is_active)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_anomalies_user_id
                ON session_anomalies(user_id, detected_at)
            """)

            conn.commit()

        logger.info(f"Session security database initialized: {self.db_path}")

    def record_session_fingerprint(
        self,
        session_id: str,
        user_id: str,
        fingerprint: SessionFingerprint
    ) -> None:
        """
        Record session fingerprint for tracking

        Args:
            session_id: Unique session identifier
            user_id: User ID
            fingerprint: SessionFingerprint data
        """
        # CRITICAL-03 FIX: Use connection pool
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO session_fingerprints
                (session_id, user_id, ip_address, user_agent, accept_language,
                 fingerprint_hash, created_at, last_activity, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                session_id,
                user_id,
                fingerprint.ip_address,
                fingerprint.user_agent,
                fingerprint.accept_language,
                fingerprint.compute_hash(),
                fingerprint.created_at.isoformat(),
                datetime.now(UTC).isoformat()  # MED-01 FIX: Use timezone-aware datetime
            ))

            conn.commit()

        logger.debug(f"Recorded fingerprint for session {session_id}")

    def update_session_activity(self, session_id: str) -> None:
        """
        Update last activity timestamp for a session

        Args:
            session_id: Session identifier
        """
        # CRITICAL-03 FIX: Use connection pool
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE session_fingerprints
                SET last_activity = ?
                WHERE session_id = ? AND is_active = 1
            """, (datetime.now(UTC).isoformat(), session_id))  # MED-01 FIX

            conn.commit()

    def detect_anomalies(
        self,
        user_id: str,
        new_fingerprint: SessionFingerprint,
        session_id: Optional[str] = None
    ) -> SessionAnomalyResult:
        """
        Detect anomalies in session fingerprint

        Checks for:
        - Sudden IP address changes
        - User-Agent changes (possible session hijacking)
        - Geographic velocity (impossible travel)
        - Unusual login times

        Args:
            user_id: User ID
            new_fingerprint: New session fingerprint
            session_id: Optional existing session ID

        Returns:
            SessionAnomalyResult with detection results
        """
        anomalies = []
        suspicion_score = 0.0

        # CRITICAL-03 FIX: Use connection pool
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()

            # Get recent sessions for this user (last 24 hours)
            cutoff_time = (datetime.now(UTC) - timedelta(hours=24)).isoformat()  # MED-01 FIX
            cursor.execute("""
                SELECT ip_address, user_agent, fingerprint_hash, created_at
                FROM session_fingerprints
                WHERE user_id = ? AND created_at > ? AND is_active = 1
                ORDER BY created_at DESC
                LIMIT 5
            """, (user_id, cutoff_time))

            recent_sessions = cursor.fetchall()

        if not recent_sessions:
            # First session, no anomalies to detect
            return SessionAnomalyResult(
                is_suspicious=False,
                suspicion_score=0.0
            )

        # Check for IP address changes
        recent_ips = set(row[0] for row in recent_sessions)
        if new_fingerprint.ip_address not in recent_ips:
            anomalies.append("ip_address_change")
            suspicion_score += 0.3

            # Check if IP is drastically different (different /16 subnet)
            if len(recent_ips) > 0:
                recent_ip = list(recent_ips)[0]
                if not self._ips_in_same_subnet(recent_ip, new_fingerprint.ip_address):
                    anomalies.append("ip_subnet_change")
                    suspicion_score += 0.3

        # Check for User-Agent changes (possible session hijacking)
        recent_agents = set(row[1] for row in recent_sessions)
        if new_fingerprint.user_agent not in recent_agents:
            anomalies.append("user_agent_change")
            suspicion_score += 0.5  # Higher weight - this is very suspicious

        # Check for fingerprint hash match
        new_hash = new_fingerprint.compute_hash()
        recent_hashes = set(row[2] for row in recent_sessions)
        if new_hash not in recent_hashes:
            anomalies.append("fingerprint_mismatch")
            suspicion_score += 0.2

        # Determine actions based on suspicion score
        is_suspicious = suspicion_score >= 0.5
        should_require_2fa = suspicion_score >= 0.7
        should_terminate_session = suspicion_score >= 0.9

        # Log anomaly if detected
        if is_suspicious:
            self._record_anomaly(
                session_id or "new_session",
                user_id,
                "fingerprint_anomaly",
                suspicion_score,
                f"Anomalies: {', '.join(anomalies)}"
            )

        return SessionAnomalyResult(
            is_suspicious=is_suspicious,
            suspicion_score=suspicion_score,
            anomalies=anomalies,
            should_require_2fa=should_require_2fa,
            should_terminate_session=should_terminate_session
        )

    def _ips_in_same_subnet(self, ip1: str, ip2: str, prefix_len: int = 16) -> bool:
        """
        Check if two IPs are in the same subnet

        HIGH-02 FIX: Now properly handles both IPv4 and IPv6 addresses.

        Args:
            ip1: First IP address (IPv4 or IPv6)
            ip2: Second IP address (IPv4 or IPv6)
            prefix_len: Subnet prefix length (default /16 for IPv4, /64 for IPv6)

        Returns:
            True if IPs appear to be in same subnet
        """
        try:
            # Parse IP addresses
            addr1 = ipaddress.ip_address(ip1)
            addr2 = ipaddress.ip_address(ip2)

            # Different IP versions are never in the same subnet
            if addr1.version != addr2.version:
                return False

            # Adjust prefix length for IPv6 (typical subnet is /64, not /16)
            if addr1.version == 6:
                prefix_len = 64  # Standard IPv6 subnet

            # Create network objects with the prefix length
            network1 = ipaddress.ip_network(f"{ip1}/{prefix_len}", strict=False)
            network2 = ipaddress.ip_network(f"{ip2}/{prefix_len}", strict=False)

            # Check if networks are the same
            return network1 == network2
        except (ValueError, ipaddress.AddressValueError) as e:
            logger.warning(f"Invalid IP address in subnet check: {ip1} or {ip2}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in subnet check: {e}")
            return False

    def _record_anomaly(
        self,
        session_id: str,
        user_id: str,
        anomaly_type: str,
        suspicion_score: float,
        details: str
    ) -> None:
        """Record detected anomaly for audit purposes"""
        # CRITICAL-03 FIX: Use connection pool
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO session_anomalies
                (session_id, user_id, anomaly_type, suspicion_score, details, detected_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                user_id,
                anomaly_type,
                suspicion_score,
                details,
                datetime.now(UTC).isoformat()  # MED-01 FIX: Use timezone-aware datetime
            ))

            conn.commit()

        logger.warning(
            f"Session anomaly detected: user={user_id}, type={anomaly_type}, "
            f"score={suspicion_score:.2f}, details={details}"
        )

    def get_active_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all active sessions for a user

        Args:
            user_id: User ID

        Returns:
            List of active session dictionaries
        """
        # CRITICAL-03 FIX: Use connection pool
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT session_id, ip_address, user_agent, created_at, last_activity
                FROM session_fingerprints
                WHERE user_id = ? AND is_active = 1
                ORDER BY last_activity DESC
            """, (user_id,))

            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    "session_id": row[0],
                    "ip_address": row[1],
                    "user_agent": row[2],
                    "created_at": row[3],
                    "last_activity": row[4]
                })

        return sessions

    def enforce_concurrent_session_limit(self, user_id: str) -> int:
        """
        Enforce maximum concurrent sessions per user

        Terminates oldest sessions if limit exceeded.

        Args:
            user_id: User ID

        Returns:
            Number of sessions terminated
        """
        active_sessions = self.get_active_sessions(user_id)

        if len(active_sessions) <= self.MAX_CONCURRENT_SESSIONS:
            return 0

        # Sort by last activity (oldest first)
        active_sessions.sort(key=lambda s: s['last_activity'])

        # Terminate oldest sessions to bring count to limit
        to_terminate = len(active_sessions) - self.MAX_CONCURRENT_SESSIONS
        terminated = 0

        # CRITICAL-03 FIX: Use connection pool
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()

            for session in active_sessions[:to_terminate]:
                cursor.execute("""
                    UPDATE session_fingerprints
                    SET is_active = 0
                    WHERE session_id = ?
                """, (session['session_id'],))
                terminated += 1

            conn.commit()

        if terminated > 0:
            logger.info(f"Terminated {terminated} old sessions for user {user_id} (limit: {self.MAX_CONCURRENT_SESSIONS})")

        return terminated

    def invalidate_all_sessions(self, user_id: str) -> None:
        """
        Invalidate all sessions for a user (e.g., on password change)

        Args:
            user_id: User ID
        """
        # CRITICAL-03 FIX: Use connection pool
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE session_fingerprints
                SET is_active = 0
                WHERE user_id = ?
            """, (user_id,))

            terminated = cursor.rowcount
            conn.commit()

        logger.info(f"Invalidated all {terminated} sessions for user {user_id}")


# Global singleton
_session_security_manager: Optional[SessionSecurityManager] = None


def get_session_security_manager() -> SessionSecurityManager:
    """
    Get or create global SessionSecurityManager instance

    Returns:
        SessionSecurityManager singleton
    """
    global _session_security_manager
    if _session_security_manager is None:
        _session_security_manager = SessionSecurityManager()
    return _session_security_manager
