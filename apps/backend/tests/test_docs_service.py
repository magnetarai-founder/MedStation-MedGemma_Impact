"""
Comprehensive tests for api/docs_service.py

Tests collaborative document storage and syncing service with:
- Pydantic model validation (DocumentCreate, DocumentUpdate, Document)
- Database initialization and connection pooling
- CRUD operations (create, list, get, update, delete)
- Team-aware document access
- Batch sync with conflict resolution
- Security level validation
- SQL injection prevention via whitelist

Coverage targets: 90%+
"""

import pytest
import json
import sqlite3
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, UTC
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

# Import the module components
from api.docs_service import (
    router,
    init_db,
    get_db,
    release_db,
    build_safe_update,
    DOCUMENT_UPDATE_COLUMNS,
    VALID_DOC_TYPES,
    VALID_SECURITY_LEVELS,
    DocumentCreate,
    DocumentUpdate,
    Document,
    SyncRequest,
    SyncResponse,
)


# ========== Fixtures ==========

@pytest.fixture
def mock_current_user():
    """Mock authenticated user"""
    return {
        "user_id": "test-user-123",
        "username": "testuser",
        "role": "admin"
    }


@pytest.fixture
def app(mock_current_user):
    """Create FastAPI test app with router and auth override"""
    # Import the exact function reference that docs_service uses
    import api.docs_service as docs_module
    original_get_current_user = docs_module.get_current_user

    test_app = FastAPI()
    test_app.include_router(router)
    # Override using the exact function reference
    test_app.dependency_overrides[original_get_current_user] = lambda: mock_current_user
    return test_app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def client_not_team_member(mock_current_user):
    """Create test client with user not in team"""
    import api.docs_service as docs_module
    original_get_current_user = docs_module.get_current_user

    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[original_get_current_user] = lambda: mock_current_user

    with patch('api.docs_service.is_team_member', return_value=False):
        yield TestClient(test_app)


@pytest.fixture
def client_team_member(mock_current_user):
    """Create test client with user in team"""
    import api.docs_service as docs_module
    original_get_current_user = docs_module.get_current_user

    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[original_get_current_user] = lambda: mock_current_user

    with patch('api.docs_service.is_team_member', return_value=True):
        yield TestClient(test_app)


