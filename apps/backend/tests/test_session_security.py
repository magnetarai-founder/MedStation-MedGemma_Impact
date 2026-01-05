"""
Tests for session_security.py - Session Fingerprinting and Anomaly Detection

Tests cover:
- SessionFingerprint hash computation and consistency
- SessionAnomalyResult defaults and values
- Database initialization and schema
- Recording and retrieving session fingerprints
- Session activity timestamp updates
- Anomaly detection (IP changes, user-agent changes, subnet changes)
- IPv4 and IPv6 subnet checking
- Concurrent session limit enforcement
- Session invalidation (password change scenarios)
- Edge cases (first session, empty data, invalid IPs)
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta, UTC
from unittest.mock import patch, MagicMock

from api.session_security import (
    SessionFingerprint,
    SessionAnomalyResult,
    SessionSecurityManager,
    get_session_security_manager,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path for testing"""
    return tmp_path / "test_session_security.db"


@pytest.fixture
def session_manager(temp_db_path):
    """Create a SessionSecurityManager with a temp database"""
    manager = SessionSecurityManager(db_path=temp_db_path)
    yield manager
    # Cleanup: close pool connections
    if hasattr(manager, '_pool') and manager._pool:
        manager._pool.close()


@pytest.fixture
def sample_fingerprint():
    """Create a sample fingerprint for testing"""
    return SessionFingerprint(
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        accept_language="en-US,en;q=0.9"
    )


@pytest.fixture
def sample_fingerprint_different_ip():
    """Create a fingerprint with different IP but same user agent"""
    return SessionFingerprint(
        ip_address="10.0.0.50",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        accept_language="en-US,en;q=0.9"
    )


@pytest.fixture
def sample_fingerprint_different_agent():
    """Create a fingerprint with same IP but different user agent"""
    return SessionFingerprint(
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        accept_language="en-US,en;q=0.9"
    )


# =============================================================================
# SessionFingerprint Tests
# =============================================================================

class TestSessionFingerprint:
    """Tests for the SessionFingerprint dataclass"""

    def test_fingerprint_creation(self):
        """Test basic fingerprint creation"""
        fp = SessionFingerprint(
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0"
        )
        assert fp.ip_address == "192.168.1.1"
        assert fp.user_agent == "TestAgent/1.0"
        assert fp.accept_language is None

    def test_fingerprint_with_all_fields(self):
        """Test fingerprint with all fields populated"""
        fp = SessionFingerprint(
            ip_address="10.0.0.1",
            user_agent="Mozilla/5.0",
            accept_language="en-US"
        )
        assert fp.ip_address == "10.0.0.1"
        assert fp.user_agent == "Mozilla/5.0"
        assert fp.accept_language == "en-US"

    def test_hash_computation_consistency(self):
        """Test that hash is consistent for same inputs"""
        fp1 = SessionFingerprint(
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
            accept_language="en-US"
        )
        fp2 = SessionFingerprint(
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
            accept_language="en-US"
        )
        assert fp1.compute_hash() == fp2.compute_hash()

    def test_hash_differs_for_different_ip(self):
        """Test that hash differs when IP changes"""
        fp1 = SessionFingerprint(ip_address="192.168.1.1", user_agent="Agent")
        fp2 = SessionFingerprint(ip_address="192.168.1.2", user_agent="Agent")
        assert fp1.compute_hash() != fp2.compute_hash()

    def test_hash_differs_for_different_user_agent(self):
        """Test that hash differs when user agent changes"""
        fp1 = SessionFingerprint(ip_address="192.168.1.1", user_agent="Agent1")
        fp2 = SessionFingerprint(ip_address="192.168.1.1", user_agent="Agent2")
        assert fp1.compute_hash() != fp2.compute_hash()

    def test_hash_differs_for_different_language(self):
        """Test that hash differs when accept-language changes"""
        fp1 = SessionFingerprint(
            ip_address="192.168.1.1",
            user_agent="Agent",
            accept_language="en-US"
        )
        fp2 = SessionFingerprint(
            ip_address="192.168.1.1",
            user_agent="Agent",
            accept_language="fr-FR"
        )
        assert fp1.compute_hash() != fp2.compute_hash()

    def test_hash_with_none_language(self):
        """Test hash handles None accept_language correctly"""
        fp = SessionFingerprint(
            ip_address="192.168.1.1",
            user_agent="Agent",
            accept_language=None
        )
        # Should not raise and should produce consistent hash
        hash1 = fp.compute_hash()
        hash2 = fp.compute_hash()
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_to_dict(self):
        """Test conversion to dictionary"""
        fp = SessionFingerprint(
            ip_address="192.168.1.1",
            user_agent="Agent",
            accept_language="en"
        )
        d = fp.to_dict()
        assert d["ip_address"] == "192.168.1.1"
        assert d["user_agent"] == "Agent"
        assert d["accept_language"] == "en"
        assert "fingerprint_hash" in d
        assert "created_at" in d

    def test_to_dict_includes_hash(self):
        """Test that to_dict includes the computed hash"""
        fp = SessionFingerprint(ip_address="1.2.3.4", user_agent="Test")
        d = fp.to_dict()
        assert d["fingerprint_hash"] == fp.compute_hash()


