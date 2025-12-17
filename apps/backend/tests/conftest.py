"""
Shared pytest fixtures for MagnetarStudio tests.

Provides:
- Database fixtures (test database, migrations, cleanup)
- API client fixtures (authenticated and unauthenticated)
- User fixtures (regular user, admin, founder)
- Mock external services (Ollama, ANE)
- Test data factories
"""

import os
import sys
import sqlite3
import tempfile
import pytest
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, UTC

# Add api to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.db_utils import get_sqlite_connection


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_db_path() -> Generator[Path, None, None]:
    """
    Create a temporary database file for the entire test session.

    Yields:
        Path to temporary database file
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    yield tmp_path

    # Cleanup
    try:
        tmp_path.unlink()
        # Clean up WAL files
        wal_path = tmp_path.with_suffix(".db-wal")
        if wal_path.exists():
            wal_path.unlink()
        shm_path = tmp_path.with_suffix(".db-shm")
        if shm_path.exists():
            shm_path.unlink()
    except Exception:
        pass


@pytest.fixture(scope="session")
def test_db_schema(test_db_path: Path) -> sqlite3.Connection:
    """
    Create test database schema once for the entire test session.

    Runs all migrations to set up the schema.

    Returns:
        SQLite connection with schema initialized
    """
    conn = get_sqlite_connection(test_db_path)

    # Run migrations
    try:
        # Auth migrations
        from api.migrations.auth import run_auth_migrations
        run_auth_migrations(conn)

        # Other migrations can be added here
        # from api.migrations.vault import run_vault_migrations
        # run_vault_migrations(conn)

    except ImportError as e:
        print(f"Warning: Could not import migrations: {e}")

    return conn


@pytest.fixture
def db(test_db_schema: sqlite3.Connection) -> Generator[sqlite3.Connection, None, None]:
    """
    Provide a clean database for each test with automatic rollback.

    Uses transactions to ensure each test starts with a clean state
    and doesn't affect other tests.

    Yields:
        SQLite connection with transaction started
    """
    # Start transaction
    test_db_schema.execute("BEGIN")

    yield test_db_schema

    # Rollback transaction (cleanup)
    test_db_schema.rollback()


@pytest.fixture
def empty_db() -> Generator[sqlite3.Connection, None, None]:
    """
    Provide a completely empty in-memory database.

    Useful for testing migrations or schema creation.

    Yields:
        SQLite connection to empty in-memory database
    """
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")

    yield conn

    conn.close()


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def founder_user(db: sqlite3.Connection) -> dict:
    """
    Create a founder user in the test database.

    Returns:
        Dict with user_id, username, email, role
    """
    from api.auth_bootstrap import ensure_dev_founder_user

    with patch.dict('os.environ', {
        "ELOHIM_ENV": "development",
        "ELOHIM_FOUNDER_USERNAME": "test_founder",
        "ELOHIM_FOUNDER_PASSWORD": "FounderPass123"
    }):
        ensure_dev_founder_user(db)

    # Get the created user
    user = db.execute("""
        SELECT user_id, username, email, role
        FROM users
        WHERE username = 'test_founder'
    """).fetchone()

    return {
        "user_id": user[0],
        "username": user[1],
        "email": user[2],
        "role": user[3],
        "password": "FounderPass123"
    }


@pytest.fixture
def regular_user(db: sqlite3.Connection) -> dict:
    """
    Create a regular user in the test database.

    Returns:
        Dict with user_id, username, email, role
    """
    from api.core.security import hash_password
    import uuid

    user_id = str(uuid.uuid4())
    username = "test_user"
    email = "test@example.com"
    password = "TestPass123"
    password_hash = hash_password(password)

    db.execute("""
        INSERT INTO users (user_id, username, email, password_hash, role, is_active)
        VALUES (?, ?, ?, ?, 'member', 1)
    """, (user_id, username, email, password_hash))

    return {
        "user_id": user_id,
        "username": username,
        "email": email,
        "role": "member",
        "password": password
    }


@pytest.fixture
def admin_user(db: sqlite3.Connection) -> dict:
    """
    Create an admin user in the test database.

    Returns:
        Dict with user_id, username, email, role
    """
    from api.core.security import hash_password
    import uuid

    user_id = str(uuid.uuid4())
    username = "test_admin"
    email = "admin@example.com"
    password = "AdminPass123"
    password_hash = hash_password(password)

    db.execute("""
        INSERT INTO users (user_id, username, email, password_hash, role, is_active)
        VALUES (?, ?, ?, ?, 'admin', 1)
    """, (user_id, username, email, password_hash))

    return {
        "user_id": user_id,
        "username": username,
        "email": email,
        "role": "admin",
        "password": password
    }


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture
def auth_token(founder_user: dict, db: sqlite3.Connection) -> str:
    """
    Generate a valid JWT token for the founder user.

    Returns:
        JWT token string
    """
    from api.core.security import create_access_token

    token = create_access_token(founder_user["user_id"])
    return token


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """
    Generate authentication headers with Bearer token.

    Returns:
        Dict of HTTP headers with Authorization
    """
    return {
        "Authorization": f"Bearer {auth_token}"
    }


@pytest.fixture
def regular_user_token(regular_user: dict, db: sqlite3.Connection) -> str:
    """
    Generate a valid JWT token for a regular user.

    Returns:
        JWT token string
    """
    from api.core.security import create_access_token

    token = create_access_token(regular_user["user_id"])
    return token


@pytest.fixture
def regular_user_headers(regular_user_token: str) -> dict:
    """
    Generate authentication headers for regular user.

    Returns:
        Dict of HTTP headers with Authorization
    """
    return {
        "Authorization": f"Bearer {regular_user_token}"
    }


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest.fixture
def api_client():
    """
    Create a test client for the FastAPI application.

    Returns:
        TestClient instance
    """
    from fastapi.testclient import TestClient

    # Import your FastAPI app
    try:
        from api.main import app
        return TestClient(app)
    except ImportError:
        # If main doesn't exist yet, create a minimal test app
        from fastapi import FastAPI
        test_app = FastAPI()
        return TestClient(test_app)


@pytest.fixture
def authenticated_client(api_client, auth_headers: dict, db: sqlite3.Connection):
    """
    Create an authenticated test client.

    The client automatically includes authentication headers in requests.
    """
    # Patch the database dependency to use test database
    from api.app_factory import get_db

    def override_get_db():
        yield db

    # This would need to be implemented in your actual app
    # api_client.app.dependency_overrides[get_db] = override_get_db

    # For now, just return client with headers
    api_client.headers.update(auth_headers)
    return api_client


# ============================================================================
# Mock External Services
# ============================================================================

@pytest.fixture
def mock_ollama():
    """
    Mock Ollama API responses.

    Returns:
        Mock object for Ollama client
    """
    mock = Mock()

    # Mock list_models
    mock.list_models.return_value = [
        {"name": "llama2", "size": "7B"},
        {"name": "codellama", "size": "13B"}
    ]

    # Mock generate
    mock.generate.return_value = {
        "response": "This is a mocked AI response.",
        "model": "llama2"
    }

    # Mock chat
    mock.chat.return_value = {
        "message": {
            "role": "assistant",
            "content": "This is a mocked chat response."
        }
    }

    return mock


@pytest.fixture
def mock_ane():
    """
    Mock Apple Neural Engine responses.

    Returns:
        Mock object for ANE context engine
    """
    mock = Mock()

    # Mock embedding generation
    mock.embed_text.return_value = [0.1] * 384  # Mock 384-dim embedding

    # Mock vectorization
    mock.preserve_context.return_value = None

    # Mock search
    mock.search_similar.return_value = [
        {"session_id": "test-session-1", "similarity": 0.95},
        {"session_id": "test-session-2", "similarity": 0.85}
    ]

    return mock


# ============================================================================
# Test Data Factories
# ============================================================================

@pytest.fixture
def chat_session_factory(db: sqlite3.Connection):
    """
    Factory for creating test chat sessions.

    Returns:
        Function that creates chat sessions
    """
    def create_session(user_id: str, title: str = "Test Chat", model: str = "llama2"):
        import uuid
        session_id = str(uuid.uuid4())

        db.execute("""
            INSERT INTO chat_sessions (id, user_id, title, model, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, user_id, title, model, datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat()))

        return session_id

    return create_session


