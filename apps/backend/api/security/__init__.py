"""
Security Package for MedStation

Comprehensive security utilities including:
- SQL injection prevention
- End-to-end encryption (NaCl/libsodium)
- Encrypted database storage
- Password breach detection (HaveIBeenPwned)
- Session security and anomaly detection
- Device identity management
- Emergency data wipe (DoD 5220.22-M)
- Rate limiting (token bucket)
- Team cryptography (key derivation, HMAC signing)
"""

import logging

logger = logging.getLogger(__name__)

# SQL Safety (existing) - always available
from api.security.sql_safety import (
    SQLInjectionError,
    validate_identifier,
    quote_identifier,
    validate_and_quote,
    SafeSQLBuilder,
    build_update_sql,
)

# E2E Encryption (NaCl) - requires nacl package
try:
    from api.security.e2e_encryption import (
        E2EEncryptionService,
        get_e2e_service,
    )
except ImportError:
    E2EEncryptionService = None
    get_e2e_service = None
    logger.debug("E2E encryption unavailable - nacl package not installed")

# Encrypted Database - requires cryptography package
try:
    from api.security.encrypted_db import (
        EncryptedDatabase,
        BackupCodesService,
        get_encrypted_database,
    )
except ImportError:
    EncryptedDatabase = None
    BackupCodesService = None
    get_encrypted_database = None
    logger.debug("Encrypted database unavailable - cryptography package not installed")

# Password Breach Checker - requires aiohttp
try:
    from api.security.password_breach import (
        PasswordBreachChecker,
        get_breach_checker,
        check_password_breach,
        cleanup_breach_checker,
    )
except ImportError:
    PasswordBreachChecker = None
    get_breach_checker = None
    check_password_breach = None
    cleanup_breach_checker = None
    logger.debug("Password breach checker unavailable - aiohttp package not installed")

# Session Security - always available
from api.security.session import (
    SessionFingerprint,
    SessionAnomalyResult,
    SessionSecurityManager,
    get_session_security_manager,
)

# Device Identity - always available
from api.security.device_identity import (
    ensure_device_identity,
    get_device_identity,
)

# Emergency Wipe - always available
from api.security.emergency_wipe import (
    perform_dod_wipe,
    wipe_single_file,
)

# Rate Limiter - always available
from api.security.rate_limiter import (
    RateLimiter,
    rate_limiter,
    get_client_ip,
    ConnectionCodeLimiter,
    connection_code_limiter,
)

# Team Crypto - requires cryptography package
try:
    from api.security.team_crypto import (
        get_device_secret,
        derive_team_key,
        sign_team_payload,
        verify_team_payload,
    )
except ImportError:
    get_device_secret = None
    derive_team_key = None
    sign_team_payload = None
    verify_team_payload = None
    logger.debug("Team crypto unavailable - cryptography package not installed")

__all__ = [
    # SQL Safety
    "SQLInjectionError",
    "validate_identifier",
    "quote_identifier",
    "validate_and_quote",
    "SafeSQLBuilder",
    "build_update_sql",
    # E2E Encryption (optional)
    "E2EEncryptionService",
    "get_e2e_service",
    # Encrypted Database (optional)
    "EncryptedDatabase",
    "BackupCodesService",
    "get_encrypted_database",
    # Password Breach (optional)
    "PasswordBreachChecker",
    "get_breach_checker",
    "check_password_breach",
    "cleanup_breach_checker",
    # Session Security
    "SessionFingerprint",
    "SessionAnomalyResult",
    "SessionSecurityManager",
    "get_session_security_manager",
    # Device Identity
    "ensure_device_identity",
    "get_device_identity",
    # Emergency Wipe
    "perform_dod_wipe",
    "wipe_single_file",
    # Rate Limiter
    "RateLimiter",
    "rate_limiter",
    "get_client_ip",
    "ConnectionCodeLimiter",
    "connection_code_limiter",
    # Team Crypto (optional)
    "get_device_secret",
    "derive_team_key",
    "sign_team_payload",
    "verify_team_payload",
]
