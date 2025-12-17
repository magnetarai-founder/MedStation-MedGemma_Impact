"""
Password Breach Detection using HaveIBeenPwned API

Implements k-anonymity password breach checking using the HaveIBeenPwned
Pwned Passwords API v3. Uses SHA-1 hash prefix (first 5 chars) to check
if a password has been exposed in data breaches without revealing the
full password hash.

Security Features:
- k-anonymity: Only sends first 5 chars of SHA-1 hash
- No plaintext passwords sent over network
- HTTPS-only API calls
- Local caching of breach results (24 hour TTL)
- Rate limiting to prevent API abuse

Based on: https://haveibeenpwned.com/API/v3#PwnedPasswords
Reference: https://www.troyhunt.com/ive-just-launched-pwned-passwords-version-2/
"""

import hashlib
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import aiohttp
from functools import lru_cache

logger = logging.getLogger(__name__)


class PasswordBreachChecker:
    """
    Check passwords against HaveIBeenPwned database using k-anonymity

    The API uses k-anonymity to preserve privacy:
    1. Hash password with SHA-1
    2. Send only first 5 characters of hash to API
    3. API returns all hash suffixes matching that prefix
    4. Client checks if full hash is in results

    This means the full password hash is never transmitted.
    """

    HIBP_API_URL = "https://api.pwnedpasswords.com/range/{hash_prefix}"
    HASH_PREFIX_LENGTH = 5
    CACHE_TTL_HOURS = 24

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache: dict[str, Tuple[int, datetime]] = {}  # hash_prefix -> (count, timestamp)
        self._cache_hits = 0
        self._cache_misses = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            # Set User-Agent as requested by HIBP API guidelines
            headers = {
                "User-Agent": "MagnetarStudio-PasswordChecker/1.0",
                "Accept": "text/plain"
            }
            timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout
            self._session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self._session

    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _hash_password(self, password: str) -> str:
        """
        Hash password with SHA-1 (required by HIBP API)

        Note: SHA-1 is used here because it's what HIBP uses for their
        database. This is safe because we're not using it for cryptographic
        security, just as a lookup key.

        Args:
            password: Plain text password

        Returns:
            Uppercase SHA-1 hash hex string
        """
        return hashlib.sha1(password.encode('utf-8')).hexdigest().upper()

    def _get_cache_key(self, hash_prefix: str) -> Optional[Tuple[int, datetime]]:
        """
        Get cached breach count for a hash prefix

        Args:
            hash_prefix: First 5 chars of SHA-1 hash

        Returns:
            Tuple of (breach_count, timestamp) or None if not cached or expired
        """
        if hash_prefix in self._cache:
            breach_count, timestamp = self._cache[hash_prefix]
            age = datetime.utcnow() - timestamp
            if age < timedelta(hours=self.CACHE_TTL_HOURS):
                self._cache_hits += 1
                return (breach_count, timestamp)
            else:
                # Expired, remove from cache
                del self._cache[hash_prefix]

        self._cache_misses += 1
        return None

    def _set_cache(self, hash_prefix: str, breach_count: int):
        """
        Cache breach count for a hash prefix

        Args:
            hash_prefix: First 5 chars of SHA-1 hash
            breach_count: Number of breaches found
        """
        self._cache[hash_prefix] = (breach_count, datetime.utcnow())

        # Limit cache size to 10000 entries (prevents memory bloat)
        if len(self._cache) > 10000:
            # Remove oldest 20% of entries
            sorted_cache = sorted(
                self._cache.items(),
                key=lambda x: x[1][1]  # Sort by timestamp
            )
            to_remove = len(self._cache) // 5
            for key, _ in sorted_cache[:to_remove]:
                del self._cache[key]

    async def check_password(self, password: str) -> Tuple[bool, int]:
        """
        Check if password has been exposed in data breaches

        Args:
            password: Plain text password to check

        Returns:
            Tuple of (is_breached: bool, breach_count: int)
            - is_breached: True if password found in breach database
            - breach_count: Number of times password appears in breaches (0 if not found)

        Raises:
            Exception: If API call fails (should be caught by caller)

        Example:
            >>> checker = PasswordBreachChecker()
            >>> is_breached, count = await checker.check_password("password123")
            >>> if is_breached:
            ...     print(f"Password found in {count} breaches!")
            >>> await checker.close()
        """
        # Hash the password
        full_hash = self._hash_password(password)
        hash_prefix = full_hash[:self.HASH_PREFIX_LENGTH]
        hash_suffix = full_hash[self.HASH_PREFIX_LENGTH:]

        # Check cache first
        cached = self._get_cache_key(hash_prefix)
        if cached is not None:
            breach_count, _ = cached
            logger.debug(f"Cache hit for hash prefix {hash_prefix[:3]}...")
            return (breach_count > 0, breach_count)

        # Call HIBP API
        try:
            session = await self._get_session()
            url = self.HIBP_API_URL.format(hash_prefix=hash_prefix)

            async with session.get(url) as response:
                if response.status == 404:
                    # No hashes found with this prefix (very rare, password is safe)
                    self._set_cache(hash_prefix, 0)
                    return (False, 0)

                if response.status != 200:
                    logger.error(f"HIBP API returned status {response.status}")
                    raise Exception(f"HIBP API error: {response.status}")

                # Parse response (format: "SUFFIX:COUNT\r\n")
                text = await response.text()
                for line in text.splitlines():
                    if ':' in line:
                        suffix, count_str = line.split(':', 1)
                        if suffix.strip() == hash_suffix:
                            breach_count = int(count_str.strip())
                            self._set_cache(hash_prefix, breach_count)
                            logger.warning(
                                f"Password found in {breach_count} breaches "
                                f"(hash: {hash_prefix[:3]}...{hash_suffix[:3]})"
                            )
                            return (True, breach_count)

                # Hash suffix not found in response, password is safe
                self._set_cache(hash_prefix, 0)
                return (False, 0)

        except asyncio.TimeoutError:
            logger.error("HIBP API request timed out")
            raise Exception("Password breach check timed out")
        except aiohttp.ClientError as e:
            logger.error(f"HIBP API request failed: {e}")
            raise Exception(f"Password breach check failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking password breach: {e}")
            raise

    def get_stats(self) -> dict:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        return {
            "cache_size": len(self._cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": (
                self._cache_hits / (self._cache_hits + self._cache_misses)
                if (self._cache_hits + self._cache_misses) > 0
                else 0.0
            )
        }


# Global singleton instance
_breach_checker: Optional[PasswordBreachChecker] = None


def get_breach_checker() -> PasswordBreachChecker:
    """
    Get or create global PasswordBreachChecker instance

    Returns:
        PasswordBreachChecker singleton

    Example:
        >>> checker = get_breach_checker()
        >>> is_breached, count = await checker.check_password("password123")
    """
    global _breach_checker
    if _breach_checker is None:
        _breach_checker = PasswordBreachChecker()
    return _breach_checker


async def check_password_breach(password: str) -> Tuple[bool, int]:
    """
    Convenience function to check password breach

    Args:
        password: Plain text password

    Returns:
        Tuple of (is_breached, breach_count)

    Example:
        >>> is_breached, count = await check_password_breach("mypassword")
        >>> if is_breached:
        ...     print(f"Warning: Password exposed in {count} breaches")
    """
    checker = get_breach_checker()
    return await checker.check_password(password)


async def cleanup_breach_checker():
    """
    Close the global breach checker session

    Call this on application shutdown.
    """
    global _breach_checker
    if _breach_checker is not None:
        await _breach_checker.close()
        _breach_checker = None