@pytest.fixture
def chat_message_factory(db: sqlite3.Connection):
    """
    Factory for creating test chat messages.

    Returns:
        Function that creates chat messages
    """
    def create_message(session_id: str, role: str = "user", content: str = "Test message"):
        import uuid
        message_id = str(uuid.uuid4())

        db.execute("""
            INSERT INTO chat_messages (id, session_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (message_id, session_id, role, content, datetime.now(UTC).isoformat()))

        return message_id

    return create_message


@pytest.fixture
def vault_item_factory(db: sqlite3.Connection):
    """
    Factory for creating test vault items.

    Returns:
        Function that creates vault items
    """
    def create_item(user_id: str, name: str = "Test Item", content: str = "Test content"):
        import uuid
        item_id = str(uuid.uuid4())

        db.execute("""
            INSERT INTO vault_items (id, user_id, name, content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (item_id, user_id, name, content, datetime.now(UTC).isoformat(), datetime.now(UTC).isoformat()))

        return item_id

    return create_item


# ============================================================================
# Environment Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def test_environment():
    """
    Set up test environment variables.

    Automatically applied to all tests.
    """
    original_env = os.environ.copy()

    # Set test environment
    os.environ.update({
        "ELOHIM_ENV": "test",
        "DEBUG": "false",
        "JWT_SECRET_KEY": "test-secret-key-for-testing-only",
        "DATABASE_URL": ":memory:",
    })

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """
    Cleanup after each test.

    Automatically applied to all tests.
    """
    yield

    # Any cleanup needed after each test
    # e.g., clear caches, reset singletons, etc.


# ============================================================================
# Pytest Hooks
# ============================================================================

def pytest_configure(config):
    """Configure pytest."""
    # Add custom markers programmatically if needed
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    # You can modify test items here
    # e.g., skip tests based on conditions
    pass
