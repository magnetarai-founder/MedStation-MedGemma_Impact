"""
Comprehensive tests for password_breach_checker.py

Tests cover:
- Password hashing (SHA-1)
- Cache operations (get/set, TTL, thread safety, size limits)
- HIBP API calls (success, failure, timeout, offline mode)
- Singleton pattern
- Session management
- Statistics tracking

Coverage target: 100%
"""

import pytest
import asyncio
import hashlib
import threading
from datetime import datetime, timedelta, UTC
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import aiohttp

from api.password_breach_checker import (
    PasswordBreachChecker,
    get_breach_checker,
    check_password_breach,
    cleanup_breach_checker,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def checker():
    """Create a fresh PasswordBreachChecker instance"""
    return PasswordBreachChecker()


@pytest.fixture
def checker_with_cache(checker):
    """Create checker with pre-populated cache"""
    # Add some cached entries
    now = datetime.now(UTC)
    checker._cache = {
        "ABCDE": (100, now),  # Breached password
        "12345": (0, now),     # Safe password
        "OLDEE": (50, now - timedelta(hours=25)),  # Expired entry
    }
    return checker


@pytest.fixture
async def cleanup_global():
    """Cleanup global singleton after test"""
    yield
    await cleanup_breach_checker()


# =============================================================================
# Password Hashing Tests
# =============================================================================

class TestPasswordHashing:
    """Tests for SHA-1 password hashing"""

    def test_hash_password_basic(self, checker):
        """Test basic password hashing"""
        result = checker._hash_password("password123")

        # Should be SHA-1 hash
        expected = hashlib.sha1(b"password123").hexdigest().upper()
        assert result == expected
        assert len(result) == 40  # SHA-1 is 40 hex chars

    def test_hash_password_uppercase(self, checker):
        """Test that hash is uppercase"""
        result = checker._hash_password("test")
        assert result == result.upper()

    def test_hash_password_empty(self, checker):
        """Test hashing empty string"""
        result = checker._hash_password("")
        expected = hashlib.sha1(b"").hexdigest().upper()
        assert result == expected

    def test_hash_password_unicode(self, checker):
        """Test hashing unicode passwords"""
        result = checker._hash_password("пароль123")
        expected = hashlib.sha1("пароль123".encode('utf-8')).hexdigest().upper()
        assert result == expected

    def test_hash_password_special_chars(self, checker):
        """Test hashing passwords with special characters"""
        result = checker._hash_password("P@$$w0rd!#%")
        assert len(result) == 40

    def test_hash_password_deterministic(self, checker):
        """Test that hashing is deterministic"""
        password = "testpassword"
        hash1 = checker._hash_password(password)
        hash2 = checker._hash_password(password)
        assert hash1 == hash2

    def test_hash_password_different_inputs(self, checker):
        """Test that different passwords produce different hashes"""
        hash1 = checker._hash_password("password1")
        hash2 = checker._hash_password("password2")
        assert hash1 != hash2


# =============================================================================
# Cache Tests
# =============================================================================

class TestCache:
    """Tests for cache operations"""

    def test_get_cache_key_hit(self, checker_with_cache):
        """Test cache hit for valid entry"""
        result = checker_with_cache._get_cache_key("ABCDE")
        assert result is not None
        breach_count, timestamp = result
        assert breach_count == 100

    def test_get_cache_key_miss(self, checker_with_cache):
        """Test cache miss for non-existent entry"""
        result = checker_with_cache._get_cache_key("XXXXX")
        assert result is None

    def test_get_cache_key_expired(self, checker_with_cache):
        """Test that expired entries return None and are removed"""
        result = checker_with_cache._get_cache_key("OLDEE")
        assert result is None
        # Entry should be removed
        assert "OLDEE" not in checker_with_cache._cache

    def test_get_cache_key_safe_password(self, checker_with_cache):
        """Test cache hit for safe password (count=0)"""
        result = checker_with_cache._get_cache_key("12345")
        assert result is not None
        breach_count, _ = result
        assert breach_count == 0

    def test_set_cache_basic(self, checker):
        """Test basic cache set"""
        checker._set_cache("AAAAA", 500)
        assert "AAAAA" in checker._cache
        breach_count, timestamp = checker._cache["AAAAA"]
        assert breach_count == 500

    def test_set_cache_timestamp(self, checker):
        """Test that cache timestamp is set correctly"""
        before = datetime.now(UTC)
        checker._set_cache("BBBBB", 10)
        after = datetime.now(UTC)

        _, timestamp = checker._cache["BBBBB"]
        assert before <= timestamp <= after

    def test_set_cache_overwrites(self, checker):
        """Test that setting same key overwrites"""
        checker._set_cache("CCCCC", 100)
        checker._set_cache("CCCCC", 200)

        breach_count, _ = checker._cache["CCCCC"]
        assert breach_count == 200

    def test_cache_size_limit(self, checker):
        """Test that cache is pruned when exceeding 10000 entries"""
        # Fill cache with 10001 entries
        base_time = datetime.now(UTC)
        for i in range(10001):
            # Use sequential timestamps so we can predict pruning
            checker._cache[f"{i:05X}"] = (i, base_time + timedelta(seconds=i))

        # Add one more entry to trigger pruning
        checker._set_cache("ZZZZZ", 999)

        # Should have pruned ~20% of entries (20% of 10001 = ~2000)
        # After pruning: 10001 - 2000 = 8001, plus new entry = 8002
        assert len(checker._cache) <= 8002

    def test_cache_prune_removes_oldest(self, checker):
        """Test that pruning removes oldest entries"""
        base_time = datetime.now(UTC) - timedelta(hours=3)  # Start in the past

        # Add entries with increasing timestamps (all in the past)
        for i in range(10001):
            checker._cache[f"{i:05X}"] = (i, base_time + timedelta(seconds=i))

        # Trigger pruning by adding new entry (will have current time = newest)
        checker._set_cache("ZZZZZ", 999)

        # Oldest entries should be removed (lowest indices = oldest timestamps)
        # Pruning removes ~20% = 2000 entries, so entries 0-1999 should be gone
        assert "00000" not in checker._cache
        assert "00001" not in checker._cache
        # Entry at index 2000+ should remain (after pruning boundary)
        assert "007D0" in checker._cache  # Index 2000
        # Newest entries should remain (ZZZZZ has current time, so it's newest)
        assert "ZZZZZ" in checker._cache

    def test_cache_hit_tracking(self, checker_with_cache):
        """Test cache hit counter"""
        initial_hits = checker_with_cache._cache_hits

        checker_with_cache._get_cache_key("ABCDE")  # Hit
        checker_with_cache._get_cache_key("ABCDE")  # Hit again

        assert checker_with_cache._cache_hits == initial_hits + 2

    def test_cache_miss_tracking(self, checker_with_cache):
        """Test cache miss counter"""
        initial_misses = checker_with_cache._cache_misses

        checker_with_cache._get_cache_key("XXXXX")  # Miss
        checker_with_cache._get_cache_key("YYYYY")  # Miss

        assert checker_with_cache._cache_misses == initial_misses + 2

    def test_cache_thread_safety(self, checker):
        """Test that cache operations are thread-safe"""
        errors = []
        iterations = 100

        def reader():
            try:
                for i in range(iterations):
                    checker._get_cache_key(f"{i:05X}")
            except Exception as e:
                errors.append(e)

        def writer():
            try:
                for i in range(iterations):
                    checker._set_cache(f"{i:05X}", i)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# =============================================================================
# API Call Tests
# =============================================================================

class TestCheckPassword:
    """Tests for check_password method"""

    @pytest.mark.asyncio
    async def test_check_password_found_in_breaches(self, checker):
        """Test password found in breach database"""
        # Mock the API response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=(
            "0018A45C4D1DEF81644B54AB7F969B88D65:100\r\n"  # Some hash
            "1E4C9B93F3F0682250B6CF8331B7EE68FD8:5000\r\n"  # Another hash
        ))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.closed = False

        # Set up password that will match second hash suffix
        # SHA1("password") starts with 5BAA6...
        with patch.object(checker, '_get_session', return_value=mock_session):
            with patch.object(checker, '_hash_password', return_value="5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8"):
                is_breached, count = await checker.check_password("password")

        assert is_breached is True
        assert count == 5000

    @pytest.mark.asyncio
    async def test_check_password_not_found(self, checker):
        """Test password not found in breach database"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=(
            "0018A45C4D1DEF81644B54AB7F969B88D65:100\r\n"
            "1111111111111111111111111111111111111:500\r\n"
        ))
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.closed = False

        with patch.object(checker, '_get_session', return_value=mock_session):
            with patch.object(checker, '_hash_password', return_value="ABCDE9999999999999999999999999999999999"):
                is_breached, count = await checker.check_password("unique_password")

        assert is_breached is False
        assert count == 0

    @pytest.mark.asyncio
    async def test_check_password_api_404(self, checker):
        """Test API returns 404 (no hashes with prefix)"""
        mock_response = Mock()
        mock_response.status = 404
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.closed = False

        with patch.object(checker, '_get_session', return_value=mock_session):
            is_breached, count = await checker.check_password("some_password")

        assert is_breached is False
        assert count == 0

    @pytest.mark.asyncio
    async def test_check_password_api_error_status(self, checker):
        """Test API returns error status code"""
        mock_response = Mock()
        mock_response.status = 500
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.closed = False

        with patch.object(checker, '_get_session', return_value=mock_session):
            with pytest.raises(Exception) as exc_info:
                await checker.check_password("test_password")

        assert "HIBP API error: 500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_check_password_timeout(self, checker):
        """Test API request timeout"""
        mock_session = Mock()
        mock_session.closed = False

        # Create a context manager that raises TimeoutError
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = Mock(return_value=mock_cm)

        with patch.object(checker, '_get_session', return_value=mock_session):
            with pytest.raises(Exception) as exc_info:
                await checker.check_password("test_password")

        assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_check_password_client_error(self, checker):
        """Test aiohttp client error"""
        mock_session = Mock()
        mock_session.closed = False

        # Create a context manager that raises ClientError
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Connection refused"))
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = Mock(return_value=mock_cm)

        with patch.object(checker, '_get_session', return_value=mock_session):
            with pytest.raises(Exception) as exc_info:
                await checker.check_password("test_password")

        assert "failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_check_password_uses_cache(self, checker_with_cache):
        """Test that cached results are used"""
        # Pre-cache a result
        checker_with_cache._cache["5BAA6"] = (1000, datetime.now(UTC))

        # Should not make API call
        with patch.object(checker_with_cache, '_get_session') as mock_get_session:
            with patch.object(checker_with_cache, '_hash_password', return_value="5BAA6XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"):
                is_breached, count = await checker_with_cache.check_password("password")

        mock_get_session.assert_not_called()
        assert is_breached is True
        assert count == 1000

    @pytest.mark.asyncio
    async def test_check_password_caches_result(self, checker):
        """Test that results are cached after API call"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1:50\r\n")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.closed = False

        with patch.object(checker, '_get_session', return_value=mock_session):
            with patch.object(checker, '_hash_password', return_value="ABCDEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1"):
                await checker.check_password("test")

        # Check cache was populated
        assert "ABCDE" in checker._cache


