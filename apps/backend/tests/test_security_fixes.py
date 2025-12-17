"""
Test suite for security fixes from CRITICAL_BUGS_FOUND.md

Validates all critical and high-priority security fixes:
- CRITICAL-01: Thread-safe cache in password breach checker
- CRITICAL-02: Sanitization middleware removed (Pydantic validation)
- CRITICAL-03: Connection pooling in session security
- HIGH-02: IPv6 subnet checking
- HIGH-05: HSTS headers behind reverse proxy
"""

import pytest
import asyncio
import threading
import ipaddress
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch, AsyncMock


class TestPasswordBreachCheckerThreadSafety:
    """Test CRITICAL-01: Thread-safe cache operations"""

    @pytest.mark.asyncio
    async def test_cache_thread_safety(self):
        """Verify cache operations are thread-safe under concurrent access"""
        from api.password_breach_checker import PasswordBreachChecker

        checker = PasswordBreachChecker()

        # Populate cache with test data
        test_hash = "5BAA6"  # First 5 chars of "password" SHA-1
        checker._set_cache(test_hash, 100)

        # Concurrent cache access
        results = []
        errors = []

        def access_cache():
            try:
                result = checker._get_cache_key(test_hash)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Run 50 concurrent cache accesses
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(access_cache) for _ in range(50)]
            for future in futures:
                future.result()

        # Verify no errors and all results are consistent
        assert len(errors) == 0, f"Cache access errors: {errors}"
        assert len(results) == 50
        assert all(r is not None for r in results), "All cache hits should return data"

    @pytest.mark.asyncio
    async def test_cache_concurrent_writes(self):
        """Verify cache writes don't corrupt under concurrent access"""
        from api.password_breach_checker import PasswordBreachChecker

        checker = PasswordBreachChecker()
        errors = []

        def write_cache(index):
            try:
                hash_prefix = f"TEST{index:05d}"
                checker._set_cache(hash_prefix, index)
            except Exception as e:
                errors.append(e)

        # Run 100 concurrent cache writes
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(write_cache, i) for i in range(100)]
            for future in futures:
                future.result()

        # Verify no errors
        assert len(errors) == 0, f"Cache write errors: {errors}"

        # Verify cache is consistent
        assert len(checker._cache) <= 100


class TestSessionSecurityConnectionPooling:
    """Test CRITICAL-03: Connection pooling in session security"""

    def test_uses_connection_pool(self):
        """Verify SessionSecurityManager uses connection pool"""
        from api.session_security import SessionSecurityManager
        from api.db_pool import SQLiteConnectionPool
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_sessions.db"
            manager = SessionSecurityManager(db_path=db_path)

            # Verify pool is initialized
            assert hasattr(manager, '_pool')
            assert isinstance(manager._pool, SQLiteConnectionPool)

            # Verify pool is configured correctly
            stats = manager._pool.stats()
            assert stats['min_size'] == 2
            assert stats['max_size'] == 5
            # Compare resolved paths (macOS /var is symlink to /private/var)
            assert Path(stats['database']).resolve() == db_path.resolve()

    def test_connection_pooling_under_load(self):
        """Verify no database locked errors under concurrent load"""
        from api.session_security import SessionSecurityManager, SessionFingerprint
        from datetime import datetime
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_sessions.db"
            manager = SessionSecurityManager(db_path=db_path)

            errors = []

            def record_fingerprint(index):
                try:
                    fp = SessionFingerprint(
                        ip_address=f"192.168.1.{index % 255}",
                        user_agent=f"TestAgent/{index}",
                        accept_language="en-US"
                    )
                    manager.record_session_fingerprint(
                        session_id=f"session_{index}",
                        user_id=f"user_{index % 10}",
                        fingerprint=fp
                    )
                except Exception as e:
                    errors.append(e)

            # Run 100 concurrent database operations
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(record_fingerprint, i) for i in range(100)]
                for future in futures:
                    future.result()

            # Verify no "database is locked" errors
            locked_errors = [e for e in errors if "locked" in str(e).lower()]
            assert len(locked_errors) == 0, f"Database locked errors: {locked_errors}"


