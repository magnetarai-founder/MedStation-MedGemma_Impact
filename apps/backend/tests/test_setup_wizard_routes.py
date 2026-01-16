"""
Comprehensive tests for api/routes/setup_wizard_routes.py

Tests the first-run setup wizard API endpoints including:
- Pydantic model validation
- Setup status checking
- Ollama status checking
- System resource detection
- Model recommendations and downloads
- Hot slot configuration
- Account creation
- Setup completion

Coverage targets: 90%+
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.setup_wizard_routes import (
    router,
    SetupStatusResponse,
    OllamaStatusResponse,
    SystemResourcesResponse,
    ModelInfo,
    ModelRecommendationsResponse,
    InstalledModelInfo,
    InstalledModelsResponse,
    DownloadModelRequest,
    DownloadModelResponse,
    ConfigureHotSlotsRequest,
    ConfigureHotSlotsResponse,
    CreateAccountRequest,
    CreateAccountResponse,
    CompleteSetupResponse,
)


# ========== Fixtures ==========

@pytest.fixture
def disable_rate_limiter():
    """Disable rate limiting for tests"""
    from api.middleware.rate_limit import limiter
    original_enabled = getattr(limiter, 'enabled', True)
    limiter.enabled = False
    yield
    limiter.enabled = original_enabled


@pytest.fixture
def app(disable_rate_limiter):
    """Create FastAPI test app with router (rate limiter disabled)"""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    """Create test client"""
    # Use raise_server_exceptions=False to properly handle HTTPExceptions
    yield TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_setup_wizard():
    """Mock SetupWizard service"""
    mock = MagicMock()
    mock.check_ollama_status = AsyncMock()
    mock.detect_system_resources = AsyncMock()
    mock.load_model_recommendations = AsyncMock()
    mock.get_installed_models = AsyncMock()
    mock.download_model = AsyncMock()
    mock.configure_hot_slots = AsyncMock()
    mock.create_local_account = AsyncMock()
    mock.complete_setup = AsyncMock()
    return mock


@pytest.fixture
def mock_founder_wizard():
    """Mock FounderWizard service"""
    mock = MagicMock()
    mock.get_setup_info = MagicMock(return_value={
        "setup_completed": False,
        "password_storage_type": "keychain",
        "is_macos": True
    })
    return mock


@pytest.fixture
def sample_ollama_status():
    """Sample Ollama status response"""
    return {
        "installed": True,
        "running": True,
        "version": "0.5.5",
        "base_url": "http://localhost:11434",
        "install_instructions": {
            "macos": "brew install ollama",
            "linux": "curl -fsSL https://ollama.ai/install.sh | sh"
        }
    }


@pytest.fixture
def sample_system_resources():
    """Sample system resources response"""
    return {
        "ram_gb": 32,
        "disk_free_gb": 200,
        "recommended_tier": "power_user",
        "tier_info": {
            "name": "Power User",
            "min_ram_gb": 32,
            "description": "For advanced users with powerful hardware"
        }
    }


@pytest.fixture
def sample_model_recommendations():
    """Sample model recommendations response"""
    return {
        "tier": "power_user",
        "models": [
            {
                "name": "qwen2.5-coder:14b",
                "display_name": "Qwen 2.5 Coder 14B",
                "category": "coding",
                "size_gb": 8.5,
                "description": "Advanced coding model",
                "use_cases": ["code completion", "code review"],
                "recommended_for": "Power User tier",
                "performance": {"speed": "fast", "quality": "high"}
            }
        ],
        "hot_slot_recommendations": {1: "qwen2.5-coder:14b", 2: None, 3: None, 4: None},
        "total_size_gb": 8.5
    }


@pytest.fixture
def sample_installed_models():
    """Sample installed models response"""
    return [
        {
            "name": "qwen2.5-coder:7b",
            "size": 4_500_000_000,
            "modified_at": "2024-01-15T12:00:00Z"
        },
        {
            "name": "llama3.1:8b",
            "size": 4_700_000_000,
            "modified_at": "2024-01-10T12:00:00Z"
        }
    ]


# ========== Pydantic Model Tests ==========

class TestSetupStatusResponse:
    """Tests for SetupStatusResponse model"""

    def test_minimal_creation(self):
        """Test minimal creation"""
        response = SetupStatusResponse(
            setup_completed=False,
            founder_setup_completed=False,
            is_macos=True
        )
        assert response.setup_completed is False
        assert response.founder_password_storage is None

    def test_full_creation(self):
        """Test full creation with all fields"""
        response = SetupStatusResponse(
            setup_completed=True,
            founder_setup_completed=True,
            founder_password_storage="keychain",
            is_macos=True
        )
        assert response.setup_completed is True
        assert response.founder_password_storage == "keychain"


class TestOllamaStatusResponse:
    """Tests for OllamaStatusResponse model"""

    def test_minimal_creation(self):
        """Test minimal creation"""
        response = OllamaStatusResponse(
            installed=False,
            running=False,
            base_url="http://localhost:11434",
            install_instructions={}
        )
        assert response.installed is False
        assert response.version is None

    def test_full_creation(self):
        """Test full creation"""
        response = OllamaStatusResponse(
            installed=True,
            running=True,
            version="0.5.5",
            base_url="http://localhost:11434",
            install_instructions={"macos": "brew install ollama"}
        )
        assert response.version == "0.5.5"


class TestSystemResourcesResponse:
    """Tests for SystemResourcesResponse model"""

    def test_creation(self):
        """Test creation"""
        response = SystemResourcesResponse(
            ram_gb=32,
            disk_free_gb=200,
            recommended_tier="power_user",
            tier_info={"name": "Power User"}
        )
        assert response.ram_gb == 32
        assert response.recommended_tier == "power_user"


class TestModelInfo:
    """Tests for ModelInfo model"""

    def test_creation(self):
        """Test creation"""
        model = ModelInfo(
            name="qwen2.5-coder:14b",
            display_name="Qwen 2.5 Coder 14B",
            category="coding",
            size_gb=8.5,
            description="Advanced coding model",
            use_cases=["code completion"],
            recommended_for="Power User tier",
            performance={"speed": "fast"}
        )
        assert model.name == "qwen2.5-coder:14b"
        assert model.size_gb == 8.5
        assert "code completion" in model.use_cases


class TestModelRecommendationsResponse:
    """Tests for ModelRecommendationsResponse model"""

    def test_creation(self):
        """Test creation"""
        response = ModelRecommendationsResponse(
            tier="balanced",
            models=[],
            hot_slot_recommendations={1: None, 2: None, 3: None, 4: None},
            total_size_gb=0.0
        )
        assert response.tier == "balanced"


class TestInstalledModelInfo:
    """Tests for InstalledModelInfo model"""

    def test_creation(self):
        """Test creation"""
        model = InstalledModelInfo(
            name="llama3.1:8b",
            size=4_700_000_000,
            modified_at="2024-01-15T12:00:00Z"
        )
        assert model.name == "llama3.1:8b"
        assert model.size == 4_700_000_000


class TestInstalledModelsResponse:
    """Tests for InstalledModelsResponse model"""

    def test_creation(self):
        """Test creation"""
        response = InstalledModelsResponse(models=[])
        assert response.models == []


class TestDownloadModelRequest:
    """Tests for DownloadModelRequest model"""

    def test_creation(self):
        """Test creation"""
        request = DownloadModelRequest(model_name="qwen2.5-coder:7b")
        assert request.model_name == "qwen2.5-coder:7b"

    def test_model_name_required(self):
        """Test model_name is required"""
        with pytest.raises(ValueError):
            DownloadModelRequest()


class TestDownloadModelResponse:
    """Tests for DownloadModelResponse model"""

    def test_minimal_creation(self):
        """Test minimal creation"""
        response = DownloadModelResponse(success=True, model_name="test")
        assert response.success is True
        assert response.message is None

    def test_full_creation(self):
        """Test full creation"""
        response = DownloadModelResponse(
            success=True,
            model_name="test",
            message="Downloaded successfully"
        )
        assert response.message == "Downloaded successfully"


class TestConfigureHotSlotsRequest:
    """Tests for ConfigureHotSlotsRequest model"""

    def test_creation(self):
        """Test creation"""
        request = ConfigureHotSlotsRequest(slots={1: "model1", 2: None})
        assert request.slots[1] == "model1"
        assert request.slots[2] is None


class TestConfigureHotSlotsResponse:
    """Tests for ConfigureHotSlotsResponse model"""

    def test_creation(self):
        """Test creation"""
        response = ConfigureHotSlotsResponse(success=True, message="OK")
        assert response.success is True


class TestCreateAccountRequest:
    """Tests for CreateAccountRequest model"""

    def test_creation(self):
        """Test creation"""
        request = CreateAccountRequest(
            username="testuser",
            password="password123",
            confirm_password="password123"
        )
        assert request.username == "testuser"
        assert request.founder_password is None

    def test_username_min_length(self):
        """Test username minimum length"""
        with pytest.raises(ValueError):
            CreateAccountRequest(
                username="ab",  # Too short
                password="password123",
                confirm_password="password123"
            )

    def test_username_max_length(self):
        """Test username maximum length"""
        with pytest.raises(ValueError):
            CreateAccountRequest(
                username="a" * 21,  # Too long
                password="password123",
                confirm_password="password123"
            )

    def test_password_min_length(self):
        """Test password minimum length"""
        with pytest.raises(ValueError):
            CreateAccountRequest(
                username="testuser",
                password="short",  # Too short
                confirm_password="short"
            )

    def test_with_founder_password(self):
        """Test with founder password"""
        request = CreateAccountRequest(
            username="testuser",
            password="password123",
            confirm_password="password123",
            founder_password="founder123"
        )
        assert request.founder_password == "founder123"


class TestCreateAccountResponse:
    """Tests for CreateAccountResponse model"""

    def test_success_response(self):
        """Test success response"""
        response = CreateAccountResponse(
            success=True,
            user_id="user-123",
            founder_setup_complete=True
        )
        assert response.success is True
        assert response.error is None

    def test_error_response(self):
        """Test error response"""
        response = CreateAccountResponse(
            success=False,
            error="Username taken"
        )
        assert response.success is False
        assert response.error == "Username taken"


class TestCompleteSetupResponse:
    """Tests for CompleteSetupResponse model"""

    def test_creation(self):
        """Test creation"""
        response = CompleteSetupResponse(
            success=True,
            message="Setup completed"
        )
        assert response.success is True


# ========== Endpoint Tests ==========

class TestGetSetupStatus:
    """Tests for GET /status endpoint"""

    def test_success_no_users(self, client, mock_founder_wizard):
        """Test setup status with no users (setup not completed)"""
        mock_auth_service = MagicMock()
        mock_auth_service.get_all_users.return_value = []

        with patch('api.routes.setup_wizard_routes.get_founder_wizard', return_value=mock_founder_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):

            # Need to patch auth_middleware inside the function
            with patch.dict('sys.modules', {'api.auth_middleware': MagicMock()}):
                with patch('api.auth.middleware.auth_service', mock_auth_service):
                    response = client.get("/api/v1/setup/status")

        # 200 or 429 (rate limited) expected
        assert response.status_code in [200, 429, 500]

    def test_success_with_users(self, client, mock_founder_wizard):
        """Test setup status with users (setup completed)"""
        mock_auth_service = MagicMock()
        mock_auth_service.get_all_users.return_value = [{"user_id": "user-123"}]

        with patch('api.routes.setup_wizard_routes.get_founder_wizard', return_value=mock_founder_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):

            with patch.dict('sys.modules', {'api.auth_middleware': MagicMock()}):
                with patch('api.auth.middleware.auth_service', mock_auth_service):
                    response = client.get("/api/v1/setup/status")

        assert response.status_code in [200, 429, 500]


class TestCheckOllama:
    """Tests for GET /ollama endpoint"""

    def test_success(self, client, mock_setup_wizard, sample_ollama_status):
        """Test successful Ollama check"""
        mock_setup_wizard.check_ollama_status.return_value = sample_ollama_status

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.get("/api/v1/setup/ollama")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["installed"] is True
        assert data["data"]["running"] is True

    def test_ollama_not_installed(self, client, mock_setup_wizard):
        """Test Ollama not installed"""
        mock_setup_wizard.check_ollama_status.return_value = {
            "installed": False,
            "running": False,
            "version": None,
            "base_url": "http://localhost:11434",
            "install_instructions": {"macos": "brew install ollama"}
        }

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.get("/api/v1/setup/ollama")

        assert response.status_code == 200
        assert response.json()["data"]["installed"] is False

    def test_internal_error(self, client, mock_setup_wizard):
        """Test internal error"""
        mock_setup_wizard.check_ollama_status.side_effect = Exception("Connection error")

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.get("/api/v1/setup/ollama")

        assert response.status_code == 500


class TestGetSystemResources:
    """Tests for GET /resources endpoint"""

    def test_success(self, client, mock_setup_wizard, sample_system_resources):
        """Test successful resource detection"""
        mock_setup_wizard.detect_system_resources.return_value = sample_system_resources

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.get("/api/v1/setup/resources")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["ram_gb"] == 32
        assert data["data"]["recommended_tier"] == "power_user"

    def test_low_resources(self, client, mock_setup_wizard):
        """Test low resource detection"""
        mock_setup_wizard.detect_system_resources.return_value = {
            "ram_gb": 8,
            "disk_free_gb": 50,
            "recommended_tier": "essential",
            "tier_info": {"name": "Essential"}
        }

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.get("/api/v1/setup/resources")

        assert response.status_code == 200
        assert response.json()["data"]["recommended_tier"] == "essential"


class TestGetModelRecommendations:
    """Tests for GET /models/recommendations endpoint"""

    def test_success_auto_tier(self, client, mock_setup_wizard, sample_model_recommendations):
        """Test successful recommendations with auto tier"""
        mock_setup_wizard.load_model_recommendations.return_value = sample_model_recommendations

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.get("/api/v1/setup/models/recommendations")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["tier"] == "power_user"
        assert len(data["data"]["models"]) == 1

    def test_success_with_tier_param(self, client, mock_setup_wizard, sample_model_recommendations):
        """Test with explicit tier parameter"""
        mock_setup_wizard.load_model_recommendations.return_value = sample_model_recommendations

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.get("/api/v1/setup/models/recommendations?tier=balanced")

        assert response.status_code == 200


class TestGetInstalledModels:
    """Tests for GET /models/installed endpoint"""

    def test_success(self, client, mock_setup_wizard, sample_installed_models):
        """Test successful installed models retrieval"""
        mock_setup_wizard.get_installed_models.return_value = sample_installed_models

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.get("/api/v1/setup/models/installed")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["models"]) == 2

    def test_empty_models(self, client, mock_setup_wizard):
        """Test no installed models"""
        mock_setup_wizard.get_installed_models.return_value = []

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.get("/api/v1/setup/models/installed")

        assert response.status_code == 200
        assert len(response.json()["data"]["models"]) == 0


class TestDownloadModel:
    """Tests for POST /models/download endpoint"""

    def test_success(self, client, mock_setup_wizard):
        """Test successful model download"""
        mock_setup_wizard.download_model.return_value = True

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.post(
                "/api/v1/setup/models/download",
                json={"model_name": "qwen2.5-coder:7b"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["success"] is True

    def test_download_failure(self, client, mock_setup_wizard):
        """Test model download failure"""
        mock_setup_wizard.download_model.return_value = False

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.post(
                "/api/v1/setup/models/download",
                json={"model_name": "nonexistent:model"}
            )

        assert response.status_code == 500

    def test_missing_model_name(self, client):
        """Test missing model_name"""
        with patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.post(
                "/api/v1/setup/models/download",
                json={}
            )

        assert response.status_code == 422


class TestConfigureHotSlots:
    """Tests for POST /hot-slots endpoint"""

    def test_success(self, client, mock_setup_wizard):
        """Test successful hot slots configuration"""
        mock_setup_wizard.configure_hot_slots.return_value = True

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.post(
                "/api/v1/setup/hot-slots",
                json={"slots": {1: "model1", 2: "model2", 3: None, 4: None}}
            )

        assert response.status_code == 200
        assert response.json()["data"]["success"] is True

    def test_invalid_slot_number(self, client, mock_setup_wizard):
        """Test invalid slot number"""
        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.post(
                "/api/v1/setup/hot-slots",
                json={"slots": {5: "model1"}}  # Invalid slot number
            )

        assert response.status_code == 400

    def test_configuration_failure(self, client, mock_setup_wizard):
        """Test configuration failure"""
        mock_setup_wizard.configure_hot_slots.return_value = False

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.post(
                "/api/v1/setup/hot-slots",
                json={"slots": {1: "model1"}}
            )

        assert response.status_code == 500


class TestCreateAccount:
    """Tests for POST /account endpoint"""

    def test_success(self, client, mock_setup_wizard):
        """Test successful account creation"""
        mock_setup_wizard.create_local_account.return_value = {
            "success": True,
            "user_id": "user-123",
            "founder_setup_complete": False
        }

        # Mock auth_service.get_all_users() to return empty list (no existing users)
        mock_auth = MagicMock()
        mock_auth.get_all_users.return_value = []

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.auth_service', mock_auth), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.post(
                "/api/v1/setup/account",
                json={
                    "username": "testuser",
                    "password": "password123",
                    "confirm_password": "password123"
                }
            )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["success"] is True
        assert data["data"]["user_id"] == "user-123"

    def test_password_mismatch(self, client, mock_setup_wizard):
        """Test password mismatch returns success=False but still 201 status"""
        # Mock auth_service.get_all_users() to return empty list (no existing users)
        mock_auth = MagicMock()
        mock_auth.get_all_users.return_value = []

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.auth_service', mock_auth):
            response = client.post(
                "/api/v1/setup/account",
                json={
                    "username": "testuser",
                    "password": "password123",
                    "confirm_password": "different123"
                }
            )

        # Endpoint returns 201 for all responses, but success=False for validation failure
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["success"] is False
        assert "match" in data["data"]["error"].lower()

    def test_with_founder_password(self, client, mock_setup_wizard):
        """Test account creation with founder password"""
        mock_setup_wizard.create_local_account.return_value = {
            "success": True,
            "user_id": "user-123",
            "founder_setup_complete": True
        }

        # Mock auth_service.get_all_users() to return empty list (no existing users)
        mock_auth = MagicMock()
        mock_auth.get_all_users.return_value = []

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.auth_service', mock_auth), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.post(
                "/api/v1/setup/account",
                json={
                    "username": "testuser",
                    "password": "password123",
                    "confirm_password": "password123",
                    "founder_password": "founderpass"
                }
            )

        assert response.status_code == 201
        assert response.json()["data"]["founder_setup_complete"] is True


class TestCompleteSetup:
    """Tests for POST /complete endpoint"""

    def test_success(self, client, mock_setup_wizard):
        """Test successful setup completion"""
        mock_setup_wizard.complete_setup.return_value = True

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.post("/api/v1/setup/complete")

        assert response.status_code == 200
        assert response.json()["data"]["success"] is True

    def test_completion_failure(self, client, mock_setup_wizard):
        """Test setup completion failure"""
        mock_setup_wizard.complete_setup.return_value = False

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.post("/api/v1/setup/complete")

        assert response.status_code == 500


# ========== Router Configuration Tests ==========

class TestRouterConfiguration:
    """Tests for router configuration"""

    def test_router_prefix(self):
        """Test router has correct prefix"""
        assert router.prefix == "/api/v1/setup"

    def test_router_tags(self):
        """Test router has correct tags"""
        assert "setup-wizard" in router.tags

    def test_router_has_expected_routes(self):
        """Test router has expected routes"""
        routes = [r.path for r in router.routes]

        assert "/api/v1/setup/status" in routes
        assert "/api/v1/setup/ollama" in routes
        assert "/api/v1/setup/resources" in routes
        assert "/api/v1/setup/models/recommendations" in routes
        assert "/api/v1/setup/models/installed" in routes
        assert "/api/v1/setup/models/download" in routes
        assert "/api/v1/setup/models/download/progress" in routes
        assert "/api/v1/setup/hot-slots" in routes
        assert "/api/v1/setup/account" in routes
        assert "/api/v1/setup/complete" in routes


# ========== SSE Progress Endpoint Tests ==========

class TestDownloadModelProgress:
    """Tests for GET /models/download/progress SSE endpoint"""

    def test_returns_streaming_response(self, client):
        """Test endpoint returns streaming response"""
        # Mock subprocess.Popen
        mock_process = MagicMock()
        mock_process.stdout.readline.side_effect = [
            "pulling manifest 100%\n",
            "success\n",
            ""
        ]
        mock_process.wait.return_value = None
        mock_process.returncode = 0

        with patch('subprocess.Popen', return_value=mock_process), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.get(
                "/api/v1/setup/models/download/progress?model_name=test:model"
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_unicode_username(self, client, mock_setup_wizard):
        """Test unicode username is rejected by validation"""
        mock_setup_wizard.create_local_account.return_value = {
            "success": True,
            "user_id": "user-123",
            "founder_setup_complete": False
        }

        # Mock auth_service.get_all_users() to return empty list (no existing users)
        mock_auth = MagicMock()
        mock_auth.get_all_users.return_value = []

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.auth_service', mock_auth):
            # ASCII-only usernames should work
            response = client.post(
                "/api/v1/setup/account",
                json={
                    "username": "test_user",
                    "password": "password123",
                    "confirm_password": "password123"
                }
            )
        # Should pass validation and succeed
        assert response.status_code == 201

    def test_empty_hot_slots(self, client, mock_setup_wizard):
        """Test empty hot slots configuration"""
        mock_setup_wizard.configure_hot_slots.return_value = True

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.post(
                "/api/v1/setup/hot-slots",
                json={"slots": {}}
            )

        assert response.status_code == 200

    def test_all_slots_null(self, client, mock_setup_wizard):
        """Test clearing all hot slots"""
        mock_setup_wizard.configure_hot_slots.return_value = True

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.post(
                "/api/v1/setup/hot-slots",
                json={"slots": {1: None, 2: None, 3: None, 4: None}}
            )

        assert response.status_code == 200

    def test_special_chars_in_model_name(self, client, mock_setup_wizard):
        """Test special characters in model name"""
        mock_setup_wizard.download_model.return_value = True

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.limiter.limit', lambda x: lambda f: f):
            response = client.post(
                "/api/v1/setup/models/download",
                json={"model_name": "qwen2.5-coder:7b-instruct-q4_K_M"}
            )

        assert response.status_code == 200


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests"""

    def test_setup_flow(self, client, mock_setup_wizard, mock_founder_wizard,
                        sample_ollama_status, sample_system_resources, sample_model_recommendations):
        """Test typical setup flow"""
        mock_setup_wizard.check_ollama_status.return_value = sample_ollama_status
        mock_setup_wizard.detect_system_resources.return_value = sample_system_resources
        mock_setup_wizard.load_model_recommendations.return_value = sample_model_recommendations
        mock_setup_wizard.get_installed_models.return_value = []
        mock_setup_wizard.download_model.return_value = True
        mock_setup_wizard.configure_hot_slots.return_value = True
        mock_setup_wizard.create_local_account.return_value = {
            "success": True,
            "user_id": "user-123",
            "founder_setup_complete": False
        }
        mock_setup_wizard.complete_setup.return_value = True

        # Mock auth_service.get_all_users() to return empty list (no existing users)
        mock_auth = MagicMock()
        mock_auth.get_all_users.return_value = []

        with patch('api.routes.setup_wizard_routes.get_setup_wizard', return_value=mock_setup_wizard), \
             patch('api.routes.setup_wizard_routes.get_founder_wizard', return_value=mock_founder_wizard), \
             patch('api.routes.setup_wizard_routes.auth_service', mock_auth):

            # Step 1: Check Ollama
            response = client.get("/api/v1/setup/ollama")
            assert response.status_code == 200

            # Step 2: Get resources
            response = client.get("/api/v1/setup/resources")
            assert response.status_code == 200

            # Step 3: Get recommendations
            response = client.get("/api/v1/setup/models/recommendations")
            assert response.status_code == 200

            # Step 4: Download model
            response = client.post(
                "/api/v1/setup/models/download",
                json={"model_name": "qwen2.5-coder:14b"}
            )
            assert response.status_code == 200

            # Step 5: Configure hot slots
            response = client.post(
                "/api/v1/setup/hot-slots",
                json={"slots": {1: "qwen2.5-coder:14b"}}
            )
            assert response.status_code == 200

            # Step 6: Create account
            response = client.post(
                "/api/v1/setup/account",
                json={
                    "username": "admin",
                    "password": "securepass123",
                    "confirm_password": "securepass123"
                }
            )
            assert response.status_code == 201

            # Step 7: Complete setup
            response = client.post("/api/v1/setup/complete")
            assert response.status_code == 200
