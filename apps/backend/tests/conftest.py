"""
Test fixtures and configuration for backend tests

Provides:
- Temporary database fixtures
- AuthService test instances
- JWT token generation helpers
- FastAPI test client setup
"""

import os
import sys
import pytest
import tempfile
import secrets
from pathlib import Path
from datetime import datetime, timedelta, UTC
from typing import Generator, Dict, Any

# Add backend to path for imports
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))
sys.path.insert(0, str(backend_root / "api"))

# Set test environment before importing modules
os.environ["ELOHIMOS_JWT_SECRET_KEY"] = "test-secret-key-for-unit-tests-only"
os.environ["ELOHIM_ENV"] = "test"


@pytest.fixture
def temp_db_path() -> Generator[Path, None, None]:
    """Create a temporary database file for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def auth_service(temp_db_path: Path):
    """Create an AuthService instance with temporary database"""
    import sqlite3
    from api.auth_middleware import AuthService
    from api.migrations.auth import auth_0001_initial

    # Apply auth migrations to temp database first (AUTH-P1 requirement)
    conn = sqlite3.connect(str(temp_db_path))
    auth_0001_initial.apply_migration(conn)
    conn.close()

    return AuthService(db_path=str(temp_db_path))


@pytest.fixture
def test_user(auth_service) -> Dict[str, Any]:
    """Create a test user and return user data"""
    device_id = secrets.token_urlsafe(8)
    user = auth_service.create_user(
        username="testuser",
        password="TestPassword123!",
        device_id=device_id
    )
    return {
        "user": user,
        "username": "testuser",
        "password": "TestPassword123!",
        "device_id": device_id
    }


@pytest.fixture
def authenticated_user(auth_service, test_user) -> Dict[str, Any]:
    """Create a test user and authenticate them, returning token data"""
    auth_result = auth_service.authenticate(
        username=test_user["username"],
        password=test_user["password"],
        device_fingerprint="test-fingerprint"
    )
    return {
        **test_user,
        "auth": auth_result,
        "token": auth_result["token"],
        "refresh_token": auth_result["refresh_token"]
    }


@pytest.fixture
def expired_token(auth_service, test_user) -> str:
    """Create an expired JWT token for testing"""
    import jwt
    from api.auth_middleware import JWT_SECRET, JWT_ALGORITHM

    # Create token that expired 1 hour ago
    expiration = datetime.now(UTC) - timedelta(hours=1)
    token_payload = {
        "user_id": "test-user-id",
        "username": test_user["username"],
        "device_id": test_user["device_id"],
        "role": "member",
        "exp": expiration.timestamp(),
        "iat": (expiration - timedelta(hours=1)).timestamp()
    }

    return jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@pytest.fixture
def malformed_tokens() -> Dict[str, str]:
    """Collection of malformed tokens for negative testing"""
    return {
        "empty": "",
        "not_jwt": "not-a-jwt-token",
        "missing_segments": "header.payload",
        "too_many_segments": "a.b.c.d",
        "invalid_base64": "!!!.@@@.###",
        "null": None,
    }


@pytest.fixture
def test_client():
    """Create FastAPI test client"""
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


@pytest.fixture
def audit_logger() -> Generator:
    """Create an AuditLogger instance with isolated temporary database"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        audit_db = Path(f.name)

    from api.audit_logger import AuditLogger
    logger = AuditLogger(db_path=audit_db)
    yield logger

    # Cleanup
    if audit_db.exists():
        audit_db.unlink()
