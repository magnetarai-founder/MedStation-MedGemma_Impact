"""
Tests for Context Router

Tests REST API endpoints for ANE Context Engine semantic search and context storage.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.context_router import router
from api.auth_middleware import get_current_user


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    return {"user_id": "test_user_123", "email": "test@example.com"}


@pytest.fixture
def mock_engine():
    """Create mock ANE context engine"""
    engine = MagicMock()
    engine.search_similar.return_value = [
        {
            "session_id": "sess_123",
            "similarity": 0.85,
            "metadata": {
                "workspace": "vault",
                "content": "Test document content about machine learning"
            }
        },
        {
            "session_id": "sess_456",
            "similarity": 0.72,
            "metadata": {
                "workspace": "chat",
                "content": "Previous conversation about AI models"
            }
        }
    ]
    engine.stats.return_value = {
        "sessions_stored": 100,
        "processed_count": 500,
        "error_count": 2,
        "queue_size": 5,
        "workers": 2,
        "retention_days": 30.0
    }
    return engine


@pytest.fixture
def app(mock_user):
    """Create FastAPI app with context router and mocked dependencies"""
    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.include_router(router)
    return app


@pytest.fixture
def client(app, mock_engine):
    """Create test client with patched engine"""
    with patch("api.context_router.get_ane_engine", return_value=mock_engine):
        with patch("api.ane_context_engine._embed_with_ane", return_value=[0.1] * 384):
            yield TestClient(app)


class TestContextSearch:
    """Test context search endpoint"""

    def test_search_returns_results(self, client):
        """Test searching for context returns results"""
        response = client.post(
            "/api/v1/context/search",
            json={"query": "machine learning models", "limit": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_found" in data
        assert "query_embedding_dims" in data
        assert len(data["results"]) == 2

    def test_search_result_structure(self, client):
        """Test search results have correct structure"""
        response = client.post(
            "/api/v1/context/search",
            json={"query": "AI"}
        )

        assert response.status_code == 200
        data = response.json()
        result = data["results"][0]

        assert "source" in result
        assert "content" in result
        assert "relevance_score" in result
        assert "metadata" in result
        assert result["source"] == "vault"
        assert result["relevance_score"] == 0.85

    def test_search_with_workspace_filter(self, client, mock_engine):
        """Test filtering by workspace types"""
        response = client.post(
            "/api/v1/context/search",
            json={
                "query": "test query",
                "workspace_types": ["vault", "chat"],
                "limit": 5
            }
        )

        assert response.status_code == 200
        # Verify search was called
        mock_engine.search_similar.assert_called_once()

    def test_search_with_session_id(self, client):
        """Test search with session ID"""
        response = client.post(
            "/api/v1/context/search",
            json={
                "query": "context query",
                "session_id": "sess_abc",
                "limit": 10
            }
        )

        assert response.status_code == 200

    def test_search_embedding_dims_in_response(self, client):
        """Test query embedding dimensions are returned"""
        response = client.post(
            "/api/v1/context/search",
            json={"query": "test"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query_embedding_dims"] == 384


class TestContextStore:
    """Test context store endpoint"""

    def test_store_context_success(self, client, mock_engine):
        """Test storing context successfully"""
        response = client.post(
            "/api/v1/context/store",
            json={
                "session_id": "sess_new_123",
                "workspace_type": "chat",
                "content": "This is a test conversation about programming",
                "metadata": {"topic": "programming", "language": "python"}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["session_id"] == "sess_new_123"

    def test_store_context_enqueues_vectorization(self, client, mock_engine):
        """Test that storing context enqueues for vectorization"""
        client.post(
            "/api/v1/context/store",
            json={
                "session_id": "sess_vec_123",
                "workspace_type": "vault",
                "content": "Document content to vectorize",
                "metadata": {}
            }
        )

        # Verify enqueue was called
        mock_engine.enqueue_vectorization.assert_called_once()
        call_args = mock_engine.enqueue_vectorization.call_args
        assert call_args.kwargs["session_id"] == "sess_vec_123"

    def test_store_context_includes_metadata(self, client, mock_engine):
        """Test metadata is included in stored context"""
        client.post(
            "/api/v1/context/store",
            json={
                "session_id": "sess_meta_123",
                "workspace_type": "data",
                "content": "SQL query results",
                "metadata": {"query": "SELECT * FROM users", "rows": 100}
            }
        )

        call_args = mock_engine.enqueue_vectorization.call_args
        context = call_args.kwargs["context"]
        assert context["workspace"] == "data"
        assert context["content"] == "SQL query results"
        assert "query" in context
        assert context["rows"] == 100


class TestContextStatus:
    """Test context status endpoint"""

    def test_status_returns_engine_stats(self, client):
        """Test status endpoint returns engine statistics"""
        response = client.get("/api/v1/context/status")

        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert data["backend"] == "ANE"
        assert data["vector_count"] == 100
        assert data["queue_depth"] == 5
        assert data["processed_count"] == 500
        assert data["error_count"] == 2
        assert data["workers"] == 2

    def test_status_includes_features(self, client):
        """Test status includes feature flags"""
        response = client.get("/api/v1/context/status")

        assert response.status_code == 200
        data = response.json()
        assert "features" in data
        features = data["features"]
        assert features["semantic_search"] is True
        assert features["ane_acceleration"] is True
        assert features["background_vectorization"] is True

    def test_status_returns_retention_days(self, client):
        """Test status returns retention configuration"""
        response = client.get("/api/v1/context/status")

        assert response.status_code == 200
        data = response.json()
        assert data["retention_days"] == 30.0

    def test_status_when_engine_unavailable(self, app, mock_user):
        """Test status when engine throws exception"""
        def raise_error():
            raise RuntimeError("Engine not available")

        with patch("api.context_router.get_ane_engine", side_effect=raise_error):
            with TestClient(app) as client:
                response = client.get("/api/v1/context/status")

                assert response.status_code == 200
                data = response.json()
                assert data["available"] is False
                assert "error" in data


class TestContextSearchError:
    """Test error handling in context search"""

    def test_search_handles_engine_error(self, app, mock_user):
        """Test search handles engine errors gracefully"""
        mock_engine = MagicMock()
        mock_engine.search_similar.side_effect = RuntimeError("Search failed")

        with patch("api.context_router.get_ane_engine", return_value=mock_engine):
            with patch("api.ane_context_engine._embed_with_ane", return_value=[0.1] * 384):
                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/context/search",
                        json={"query": "test"}
                    )

                    assert response.status_code == 500
                    assert "Context search failed" in response.json()["detail"]


class TestContextStoreError:
    """Test error handling in context store"""

    def test_store_handles_engine_error(self, app, mock_user):
        """Test store handles engine errors gracefully"""
        mock_engine = MagicMock()
        mock_engine.enqueue_vectorization.side_effect = RuntimeError("Queue full")

        with patch("api.context_router.get_ane_engine", return_value=mock_engine):
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/context/store",
                    json={
                        "session_id": "sess_error",
                        "workspace_type": "chat",
                        "content": "Test content",
                        "metadata": {}
                    }
                )

                assert response.status_code == 500
                assert "Store context failed" in response.json()["detail"]