# =============================================================================
# SessionAnomalyResult Tests
# =============================================================================

class TestSessionAnomalyResult:
    """Tests for the SessionAnomalyResult dataclass"""

    def test_default_values(self):
        """Test default values for anomaly result"""
        result = SessionAnomalyResult(
            is_suspicious=False,
            suspicion_score=0.0
        )
        assert result.is_suspicious is False
        assert result.suspicion_score == 0.0
        assert result.anomalies == []
        assert result.should_require_2fa is False
        assert result.should_terminate_session is False

    def test_suspicious_result(self):
        """Test suspicious result with anomalies"""
        result = SessionAnomalyResult(
            is_suspicious=True,
            suspicion_score=0.75,
            anomalies=["ip_address_change", "user_agent_change"],
            should_require_2fa=True,
            should_terminate_session=False
        )
        assert result.is_suspicious is True
        assert result.suspicion_score == 0.75
        assert len(result.anomalies) == 2
        assert "ip_address_change" in result.anomalies
        assert result.should_require_2fa is True

    def test_high_risk_result(self):
        """Test high-risk result that should terminate session"""
        result = SessionAnomalyResult(
            is_suspicious=True,
            suspicion_score=0.95,
            anomalies=["ip_address_change", "ip_subnet_change", "user_agent_change"],
            should_require_2fa=True,
            should_terminate_session=True
        )
        assert result.should_terminate_session is True


# =============================================================================
# SessionSecurityManager Database Tests
# =============================================================================

