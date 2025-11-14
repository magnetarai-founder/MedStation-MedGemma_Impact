"""
Test Configuration and Fixtures for ElohimOS Backend Tests

Sets up isolated test environment with temporary data directory,
database fixtures, and dependency overrides for FastAPI.
"""

import os
import sqlite3
import pytest
from pathlib import Path
from typing import Generator
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def temp_data_dir(tmp_path_factory) -> Path:
    """
    Create a unique temporary data directory for the test session.
    Sets ELOHIMOS_DATA_DIR env var BEFORE importing the app.
    """
    tmp_dir = tmp_path_factory.mktemp("elohimos_test_data")

    # Set environment variable before any app imports
    os.environ["ELOHIMOS_DATA_DIR"] = str(tmp_dir)
    os.environ["ELOHIM_ENV"] = "development"  # Enable dev mode for tests

    return tmp_dir


@pytest.fixture(scope="session")
def app(temp_data_dir):
    """
    Import and configure FastAPI app with test data directory.
    Override get_current_user dependency to return static test user.
    """
    # Import AFTER setting ELOHIMOS_DATA_DIR
    from api.main import app
    from api.auth_middleware import get_current_user

    # Override dependency to return static test user
    def override_get_current_user():
        return {
            "user_id": "test_user",
            "username": "tester",
            "role": "member",
            "is_active": 1
        }

    app.dependency_overrides[get_current_user] = override_get_current_user

    yield app

    # Cleanup: restore dependencies
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def client(app) -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient that triggers lifespan startup (runs migrations).
    Function-scoped to ensure clean state per test.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def db_connection(temp_data_dir):
    """
    Direct SQLite connection to app database for seeding and assertions.
    Automatically closes after test.
    """
    from api.config_paths import PATHS

    conn = sqlite3.connect(PATHS.app_db)
    conn.row_factory = sqlite3.Row

    yield conn

    conn.close()


@pytest.fixture(scope="function")
def vault_db_connection(temp_data_dir):
    """
    Direct SQLite connection to vault database for seeding and assertions.
    Automatically closes after test.
    """
    from api.config_paths import PATHS

    conn = sqlite3.connect(PATHS.vault_db)
    conn.row_factory = sqlite3.Row

    yield conn

    conn.close()


def run_sql(db_path: Path, query: str, params: tuple = ()):
    """
    Helper to run raw SQL against a database.

    Args:
        db_path: Path to SQLite database
        query: SQL query to execute
        params: Query parameters (optional)

    Returns:
        For SELECT: list of Row objects
        For INSERT/UPDATE/DELETE: rowcount
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(query, params)

        if query.strip().upper().startswith("SELECT"):
            result = cursor.fetchall()
        else:
            conn.commit()
            result = cursor.rowcount

        return result
    finally:
        conn.close()