def make_row_mock(data: dict):
    """Create a mock that behaves like sqlite3.Row"""
    mock = MagicMock()
    mock.__getitem__ = lambda self, key: data[key]
    mock.keys = lambda: list(data.keys())
    return mock


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Initialize database
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            is_private INTEGER DEFAULT 0,
            security_level TEXT,
            shared_with TEXT DEFAULT '[]',
            team_id TEXT
        )
    """)
    conn.commit()
    conn.close()

    yield path

    # Cleanup
    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture
def sample_document_data():
    """Sample document creation data"""
    return {
        "type": "doc",
        "title": "Test Document",
        "content": {"blocks": [{"text": "Hello, world!"}]},
        "is_private": False,
        "security_level": "private"
    }


# ========== Model Validation Tests ==========

class TestDocumentCreate:
    """Tests for DocumentCreate model validation"""

    def test_valid_document(self):
        """Test valid document creation"""
        doc = DocumentCreate(
            type="doc",
            title="Test",
            content={"text": "hello"}
        )
        assert doc.type == "doc"
        assert doc.title == "Test"

    def test_valid_doc_types(self):
        """Test all valid document types"""
        for doc_type in VALID_DOC_TYPES:
            doc = DocumentCreate(type=doc_type, title="Test", content={})
            assert doc.type == doc_type

    def test_invalid_type(self):
        """Test invalid document type"""
        with pytest.raises(ValueError, match="type must be one of"):
            DocumentCreate(type="invalid", title="Test", content={})

    def test_empty_title(self):
        """Test empty title validation"""
        with pytest.raises(ValueError, match="title cannot be empty"):
            DocumentCreate(type="doc", title="   ", content={})

    def test_title_strip(self):
        """Test title whitespace is stripped"""
        doc = DocumentCreate(type="doc", title="  Test  ", content={})
        assert doc.title == "Test"

    def test_valid_security_levels(self):
        """Test all valid security levels"""
        for level in VALID_SECURITY_LEVELS:
            doc = DocumentCreate(
                type="doc",
                title="Test",
                content={},
                security_level=level
            )
            assert doc.security_level == level

    def test_invalid_security_level(self):
        """Test invalid security level"""
        with pytest.raises(ValueError, match="security_level must be one of"):
            DocumentCreate(
                type="doc",
                title="Test",
                content={},
                security_level="invalid"
            )

    def test_null_security_level_allowed(self):
        """Test None security level is allowed"""
        doc = DocumentCreate(
            type="doc",
            title="Test",
            content={},
            security_level=None
        )
        assert doc.security_level is None


class TestDocumentUpdate:
    """Tests for DocumentUpdate model validation"""

    def test_all_optional(self):
        """Test all fields are optional"""
        update = DocumentUpdate()
        assert update.title is None
        assert update.content is None
        assert update.is_private is None

    def test_partial_update(self):
        """Test partial update with some fields"""
        update = DocumentUpdate(title="New Title")
        assert update.title == "New Title"
        assert update.content is None

    def test_empty_title_validation(self):
        """Test empty title validation"""
        with pytest.raises(ValueError, match="title cannot be empty"):
            DocumentUpdate(title="   ")

    def test_title_strip(self):
        """Test title whitespace is stripped"""
        update = DocumentUpdate(title="  Updated  ")
        assert update.title == "Updated"

    def test_invalid_security_level(self):
        """Test invalid security level in update"""
        with pytest.raises(ValueError, match="security_level must be one of"):
            DocumentUpdate(security_level="invalid")

    def test_shared_with_list(self):
        """Test shared_with accepts list of strings"""
        update = DocumentUpdate(shared_with=["user1", "user2"])
        assert update.shared_with == ["user1", "user2"]


class TestDocument:
    """Tests for Document model"""

    def test_document_creation(self):
        """Test document model creation"""
        doc = Document(
            id="doc_123",
            type="doc",
            title="Test",
            content={"text": "hello"},
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            created_by="user_123"
        )
        assert doc.id == "doc_123"
        assert doc.is_private is False  # default
        assert doc.shared_with == []  # default

    def test_document_with_all_fields(self):
        """Test document with all fields"""
        doc = Document(
            id="doc_123",
            type="sheet",
            title="Test Sheet",
            content={"rows": []},
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-02T00:00:00",
            created_by="user_123",
            is_private=True,
            security_level="top-secret",
            shared_with=["user_456"],
            team_id="team_789"
        )
        assert doc.is_private is True
        assert doc.security_level == "top-secret"
        assert doc.team_id == "team_789"


class TestSyncModels:
    """Tests for SyncRequest and SyncResponse models"""

    def test_sync_request(self):
        """Test SyncRequest model"""
        req = SyncRequest(
            documents=[{"id": "doc_1", "title": "Test"}],
            last_sync="2024-01-01T00:00:00"
        )
        assert len(req.documents) == 1
        assert req.last_sync == "2024-01-01T00:00:00"

    def test_sync_request_no_last_sync(self):
        """Test SyncRequest without last_sync"""
        req = SyncRequest(documents=[])
        assert req.last_sync is None

    def test_sync_response(self):
        """Test SyncResponse model"""
        resp = SyncResponse(
            updated_documents=[],
            conflicts=[],
            sync_timestamp="2024-01-01T00:00:00"
        )
        assert resp.updated_documents == []
        assert resp.conflicts == []


# ========== build_safe_update Tests ==========

class TestBuildSafeUpdate:
    """Tests for build_safe_update function"""

    def test_valid_columns(self):
        """Test with valid columns"""
        updates = {"title": "New Title", "content": "New Content"}
        clauses, params = build_safe_update(updates, DOCUMENT_UPDATE_COLUMNS)

        assert "title = ?" in clauses
        assert "content = ?" in clauses
        assert "New Title" in params
        assert "New Content" in params

    def test_invalid_column(self):
        """Test with invalid column raises ValueError"""
        updates = {"invalid_column": "value"}
        with pytest.raises(ValueError, match="Invalid column for update"):
            build_safe_update(updates, DOCUMENT_UPDATE_COLUMNS)

    def test_empty_updates(self):
        """Test with empty updates dict"""
        clauses, params = build_safe_update({}, DOCUMENT_UPDATE_COLUMNS)
        assert clauses == []
        assert params == []

    def test_all_allowed_columns(self):
        """Test all allowed columns work"""
        updates = {
            "title": "Test",
            "content": "{}",
            "is_private": 1,
            "security_level": "private",
            "shared_with": "[]",
            "updated_at": "2024-01-01"
        }
        clauses, params = build_safe_update(updates, DOCUMENT_UPDATE_COLUMNS)
        assert len(clauses) == 6
        assert len(params) == 6


# ========== Constants Tests ==========

class TestConstants:
    """Tests for module constants"""

    def test_valid_doc_types(self):
        """Test valid document types"""
        assert VALID_DOC_TYPES == {"doc", "sheet", "insight"}

    def test_valid_security_levels(self):
        """Test valid security levels"""
        assert VALID_SECURITY_LEVELS == {"public", "private", "team", "sensitive", "top-secret"}

    def test_update_columns_whitelist(self):
        """Test update columns whitelist"""
        expected = {"title", "content", "is_private", "security_level", "shared_with", "updated_at"}
        assert DOCUMENT_UPDATE_COLUMNS == expected


# ========== Database Tests ==========

class TestDatabase:
    """Tests for database functions"""

    def test_init_db_creates_table(self, temp_db):
        """Test init_db creates documents table"""
        with patch('api.docs_service.DOCS_DB_PATH', Path(temp_db)):
            init_db()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_init_db_creates_indexes(self, temp_db):
        """Test init_db creates indexes"""
        with patch('api.docs_service.DOCS_DB_PATH', Path(temp_db)):
            init_db()

        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "idx_updated_at" in indexes
        assert "idx_created_by" in indexes
        assert "idx_team_id" in indexes


# ========== CRUD Endpoint Tests ==========

class TestCreateDocument:
    """Tests for POST /documents endpoint"""

    def test_create_document_success(self, client, sample_document_data):
        """Test successful document creation"""
        with patch('api.docs_service.get_db') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor

            row_data = {
                "id": "doc_123",
                "type": "doc",
                "title": "Test Document",
                "content": '{"blocks": []}',
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "created_by": "test-user-123",
                "is_private": 0,
                "security_level": "private",
                "shared_with": "[]",
                "team_id": None
            }
            mock_cursor.fetchone.return_value = make_row_mock(row_data)
            mock_get_db.return_value = mock_conn

            response = client.post(
                "/api/v1/docs/documents",
                json=sample_document_data
            )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["type"] == "doc"

    def test_create_document_invalid_type(self, client):
        """Test document creation with invalid type"""
        response = client.post(
            "/api/v1/docs/documents",
            json={"type": "invalid", "title": "Test", "content": {}}
        )
        assert response.status_code == 422

    def test_create_document_empty_title(self, client):
        """Test document creation with empty title"""
        response = client.post(
            "/api/v1/docs/documents",
            json={"type": "doc", "title": "   ", "content": {}}
        )
        assert response.status_code == 422

    def test_create_team_document_not_member(self, client_not_team_member, sample_document_data):
        """Test creating team document when not a member"""
        response = client_not_team_member.post(
            "/api/v1/docs/documents",
            params={"team_id": "team-123"},
            json=sample_document_data
        )
        assert response.status_code == 403
        assert "Not a member" in response.json()["detail"]


class TestListDocuments:
    """Tests for GET /documents endpoint"""

    def test_list_documents_empty(self, client):
        """Test listing documents when none exist"""
        with patch('api.docs_service.get_db') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            mock_get_db.return_value = mock_conn

            response = client.get("/api/v1/docs/documents")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []

    def test_list_documents_with_since(self, client):
        """Test listing documents with since parameter"""
        with patch('api.docs_service.get_db') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            mock_get_db.return_value = mock_conn

            response = client.get(
                "/api/v1/docs/documents",
                params={"since": "2024-01-01T00:00:00"}
            )

        assert response.status_code == 200

    def test_list_team_documents_not_member(self, client_not_team_member):
        """Test listing team documents when not a member"""
        response = client_not_team_member.get(
            "/api/v1/docs/documents",
            params={"team_id": "team-123"}
        )
        assert response.status_code == 403


class TestGetDocument:
    """Tests for GET /documents/{doc_id} endpoint"""

    def test_get_document_not_found(self, client):
        """Test getting nonexistent document"""
        with patch('api.docs_service.get_db') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = None
            mock_get_db.return_value = mock_conn

            response = client.get("/api/v1/docs/documents/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_team_document_not_member(self, client_not_team_member):
        """Test getting team document when not a member"""
        response = client_not_team_member.get(
            "/api/v1/docs/documents/doc-123",
            params={"team_id": "team-123"}
        )
        assert response.status_code == 403


class TestUpdateDocument:
    """Tests for PATCH /documents/{doc_id} endpoint"""

    def test_update_document_not_found(self, client):
        """Test updating nonexistent document"""
        with patch('api.docs_service.get_db') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = None
            mock_get_db.return_value = mock_conn

            response = client.patch(
                "/api/v1/docs/documents/nonexistent",
                json={"title": "Updated"}
            )

        assert response.status_code == 404

    def test_update_team_document_not_member(self, client_not_team_member):
        """Test updating team document when not a member"""
        response = client_not_team_member.patch(
            "/api/v1/docs/documents/doc-123",
            params={"team_id": "team-123"},
            json={"title": "Updated"}
        )
        assert response.status_code == 403


class TestDeleteDocument:
    """Tests for DELETE /documents/{doc_id} endpoint"""

    def test_delete_document_not_found(self, client):
        """Test deleting nonexistent document"""
        with patch('api.docs_service.get_db') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.rowcount = 0
            mock_get_db.return_value = mock_conn

            response = client.delete("/api/v1/docs/documents/nonexistent")

        assert response.status_code == 404

    def test_delete_document_success(self, client):
        """Test successful document deletion"""
        with patch('api.docs_service.get_db') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.rowcount = 1
            mock_get_db.return_value = mock_conn

            response = client.delete("/api/v1/docs/documents/doc-123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["id"] == "doc-123"

    def test_delete_team_document_not_member(self, client_not_team_member):
        """Test deleting team document when not a member"""
        response = client_not_team_member.delete(
            "/api/v1/docs/documents/doc-123",
            params={"team_id": "team-123"}
        )
        assert response.status_code == 403


# ========== Sync Endpoint Tests ==========

class TestSyncEndpoint:
    """Tests for POST /sync endpoint"""

    def test_sync_empty_documents(self, client):
        """Test sync with empty documents list"""
        with patch('api.docs_service.get_db') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            mock_get_db.return_value = mock_conn

            response = client.post(
                "/api/v1/docs/sync",
                json={"documents": []}
            )

        assert response.status_code == 200
        data = response.json()
        assert "sync_timestamp" in data
        assert data["conflicts"] == []

    def test_sync_with_last_sync(self, client):
        """Test sync with last_sync timestamp"""
        with patch('api.docs_service.get_db') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = None
            mock_cursor.fetchall.return_value = []
            mock_get_db.return_value = mock_conn

            response = client.post(
                "/api/v1/docs/sync",
                json={
                    "documents": [],
                    "last_sync": "2024-01-01T00:00:00"
                }
            )

        assert response.status_code == 200

    def test_sync_document_without_id_skipped(self, client):
        """Test sync skips documents without ID"""
        with patch('api.docs_service.get_db') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.return_value = None
            mock_cursor.fetchall.return_value = []
            mock_get_db.return_value = mock_conn

            response = client.post(
                "/api/v1/docs/sync",
                json={
                    "documents": [{"title": "No ID"}]  # Missing id
                }
            )

        assert response.status_code == 200


# ========== Router Configuration Tests ==========

class TestRouterConfiguration:
    """Tests for router configuration"""

    def test_router_prefix(self):
        """Test router has correct prefix"""
        assert router.prefix == "/api/v1/docs"

    def test_router_tags(self):
        """Test router has correct tags"""
        assert "Docs" in router.tags

    def test_router_has_expected_routes(self):
        """Test router has expected routes"""
        routes = [r.path for r in router.routes]

        # Routes include the prefix /api/v1/docs
        assert "/api/v1/docs/documents" in routes
        assert "/api/v1/docs/documents/{doc_id}" in routes
        assert "/api/v1/docs/sync" in routes


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_unicode_title(self, client, sample_document_data):
        """Test document with unicode title"""
        sample_document_data["title"] = "日本語ドキュメント 📄"

        with patch('api.docs_service.get_db') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor

            row_data = {
                "id": "doc_123",
                "type": "doc",
                "title": "日本語ドキュメント 📄",
                "content": '{}',
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "created_by": "test-user-123",
                "is_private": 0,
                "security_level": None,
                "shared_with": "[]",
                "team_id": None
            }
            mock_cursor.fetchone.return_value = make_row_mock(row_data)
            mock_get_db.return_value = mock_conn

            response = client.post(
                "/api/v1/docs/documents",
                json=sample_document_data
            )

        assert response.status_code == 200

    def test_complex_content(self, client):
        """Test document with complex nested content"""
        complex_content = {
            "blocks": [
                {"type": "heading", "text": "Title", "level": 1},
                {"type": "paragraph", "text": "Hello"},
                {
                    "type": "table",
                    "rows": [
                        [{"cell": "A1"}, {"cell": "B1"}],
                        [{"cell": "A2"}, {"cell": "B2"}]
                    ]
                }
            ]
        }

        with patch('api.docs_service.get_db') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor

            row_data = {
                "id": "doc_123",
                "type": "doc",
                "title": "Complex Doc",
                "content": json.dumps(complex_content),
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "created_by": "test-user-123",
                "is_private": 0,
                "security_level": None,
                "shared_with": "[]",
                "team_id": None
            }
            mock_cursor.fetchone.return_value = make_row_mock(row_data)
            mock_get_db.return_value = mock_conn

            response = client.post(
                "/api/v1/docs/documents",
                json={
                    "type": "doc",
                    "title": "Complex Doc",
                    "content": complex_content
                }
            )

        assert response.status_code == 200

    def test_all_security_levels_in_update(self):
        """Test all security levels work in update"""
        for level in VALID_SECURITY_LEVELS:
            update = DocumentUpdate(security_level=level)
            assert update.security_level == level

    def test_shared_with_empty_list(self):
        """Test shared_with with empty list"""
        update = DocumentUpdate(shared_with=[])
        assert update.shared_with == []

    def test_very_long_title(self):
        """Test title at max length"""
        long_title = "A" * 500
        doc = DocumentCreate(type="doc", title=long_title, content={})
        assert len(doc.title) == 500

    def test_title_over_max_length(self):
        """Test title over max length"""
        long_title = "A" * 501
        with pytest.raises(ValueError):
            DocumentCreate(type="doc", title=long_title, content={})


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests"""

    def test_document_crud_flow(self, client):
        """Test complete CRUD flow"""
        # Create document
        with patch('api.docs_service.get_db') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor

            # Mock for create
            row_data = {
                "id": "doc_test",
                "type": "doc",
                "title": "Test Doc",
                "content": '{"text": "hello"}',
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "created_by": "test-user-123",
                "is_private": 0,
                "security_level": "private",
                "shared_with": "[]",
                "team_id": None
            }
            mock_cursor.fetchone.return_value = make_row_mock(row_data)
            mock_get_db.return_value = mock_conn

            create_response = client.post(
                "/api/v1/docs/documents",
                json={
                    "type": "doc",
                    "title": "Test Doc",
                    "content": {"text": "hello"},
                    "security_level": "private"
                }
            )

        assert create_response.status_code == 200

        # Delete document
        with patch('api.docs_service.get_db') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.rowcount = 1
            mock_get_db.return_value = mock_conn

            delete_response = client.delete("/api/v1/docs/documents/doc_test")

        assert delete_response.status_code == 200

    def test_team_document_workflow(self, client_team_member):
        """Test team document workflow"""
        with patch('api.docs_service.get_db') as mock_get_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor

            # Mock for create
            row_data = {
                "id": "doc_team",
                "type": "doc",
                "title": "Team Doc",
                "content": '{}',
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "created_by": "test-user-123",
                "is_private": 0,
                "security_level": "team",
                "shared_with": "[]",
                "team_id": "team-123"
            }
            mock_cursor.fetchone.return_value = make_row_mock(row_data)
            mock_get_db.return_value = mock_conn

            response = client_team_member.post(
                "/api/v1/docs/documents",
                params={"team_id": "team-123"},
                json={
                    "type": "doc",
                    "title": "Team Doc",
                    "content": {},
                    "security_level": "team"
                }
            )

        assert response.status_code == 200
        assert response.json()["team_id"] == "team-123"