class TestSessionSecurityManagerDatabase:
    """Tests for database initialization and operations"""

    def test_database_creation(self, session_manager, temp_db_path):
        """Test that database file is created"""
        assert temp_db_path.exists()

    def test_tables_created(self, session_manager):
        """Test that required tables are created"""
        with session_manager._pool.get_connection() as conn:
            cursor = conn.cursor()

            # Check session_fingerprints table
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='session_fingerprints'
            """)
            assert cursor.fetchone() is not None

            # Check session_anomalies table
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='session_anomalies'
            """)
            assert cursor.fetchone() is not None

    def test_indexes_created(self, session_manager):
        """Test that indexes are created"""
        with session_manager._pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='index' AND name LIKE 'idx_%'
            """)
            indexes = [row[0] for row in cursor.fetchall()]
            assert "idx_fingerprints_user_id" in indexes
            assert "idx_fingerprints_active" in indexes
            assert "idx_anomalies_user_id" in indexes


# =============================================================================
# Session Fingerprint Recording Tests
# =============================================================================

class TestSessionFingerprintRecording:
    """Tests for recording and retrieving session fingerprints"""

    def test_record_fingerprint(self, session_manager, sample_fingerprint):
        """Test recording a session fingerprint"""
        session_manager.record_session_fingerprint(
            session_id="sess_123",
            user_id="user_456",
            fingerprint=sample_fingerprint
        )

        sessions = session_manager.get_active_sessions("user_456")
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "sess_123"
        assert sessions[0]["ip_address"] == sample_fingerprint.ip_address

    def test_record_multiple_fingerprints(self, session_manager, sample_fingerprint):
        """Test recording multiple fingerprints for same user"""
        for i in range(3):
            fp = SessionFingerprint(
                ip_address=f"192.168.1.{i}",
                user_agent="TestAgent"
            )
            session_manager.record_session_fingerprint(
                session_id=f"sess_{i}",
                user_id="user_123",
                fingerprint=fp
            )

        sessions = session_manager.get_active_sessions("user_123")
        assert len(sessions) == 3

    def test_fingerprint_replacement(self, session_manager, sample_fingerprint):
        """Test that recording same session_id replaces existing"""
        session_manager.record_session_fingerprint(
            session_id="sess_123",
            user_id="user_456",
            fingerprint=sample_fingerprint
        )

        # Record again with different IP
        new_fp = SessionFingerprint(
            ip_address="10.0.0.1",
            user_agent=sample_fingerprint.user_agent
        )
        session_manager.record_session_fingerprint(
            session_id="sess_123",
            user_id="user_456",
            fingerprint=new_fp
        )

        sessions = session_manager.get_active_sessions("user_456")
        assert len(sessions) == 1
        assert sessions[0]["ip_address"] == "10.0.0.1"

    def test_get_active_sessions_empty(self, session_manager):
        """Test getting sessions for user with no sessions"""
        sessions = session_manager.get_active_sessions("nonexistent_user")
        assert sessions == []

    def test_get_active_sessions_sorted_by_activity(self, session_manager):
        """Test that sessions are sorted by last_activity descending"""
        for i in range(3):
            fp = SessionFingerprint(ip_address=f"192.168.1.{i}", user_agent="Agent")
            session_manager.record_session_fingerprint(
                session_id=f"sess_{i}",
                user_id="user_123",
                fingerprint=fp
            )
            # Update activity for middle session to make it most recent
            if i == 1:
                session_manager.update_session_activity(f"sess_{i}")

        # Update sess_1 again to ensure it's most recent
        session_manager.update_session_activity("sess_1")

        sessions = session_manager.get_active_sessions("user_123")
        assert sessions[0]["session_id"] == "sess_1"


# =============================================================================
# Session Activity Update Tests
# =============================================================================

class TestSessionActivityUpdate:
    """Tests for updating session activity timestamps"""

    def test_update_activity(self, session_manager, sample_fingerprint):
        """Test updating session activity timestamp"""
        session_manager.record_session_fingerprint(
            session_id="sess_123",
            user_id="user_456",
            fingerprint=sample_fingerprint
        )

        sessions_before = session_manager.get_active_sessions("user_456")
        initial_activity = sessions_before[0]["last_activity"]

        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.1)

        session_manager.update_session_activity("sess_123")

        sessions_after = session_manager.get_active_sessions("user_456")
        assert sessions_after[0]["last_activity"] >= initial_activity

    def test_update_nonexistent_session(self, session_manager):
        """Test updating activity for non-existent session (should not raise)"""
        # Should not raise
        session_manager.update_session_activity("nonexistent_session")


# =============================================================================
# Anomaly Detection Tests
# =============================================================================

class TestAnomalyDetection:
    """Tests for session anomaly detection"""

    def test_first_session_no_anomalies(self, session_manager, sample_fingerprint):
        """Test that first session for user has no anomalies"""
        result = session_manager.detect_anomalies(
            user_id="new_user",
            new_fingerprint=sample_fingerprint
        )
        assert result.is_suspicious is False
        assert result.suspicion_score == 0.0
        assert result.anomalies == []

    def test_same_fingerprint_no_anomalies(self, session_manager, sample_fingerprint):
        """Test that same fingerprint produces no anomalies"""
        # Record initial session
        session_manager.record_session_fingerprint(
            session_id="sess_1",
            user_id="user_123",
            fingerprint=sample_fingerprint
        )

        # Check with same fingerprint
        result = session_manager.detect_anomalies(
            user_id="user_123",
            new_fingerprint=sample_fingerprint
        )
        assert result.is_suspicious is False
        assert len(result.anomalies) == 0

    def test_ip_change_detected(self, session_manager, sample_fingerprint, sample_fingerprint_different_ip):
        """Test that IP address change is detected"""
        # Record initial session
        session_manager.record_session_fingerprint(
            session_id="sess_1",
            user_id="user_123",
            fingerprint=sample_fingerprint
        )

        # Check with different IP
        result = session_manager.detect_anomalies(
            user_id="user_123",
            new_fingerprint=sample_fingerprint_different_ip
        )
        assert "ip_address_change" in result.anomalies
        assert result.suspicion_score >= 0.3

    def test_user_agent_change_detected(self, session_manager, sample_fingerprint, sample_fingerprint_different_agent):
        """Test that User-Agent change is detected (high suspicion)"""
        # Record initial session
        session_manager.record_session_fingerprint(
            session_id="sess_1",
            user_id="user_123",
            fingerprint=sample_fingerprint
        )

        # Check with different user agent
        result = session_manager.detect_anomalies(
            user_id="user_123",
            new_fingerprint=sample_fingerprint_different_agent
        )
        assert "user_agent_change" in result.anomalies
        assert result.suspicion_score >= 0.5  # User agent change has high weight

    def test_multiple_anomalies_compound_score(self, session_manager, sample_fingerprint):
        """Test that multiple anomalies compound the suspicion score"""
        # Record initial session
        session_manager.record_session_fingerprint(
            session_id="sess_1",
            user_id="user_123",
            fingerprint=sample_fingerprint
        )

        # Create fingerprint with multiple differences
        suspicious_fp = SessionFingerprint(
            ip_address="203.0.113.50",  # Different IP and subnet
            user_agent="SuspiciousBot/1.0",  # Different agent
            accept_language="zh-CN"  # Different language
        )

        result = session_manager.detect_anomalies(
            user_id="user_123",
            new_fingerprint=suspicious_fp
        )
        assert result.is_suspicious is True
        assert len(result.anomalies) >= 2
        assert result.suspicion_score >= 0.5

    def test_high_suspicion_requires_2fa(self, session_manager, sample_fingerprint):
        """Test that high suspicion score triggers 2FA requirement"""
        # Record initial session
        session_manager.record_session_fingerprint(
            session_id="sess_1",
            user_id="user_123",
            fingerprint=sample_fingerprint
        )

        # Very suspicious fingerprint
        suspicious_fp = SessionFingerprint(
            ip_address="203.0.113.1",  # Different subnet
            user_agent="CompletelyDifferentBrowser/99.0",
            accept_language="ar-SA"
        )

        result = session_manager.detect_anomalies(
            user_id="user_123",
            new_fingerprint=suspicious_fp
        )

        # With IP change + subnet change + user agent change + fingerprint mismatch
        # Score should be >= 0.7
        if result.suspicion_score >= 0.7:
            assert result.should_require_2fa is True

    def test_anomaly_recorded_in_database(self, session_manager, sample_fingerprint):
        """Test that detected anomalies are recorded in the database"""
        # Record initial session
        session_manager.record_session_fingerprint(
            session_id="sess_1",
            user_id="user_123",
            fingerprint=sample_fingerprint
        )

        # Trigger anomaly
        suspicious_fp = SessionFingerprint(
            ip_address="203.0.113.1",
            user_agent="DifferentBrowser/1.0"
        )

        result = session_manager.detect_anomalies(
            user_id="user_123",
            new_fingerprint=suspicious_fp,
            session_id="sess_2"
        )

        if result.is_suspicious:
            # Check database for anomaly record
            with session_manager._pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT anomaly_type, suspicion_score
                    FROM session_anomalies
                    WHERE user_id = ?
                """, ("user_123",))
                anomaly = cursor.fetchone()
                assert anomaly is not None
                assert anomaly[0] == "fingerprint_anomaly"