# =============================================================================
# Offline Mode Tests
# =============================================================================

class TestOfflineMode:
    """Tests for offline mode behavior"""

    @pytest.mark.asyncio
    async def test_offline_mode_skips_check(self, checker):
        """Test that offline mode skips breach check"""
        with patch('api.password_breach_checker.is_offline_mode', return_value=True):
            is_breached, count = await checker.check_password("any_password")

        assert is_breached is False
        assert count == 0

    @pytest.mark.asyncio
    async def test_offline_mode_no_api_call(self, checker):
        """Test that no API call is made in offline mode"""
        with patch('api.password_breach_checker.is_offline_mode', return_value=True):
            with patch.object(checker, '_get_session') as mock_session:
                await checker.check_password("any_password")

        mock_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_offline_mode_logs_warning(self, checker, caplog):
        """Test that offline mode logs a warning"""
        import logging
        with caplog.at_level(logging.WARNING):
            with patch('api.password_breach_checker.is_offline_mode', return_value=True):
                await checker.check_password("any_password")

        assert "SKIPPED" in caplog.text or "offline mode" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_online_mode_makes_api_call(self, checker):
        """Test that online mode makes API call"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.closed = False

        with patch('api.password_breach_checker.is_offline_mode', return_value=False):
            with patch.object(checker, '_get_session', return_value=mock_session):
                await checker.check_password("test_password")

        mock_session.get.assert_called_once()


# =============================================================================
# Session Management Tests
# =============================================================================

class TestSessionManagement:
    """Tests for aiohttp session management"""

    @pytest.mark.asyncio
    async def test_get_session_creates_session(self, checker):
        """Test that _get_session creates session when none exists"""
        assert checker._session is None

        session = await checker._get_session()

        assert session is not None
        assert isinstance(session, aiohttp.ClientSession)

        await checker.close()

    @pytest.mark.asyncio
    async def test_get_session_reuses_session(self, checker):
        """Test that _get_session reuses existing session"""
        session1 = await checker._get_session()
        session2 = await checker._get_session()

        assert session1 is session2

        await checker.close()

    @pytest.mark.asyncio
    async def test_get_session_recreates_closed(self, checker):
        """Test that _get_session recreates closed session"""
        session1 = await checker._get_session()
        await session1.close()

        session2 = await checker._get_session()

        assert session2 is not session1
        assert not session2.closed

        await checker.close()

    @pytest.mark.asyncio
    async def test_close_session(self, checker):
        """Test closing session"""
        await checker._get_session()
        assert checker._session is not None

        await checker.close()

        # Session should be closed
        assert checker._session.closed

    @pytest.mark.asyncio
    async def test_close_no_session(self, checker):
        """Test closing when no session exists"""
        # Should not raise
        await checker.close()

    @pytest.mark.asyncio
    async def test_session_headers(self, checker):
        """Test that session has correct headers"""
        session = await checker._get_session()

        # Check User-Agent is set
        assert "User-Agent" in session.headers
        assert "MagnetarStudio" in session.headers["User-Agent"]

        await checker.close()


# =============================================================================
# Statistics Tests
# =============================================================================

class TestStatistics:
    """Tests for get_stats method"""

    def test_get_stats_empty(self, checker):
        """Test stats for fresh checker"""
        stats = checker.get_stats()

        assert stats["cache_size"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["hit_rate"] == 0.0

    def test_get_stats_with_cache(self, checker_with_cache):
        """Test stats with cached entries"""
        stats = checker_with_cache.get_stats()

        assert stats["cache_size"] == 3  # ABCDE, 12345, OLDEE

    def test_get_stats_hit_rate(self, checker):
        """Test hit rate calculation"""
        checker._cache_hits = 3
        checker._cache_misses = 7

        stats = checker.get_stats()

        assert stats["hit_rate"] == pytest.approx(0.3)  # 3/(3+7)

    def test_get_stats_all_hits(self, checker):
        """Test hit rate with all hits"""
        checker._cache_hits = 10
        checker._cache_misses = 0

        stats = checker.get_stats()

        assert stats["hit_rate"] == 1.0

    def test_get_stats_all_misses(self, checker):
        """Test hit rate with all misses"""
        checker._cache_hits = 0
        checker._cache_misses = 10

        stats = checker.get_stats()

        assert stats["hit_rate"] == 0.0


# =============================================================================
# Global Functions Tests
# =============================================================================

class TestGlobalFunctions:
    """Tests for module-level functions"""

    @pytest.mark.asyncio
    async def test_get_breach_checker_singleton(self, cleanup_global):
        """Test that get_breach_checker returns singleton"""
        checker1 = get_breach_checker()
        checker2 = get_breach_checker()

        assert checker1 is checker2

    @pytest.mark.asyncio
    async def test_get_breach_checker_creates_instance(self, cleanup_global):
        """Test that get_breach_checker creates instance"""
        checker = get_breach_checker()

        assert checker is not None
        assert isinstance(checker, PasswordBreachChecker)

    @pytest.mark.asyncio
    async def test_check_password_breach_function(self, cleanup_global):
        """Test convenience function"""
        with patch('api.password_breach_checker.is_offline_mode', return_value=True):
            is_breached, count = await check_password_breach("test")

        assert is_breached is False
        assert count == 0

    @pytest.mark.asyncio
    async def test_cleanup_breach_checker(self, cleanup_global):
        """Test cleanup function"""
        import api.password_breach_checker as module

        # Create instance
        checker = get_breach_checker()
        await checker._get_session()

        # Cleanup
        await cleanup_breach_checker()

        # Global should be None
        assert module._breach_checker is None

    @pytest.mark.asyncio
    async def test_cleanup_breach_checker_no_instance(self):
        """Test cleanup when no instance exists"""
        import api.password_breach_checker as module
        module._breach_checker = None

        # Should not raise
        await cleanup_breach_checker()


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Edge case tests"""

    def test_hash_prefix_length_constant(self, checker):
        """Test hash prefix length is correct"""
        assert checker.HASH_PREFIX_LENGTH == 5

    def test_cache_ttl_constant(self, checker):
        """Test cache TTL is correct"""
        assert checker.CACHE_TTL_HOURS == 24

    def test_api_url_format(self, checker):
        """Test API URL format string"""
        url = checker.HIBP_API_URL.format(hash_prefix="ABCDE")
        assert url == "https://api.pwnedpasswords.com/range/ABCDE"

    @pytest.mark.asyncio
    async def test_empty_api_response(self, checker):
        """Test handling empty API response"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.closed = False

        with patch.object(checker, '_get_session', return_value=mock_session):
            is_breached, count = await checker.check_password("test")

        assert is_breached is False
        assert count == 0

    @pytest.mark.asyncio
    async def test_malformed_api_response_no_colon(self, checker):
        """Test handling malformed API response without colon"""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="INVALIDLINE\r\nANOTHER")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.closed = False

        with patch.object(checker, '_get_session', return_value=mock_session):
            is_breached, count = await checker.check_password("test")

        # Should handle gracefully - no match found
        assert is_breached is False
        assert count == 0

    @pytest.mark.asyncio
    async def test_api_response_whitespace(self, checker):
        """Test handling API response with extra whitespace"""
        mock_response = Mock()
        mock_response.status = 200
        # API returns SUFFIX:COUNT format - suffix has trailing spaces, count has surrounding spaces
        mock_response.text = AsyncMock(return_value="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1 : 50 \r\n")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.closed = False

        # Hash where suffix (after 5 chars) matches the response suffix (with strip)
        with patch.object(checker, '_get_session', return_value=mock_session):
            with patch.object(checker, '_hash_password', return_value="ABCDEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1"):
                is_breached, count = await checker.check_password("test")

        # Whitespace should be handled via strip()
        assert is_breached is True
        assert count == 50

    @pytest.mark.asyncio
    async def test_very_long_password(self, checker):
        """Test with very long password"""
        long_password = "a" * 10000
        result = checker._hash_password(long_password)

        # Should still produce valid 40-char SHA-1
        assert len(result) == 40

    @pytest.mark.asyncio
    async def test_concurrent_checks(self, checker):
        """Test concurrent password checks"""
        with patch('api.password_breach_checker.is_offline_mode', return_value=True):
            # Run multiple checks concurrently
            tasks = [
                checker.check_password(f"password{i}")
                for i in range(10)
            ]
            results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 10
        for is_breached, count in results:
            assert is_breached is False
            assert count == 0

    @pytest.mark.asyncio
    async def test_generic_exception_reraise(self, checker):
        """Test that generic exceptions are reraised"""
        mock_session = Mock()
        mock_session.closed = False

        # Create a context manager that raises ValueError
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=ValueError("Unexpected error"))
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = Mock(return_value=mock_cm)

        with patch.object(checker, '_get_session', return_value=mock_session):
            with pytest.raises(ValueError) as exc_info:
                await checker.check_password("test")

        assert "Unexpected error" in str(exc_info.value)


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration-style tests"""

    @pytest.mark.asyncio
    async def test_full_workflow_cache_miss_then_hit(self, checker):
        """Test full workflow: API call, cache, then cache hit"""
        mock_response = Mock()
        mock_response.status = 200
        # SHA1("test") = A94A8FE5CCB19BA61C4C0873D391E987982FBBD3
        # We want suffix after 5 chars: FE5CCB19BA61C4C0873D391E987982FBBD3
        mock_response.text = AsyncMock(return_value="FE5CCB19BA61C4C0873D391E987982FBBD3:777\r\n")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.closed = False

        with patch('api.password_breach_checker.is_offline_mode', return_value=False):
            with patch.object(checker, '_get_session', return_value=mock_session):
                # First call - API
                result1 = await checker.check_password("test")

                # Second call - should use cache
                result2 = await checker.check_password("test")

        # Both should return same result
        assert result1 == result2 == (True, 777)

        # API should only be called once
        assert mock_session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_stats_after_operations(self, checker):
        """Test stats reflect actual operations"""
        # Pre-populate cache
        now = datetime.now(UTC)
        checker._cache["A94A8"] = (100, now)

        with patch('api.password_breach_checker.is_offline_mode', return_value=False):
            # Cache hit
            with patch.object(checker, '_hash_password', return_value="A94A8XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"):
                await checker.check_password("test1")

            # Cache miss (offline mode will be used due to no session mock)
            with patch.object(checker, '_hash_password', return_value="BBBBBXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"):
                checker._get_cache_key("BBBBB")  # Direct miss

        stats = checker.get_stats()
        assert stats["cache_hits"] >= 1
        assert stats["cache_misses"] >= 1