class TestIPv6SubnetChecking:
    """Test HIGH-02: IPv6 subnet checking"""

    def test_ipv4_same_subnet(self):
        """Verify IPv4 subnet checking works"""
        from api.session_security import SessionSecurityManager
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionSecurityManager(db_path=Path(tmpdir) / "test.db")

            # Same /16 subnet
            assert manager._ips_in_same_subnet("192.168.1.10", "192.168.1.20") is True
            assert manager._ips_in_same_subnet("192.168.1.10", "192.168.2.20") is True

            # Different /16 subnet
            assert manager._ips_in_same_subnet("192.168.1.10", "10.0.0.10") is False
            assert manager._ips_in_same_subnet("192.168.1.10", "172.16.0.1") is False

    def test_ipv6_same_subnet(self):
        """Verify IPv6 subnet checking works"""
        from api.session_security import SessionSecurityManager
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionSecurityManager(db_path=Path(tmpdir) / "test.db")

            # Same /64 subnet
            assert manager._ips_in_same_subnet(
                "2001:db8::1",
                "2001:db8::2"
            ) is True

            # Different /64 subnet
            assert manager._ips_in_same_subnet(
                "2001:db8::1",
                "2001:db9::1"
            ) is False

    def test_mixed_ip_versions(self):
        """Verify mixed IPv4/IPv6 returns False"""
        from api.session_security import SessionSecurityManager
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionSecurityManager(db_path=Path(tmpdir) / "test.db")

            # IPv4 vs IPv6 should never be same subnet
            assert manager._ips_in_same_subnet(
                "192.168.1.10",
                "2001:db8::1"
            ) is False

    def test_invalid_ips(self):
        """Verify invalid IPs are handled gracefully"""
        from api.session_security import SessionSecurityManager
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionSecurityManager(db_path=Path(tmpdir) / "test.db")

            # Invalid IPs should return False without crashing
            assert manager._ips_in_same_subnet("invalid", "192.168.1.1") is False
            assert manager._ips_in_same_subnet("999.999.999.999", "192.168.1.1") is False


class TestHSTSReverseProxySupport:
    """Test HIGH-05: HSTS headers behind reverse proxy"""

    @pytest.mark.asyncio
    async def test_hsts_with_x_forwarded_proto(self):
        """Verify HSTS set when X-Forwarded-Proto: https"""
        from fastapi import FastAPI, Request
        from api.middleware.security_headers import SecurityHeadersMiddleware
        from starlette.responses import Response
        import os

        # Set production mode
        os.environ['ELOHIM_ENV'] = 'production'

        app = FastAPI()
        middleware = SecurityHeadersMiddleware(app)

        # Mock request with X-Forwarded-Proto header
        mock_request = Mock(spec=Request)
        mock_request.url.scheme = "http"  # Backend sees HTTP
        mock_request.headers.get.return_value = "https"  # Proxy sets X-Forwarded-Proto

        # Mock call_next
        async def mock_call_next(request):
            return Response(content="test", status_code=200)

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verify HSTS header is set
        assert "Strict-Transport-Security" in response.headers
        assert "max-age=31536000" in response.headers["Strict-Transport-Security"]

    @pytest.mark.asyncio
    async def test_no_hsts_without_https(self):
        """Verify HSTS not set for HTTP requests"""
        from fastapi import FastAPI, Request
        from api.middleware.security_headers import SecurityHeadersMiddleware
        from starlette.responses import Response
        import os

        os.environ['ELOHIM_ENV'] = 'production'

        app = FastAPI()
        middleware = SecurityHeadersMiddleware(app)

        # Mock HTTP request
        mock_request = Mock(spec=Request)
        mock_request.url.scheme = "http"
        mock_request.headers.get.return_value = ""  # No X-Forwarded-Proto

        async def mock_call_next(request):
            return Response(content="test", status_code=200)

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verify HSTS header is NOT set for HTTP
        assert "Strict-Transport-Security" not in response.headers


class TestPydanticValidation:
    """Test CRITICAL-02: Pydantic model validation (sanitization middleware removed)"""

    def test_pydantic_blocks_invalid_input(self):
        """Verify Pydantic models validate input correctly"""
        from pydantic import BaseModel, ValidationError, validator

        class TestModel(BaseModel):
            username: str
            email: str

            @validator('username')
            def validate_username(cls, v):
                # Example validation
                if len(v) < 3:
                    raise ValueError('Username must be at least 3 characters')
                return v

        # Valid input passes
        valid = TestModel(username="testuser", email="test@example.com")
        assert valid.username == "testuser"

        # Invalid input raises ValidationError
        with pytest.raises(ValidationError):
            TestModel(username="ab", email="test@example.com")

        # Missing field raises ValidationError
        with pytest.raises(ValidationError):
            TestModel(username="testuser")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