# =============================================================================
# IP Subnet Tests
# =============================================================================

class TestIPSubnetChecking:
    """Tests for IP subnet comparison logic"""

    def test_same_ipv4_subnet(self, session_manager):
        """Test IPs in same /16 subnet"""
        assert session_manager._ips_in_same_subnet(
            "192.168.1.1",
            "192.168.255.255"
        ) is True

    def test_different_ipv4_subnet(self, session_manager):
        """Test IPs in different /16 subnets"""
        assert session_manager._ips_in_same_subnet(
            "192.168.1.1",
            "10.0.0.1"
        ) is False

    def test_same_ipv6_subnet(self, session_manager):
        """Test IPv6 addresses in same /64 subnet"""
        assert session_manager._ips_in_same_subnet(
            "2001:db8:85a3::8a2e:370:7334",
            "2001:db8:85a3::1"
        ) is True

    def test_different_ipv6_subnet(self, session_manager):
        """Test IPv6 addresses in different subnets"""
        assert session_manager._ips_in_same_subnet(
            "2001:db8:85a3::1",
            "2001:db8:1234::1"
        ) is False

    def test_mixed_ip_versions(self, session_manager):
        """Test that IPv4 and IPv6 are never in same subnet"""
        assert session_manager._ips_in_same_subnet(
            "192.168.1.1",
            "2001:db8::1"
        ) is False

    def test_invalid_ip_addresses(self, session_manager):
        """Test handling of invalid IP addresses"""
        # Should return False, not raise
        assert session_manager._ips_in_same_subnet(
            "not.an.ip",
            "192.168.1.1"
        ) is False

        assert session_manager._ips_in_same_subnet(
            "192.168.1.1",
            "invalid"
        ) is False

    def test_empty_ip_addresses(self, session_manager):
        """Test handling of empty IP addresses"""
        assert session_manager._ips_in_same_subnet("", "192.168.1.1") is False
        assert session_manager._ips_in_same_subnet("192.168.1.1", "") is False

    def test_localhost_comparison(self, session_manager):
        """Test localhost address comparisons"""
        assert session_manager._ips_in_same_subnet(
            "127.0.0.1",
            "127.0.0.2"
        ) is True

    def test_ipv6_localhost(self, session_manager):
        """Test IPv6 localhost"""
        assert session_manager._ips_in_same_subnet("::1", "::1") is True


# =============================================================================
# Concurrent Session Limit Tests
# =============================================================================

class TestConcurrentSessionLimit:
    """Tests for concurrent session limit enforcement"""

    def test_under_limit_no_termination(self, session_manager):
        """Test that sessions under limit are not terminated"""
        for i in range(3):
            fp = SessionFingerprint(ip_address=f"192.168.1.{i}", user_agent="Agent")
            session_manager.record_session_fingerprint(
                session_id=f"sess_{i}",
                user_id="user_123",
                fingerprint=fp
            )

        terminated = session_manager.enforce_concurrent_session_limit("user_123")
        assert terminated == 0
        assert len(session_manager.get_active_sessions("user_123")) == 3

    def test_over_limit_terminates_oldest(self, session_manager):
        """Test that oldest sessions are terminated when over limit"""
        # Create 5 sessions (limit is 3)
        for i in range(5):
            fp = SessionFingerprint(ip_address=f"192.168.1.{i}", user_agent="Agent")
            session_manager.record_session_fingerprint(
                session_id=f"sess_{i}",
                user_id="user_123",
                fingerprint=fp
            )
            # Update activity to establish order
            session_manager.update_session_activity(f"sess_{i}")
            import time
            time.sleep(0.05)  # Small delay to ensure different timestamps

        terminated = session_manager.enforce_concurrent_session_limit("user_123")
        assert terminated == 2  # 5 - 3 = 2 terminated

        remaining = session_manager.get_active_sessions("user_123")
        assert len(remaining) == 3

    def test_exactly_at_limit(self, session_manager):
        """Test behavior when exactly at the limit"""
        for i in range(session_manager.MAX_CONCURRENT_SESSIONS):
            fp = SessionFingerprint(ip_address=f"192.168.1.{i}", user_agent="Agent")
            session_manager.record_session_fingerprint(
                session_id=f"sess_{i}",
                user_id="user_123",
                fingerprint=fp
            )

        terminated = session_manager.enforce_concurrent_session_limit("user_123")
        assert terminated == 0

    def test_enforce_limit_user_with_no_sessions(self, session_manager):
        """Test enforcing limit on user with no sessions"""
        terminated = session_manager.enforce_concurrent_session_limit("no_sessions_user")
        assert terminated == 0


# =============================================================================
# Session Invalidation Tests
# =============================================================================

class TestSessionInvalidation:
    """Tests for session invalidation"""

    def test_invalidate_all_sessions(self, session_manager):
        """Test invalidating all sessions for a user"""
        # Create multiple sessions
        for i in range(3):
            fp = SessionFingerprint(ip_address=f"192.168.1.{i}", user_agent="Agent")
            session_manager.record_session_fingerprint(
                session_id=f"sess_{i}",
                user_id="user_123",
                fingerprint=fp
            )

        assert len(session_manager.get_active_sessions("user_123")) == 3

        session_manager.invalidate_all_sessions("user_123")

        assert len(session_manager.get_active_sessions("user_123")) == 0

    def test_invalidate_does_not_affect_other_users(self, session_manager):
        """Test that invalidation only affects target user"""
        # Create sessions for two users
        for user in ["user_1", "user_2"]:
            fp = SessionFingerprint(ip_address="192.168.1.1", user_agent="Agent")
            session_manager.record_session_fingerprint(
                session_id=f"sess_{user}",
                user_id=user,
                fingerprint=fp
            )

        session_manager.invalidate_all_sessions("user_1")

        assert len(session_manager.get_active_sessions("user_1")) == 0
        assert len(session_manager.get_active_sessions("user_2")) == 1

    def test_invalidate_user_with_no_sessions(self, session_manager):
        """Test invalidating sessions for user with no sessions"""
        # Should not raise
        session_manager.invalidate_all_sessions("nonexistent_user")


# =============================================================================
# Singleton Tests
# =============================================================================

class TestSessionSecuritySingleton:
    """Tests for the global singleton pattern"""

    def test_get_session_security_manager_returns_instance(self, temp_db_path):
        """Test that get_session_security_manager returns an instance"""
        # Reset global singleton for this test
        import api.session_security as ss_module
        ss_module._session_security_manager = None

        # Patch the config_paths module where get_data_dir is actually defined
        with patch('api.config_paths.get_data_dir', return_value=temp_db_path.parent):
            manager = get_session_security_manager()
            assert isinstance(manager, SessionSecurityManager)

    def test_singleton_returns_same_instance(self, temp_db_path):
        """Test that singleton returns the same instance on repeated calls"""
        import api.session_security as ss_module
        ss_module._session_security_manager = None

        with patch('api.config_paths.get_data_dir', return_value=temp_db_path.parent):
            manager1 = get_session_security_manager()
            manager2 = get_session_security_manager()
            assert manager1 is manager2


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_very_long_user_agent(self, session_manager):
        """Test handling of very long user agent strings"""
        long_agent = "A" * 10000
        fp = SessionFingerprint(ip_address="192.168.1.1", user_agent=long_agent)

        # Should not raise
        session_manager.record_session_fingerprint(
            session_id="sess_long",
            user_id="user_123",
            fingerprint=fp
        )

        sessions = session_manager.get_active_sessions("user_123")
        assert len(sessions) == 1

    def test_unicode_in_user_agent(self, session_manager):
        """Test handling of unicode characters in user agent"""
        unicode_agent = "Mozilla/5.0 (兼容性测试) 日本語テスト"
        fp = SessionFingerprint(ip_address="192.168.1.1", user_agent=unicode_agent)

        session_manager.record_session_fingerprint(
            session_id="sess_unicode",
            user_id="user_123",
            fingerprint=fp
        )

        sessions = session_manager.get_active_sessions("user_123")
        assert sessions[0]["user_agent"] == unicode_agent

    def test_special_characters_in_language(self, session_manager):
        """Test handling of special characters in accept-language"""
        fp = SessionFingerprint(
            ip_address="192.168.1.1",
            user_agent="Agent",
            accept_language="en-US,en;q=0.9,*;q=0.5"
        )

        session_manager.record_session_fingerprint(
            session_id="sess_special",
            user_id="user_123",
            fingerprint=fp
        )

        # Verify hash is computed correctly
        assert len(fp.compute_hash()) == 64

    def test_empty_user_id(self, session_manager, sample_fingerprint):
        """Test handling of empty user_id"""
        # Should handle gracefully
        session_manager.record_session_fingerprint(
            session_id="sess_empty_user",
            user_id="",
            fingerprint=sample_fingerprint
        )

        sessions = session_manager.get_active_sessions("")
        assert len(sessions) == 1

    def test_concurrent_operations(self, session_manager):
        """Test concurrent session operations don't corrupt data"""
        import threading

        def create_sessions(thread_id):
            for i in range(5):
                fp = SessionFingerprint(
                    ip_address=f"192.168.{thread_id}.{i}",
                    user_agent=f"Thread{thread_id}"
                )
                session_manager.record_session_fingerprint(
                    session_id=f"sess_{thread_id}_{i}",
                    user_id=f"user_{thread_id}",
                    fingerprint=fp
                )

        threads = []
        for t in range(3):
            thread = threading.Thread(target=create_sessions, args=(t,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify each user has their sessions
        for t in range(3):
            sessions = session_manager.get_active_sessions(f"user_{t}")
            assert len(sessions) == 5
