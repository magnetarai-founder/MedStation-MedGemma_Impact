"""
Comprehensive tests for api/config.py

Tests unified configuration management using Pydantic BaseSettings.

Coverage targets:
- ElohimOSSettings class initialization and defaults
- Field validators (data_dir)
- Model validator (jwt_secret validation)
- Computed properties (paths, system info)
- Helper methods (get_ollama_generation_options, get_rate_limit, detect_optimal_ollama_settings)
- Singleton pattern via get_settings()
- Helper functions (is_airgap_mode, is_offline_mode)
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from api.config import (
    ElohimOSSettings,
    get_settings,
    is_airgap_mode,
    is_offline_mode,
    PATHS,
)


# ========== Fixtures ==========

@pytest.fixture
def reset_singleton():
    """Reset the get_settings singleton between tests"""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def clean_env():
    """Clean environment of config-related env vars"""
    vars_to_clear = [
        "ELOHIMOS_JWT_SECRET_KEY",
        "ELOHIMOS_ENVIRONMENT",
        "ELOHIMOS_DEBUG",
        "ELOHIMOS_AIRGAP_MODE",
        "ELOHIMOS_OFFLINE_MODE",
        "MAGNETAR_AIRGAP_MODE",
        "ELOHIM_OFFLINE_MODE",
        "ELOHIM_JWT_SECRET",
    ]
    old_values = {}
    for var in vars_to_clear:
        old_values[var] = os.environ.pop(var, None)

    yield

    # Restore old values
    for var, val in old_values.items():
        if val is not None:
            os.environ[var] = val
        else:
            os.environ.pop(var, None)


# ========== ElohimOSSettings Initialization Tests ==========

class TestSettingsInit:
    """Tests for ElohimOSSettings initialization"""

    def test_default_environment(self, reset_singleton, clean_env, temp_data_dir):
        """Test default environment is development"""
        with patch.dict(os.environ, {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}, clear=False):
            settings = ElohimOSSettings()

        assert settings.environment == "development"

    def test_default_debug(self, reset_singleton, clean_env, temp_data_dir):
        """Test default debug is True"""
        with patch.dict(os.environ, {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}, clear=False):
            settings = ElohimOSSettings()

        assert settings.debug is True

    def test_default_log_level(self, reset_singleton, clean_env, temp_data_dir):
        """Test default log level is INFO"""
        with patch.dict(os.environ, {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}, clear=False):
            settings = ElohimOSSettings()

        assert settings.log_level == "INFO"

    def test_default_api_settings(self, reset_singleton, clean_env, temp_data_dir):
        """Test default API server settings"""
        with patch.dict(os.environ, {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}, clear=False):
            settings = ElohimOSSettings()

        assert settings.api_host == "localhost"
        assert settings.api_port == 8000
        assert settings.api_workers == 1

    def test_default_cors_origins(self, reset_singleton, clean_env, temp_data_dir):
        """Test default CORS origins"""
        with patch.dict(os.environ, {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}, clear=False):
            settings = ElohimOSSettings()

        assert "http://localhost:4200" in settings.cors_origins
        assert "http://127.0.0.1:4200" in settings.cors_origins

    def test_default_jwt_algorithm(self, reset_singleton, clean_env, temp_data_dir):
        """Test default JWT algorithm"""
        with patch.dict(os.environ, {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}, clear=False):
            settings = ElohimOSSettings()

        assert settings.jwt_algorithm == "HS256"

    def test_default_jwt_expire_minutes(self, reset_singleton, clean_env, temp_data_dir):
        """Test default JWT expiration"""
        with patch.dict(os.environ, {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}, clear=False):
            settings = ElohimOSSettings()

        assert settings.jwt_access_token_expire_minutes == 60

    def test_default_ollama_settings(self, reset_singleton, clean_env, temp_data_dir):
        """Test default Ollama settings"""
        with patch.dict(os.environ, {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}, clear=False):
            settings = ElohimOSSettings()

        assert settings.ollama_base_url == "http://localhost:11434"
        assert settings.ollama_timeout == 300
        assert settings.ollama_num_gpu_layers == 100
        assert settings.ollama_num_ctx == 200000

    def test_default_p2p_settings(self, reset_singleton, clean_env, temp_data_dir):
        """Test default P2P settings"""
        with patch.dict(os.environ, {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}, clear=False):
            settings = ElohimOSSettings()

        assert settings.p2p_enabled is False
        assert settings.p2p_port == 9000

    def test_default_airgap_mode(self, reset_singleton, clean_env, temp_data_dir):
        """Test default airgap mode is disabled"""
        with patch.dict(os.environ, {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}, clear=False):
            settings = ElohimOSSettings()

        assert settings.airgap_mode is False
        assert settings.offline_mode is False


# ========== Environment Variable Override Tests ==========

class TestEnvOverrides:
    """Tests for environment variable overrides"""

    def test_env_prefix_elohimos(self, reset_singleton, clean_env, temp_data_dir):
        """Test ELOHIMOS_ prefix works"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_DEBUG": "false",
            "ELOHIMOS_LOG_LEVEL": "DEBUG",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.debug is False
        assert settings.log_level == "DEBUG"

    def test_env_override_api_port(self, reset_singleton, clean_env, temp_data_dir):
        """Test API port override"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_API_PORT": "9000",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.api_port == 9000

    def test_env_override_jwt_secret(self, reset_singleton, clean_env, temp_data_dir):
        """Test JWT secret key override"""
        secret = "a" * 32  # 32 char secret
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_JWT_SECRET_KEY": secret,
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.jwt_secret_key == secret

    def test_env_override_environment(self, reset_singleton, clean_env, temp_data_dir):
        """Test environment override"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_ENVIRONMENT": "testing",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.environment == "testing"

    def test_env_override_ollama_url(self, reset_singleton, clean_env, temp_data_dir):
        """Test Ollama URL override"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_OLLAMA_BASE_URL": "http://192.168.1.100:11434",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.ollama_base_url == "http://192.168.1.100:11434"

    def test_case_insensitive_env_vars(self, reset_singleton, clean_env, temp_data_dir):
        """Test env vars are case insensitive"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "elohimos_debug": "false",  # lowercase
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.debug is False


# ========== JWT Validator Tests ==========

class TestJWTValidator:
    """Tests for JWT secret validation"""

    def test_auto_generate_secret_in_dev(self, reset_singleton, clean_env, temp_data_dir):
        """Test auto-generates JWT secret in development mode"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_ENVIRONMENT": "development",
        }
        with patch.dict(os.environ, env, clear=False):
            import warnings
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                settings = ElohimOSSettings()

                # Should have auto-generated a secret
                assert len(settings.jwt_secret_key) >= 32
                # Should have warned
                assert any("JWT_SECRET_KEY not set" in str(warning.message) for warning in w)

    def test_empty_secret_auto_generates_in_dev(self, reset_singleton, clean_env, temp_data_dir):
        """Test empty secret triggers auto-generation in dev"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_JWT_SECRET_KEY": "",
            "ELOHIMOS_ENVIRONMENT": "development",
        }
        with patch.dict(os.environ, env, clear=False):
            import warnings
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                settings = ElohimOSSettings()

                assert len(settings.jwt_secret_key) >= 32

    def test_insecure_defaults_auto_generates(self, reset_singleton, clean_env, temp_data_dir):
        """Test insecure default secrets are auto-regenerated"""
        insecure_secrets = ["secret", "changeme", "CHANGE_ME_IN_PRODUCTION_12345678901234567890"]

        for secret in insecure_secrets:
            env = {
                "ELOHIMOS_DATA_DIR": str(temp_data_dir),
                "ELOHIMOS_JWT_SECRET_KEY": secret,
                "ELOHIMOS_ENVIRONMENT": "development",
            }
            with patch.dict(os.environ, env, clear=False):
                import warnings
                with warnings.catch_warnings(record=True):
                    warnings.simplefilter("always")
                    settings = ElohimOSSettings()

                    # Should have auto-generated a new secret
                    assert settings.jwt_secret_key != secret
                    assert len(settings.jwt_secret_key) >= 32

    def test_production_requires_jwt_secret(self, reset_singleton, clean_env, temp_data_dir):
        """Test production mode requires JWT secret"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_ENVIRONMENT": "production",
            "ELOHIMOS_JWT_SECRET_KEY": "",
        }
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(ValueError, match="JWT_SECRET_KEY must be set in production"):
                ElohimOSSettings()

    def test_production_requires_long_secret(self, reset_singleton, clean_env, temp_data_dir):
        """Test production mode requires secret >= 32 chars"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_ENVIRONMENT": "production",
            "ELOHIMOS_JWT_SECRET_KEY": "short_secret",  # < 32 chars
        }
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(ValueError, match="JWT_SECRET_KEY is too short"):
                ElohimOSSettings()

    def test_production_with_valid_secret(self, reset_singleton, clean_env, temp_data_dir):
        """Test production mode works with valid secret"""
        valid_secret = "a" * 32  # 32 chars
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_ENVIRONMENT": "production",
            "ELOHIMOS_JWT_SECRET_KEY": valid_secret,
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.jwt_secret_key == valid_secret


# ========== Data Dir Validator Tests ==========

class TestDataDirValidator:
    """Tests for data directory validator"""

    def test_creates_data_dir_if_not_exists(self, reset_singleton, clean_env):
        """Test data directory is created if it doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_data_dir = Path(tmpdir) / "new_data_dir"
            assert not new_data_dir.exists()

            env = {"ELOHIMOS_DATA_DIR": str(new_data_dir)}
            with patch.dict(os.environ, env, clear=False):
                settings = ElohimOSSettings()

            assert new_data_dir.exists()
            assert new_data_dir.is_dir()

    def test_creates_nested_data_dir(self, reset_singleton, clean_env):
        """Test creates nested directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "level1" / "level2" / "data"
            assert not nested_dir.exists()

            env = {"ELOHIMOS_DATA_DIR": str(nested_dir)}
            with patch.dict(os.environ, env, clear=False):
                settings = ElohimOSSettings()

            assert nested_dir.exists()

    def test_uses_existing_data_dir(self, reset_singleton, clean_env, temp_data_dir):
        """Test uses existing directory without error"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.data_dir == temp_data_dir


# ========== Computed Properties Tests ==========

class TestComputedProperties:
    """Tests for computed properties"""

    def test_app_db_path(self, reset_singleton, clean_env, temp_data_dir):
        """Test app_db computed property"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.app_db == temp_data_dir / "elohimos_app.db"

    def test_vault_db_path(self, reset_singleton, clean_env, temp_data_dir):
        """Test vault_db computed property"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.vault_db == temp_data_dir / "vault.db"

    def test_datasets_db_path(self, reset_singleton, clean_env, temp_data_dir):
        """Test datasets_db computed property"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.datasets_db == temp_data_dir / "datasets" / "datasets.db"

    def test_memory_db_path(self, reset_singleton, clean_env, temp_data_dir):
        """Test memory_db computed property"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.memory_db == temp_data_dir / "memory" / "chat_memory.db"

    def test_uploads_dir_creates_directory(self, reset_singleton, clean_env, temp_data_dir):
        """Test uploads_dir creates directory"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        uploads = settings.uploads_dir
        assert uploads.exists()
        assert uploads.is_dir()
        assert uploads == temp_data_dir / "uploads"

    def test_cache_dir_creates_directory(self, reset_singleton, clean_env, temp_data_dir):
        """Test cache_dir creates directory"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        cache = settings.cache_dir
        assert cache.exists()
        assert cache.is_dir()
        assert cache == temp_data_dir / "cache"

    def test_shared_files_dir_creates_directory(self, reset_singleton, clean_env, temp_data_dir):
        """Test shared_files_dir creates directory"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        shared = settings.shared_files_dir
        assert shared.exists()
        assert shared.is_dir()
        assert shared == temp_data_dir / "shared_files"

    def test_model_hot_slots_file_path(self, reset_singleton, clean_env, temp_data_dir):
        """Test model_hot_slots_file computed property"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.model_hot_slots_file == temp_data_dir / "model_hot_slots.json"

    def test_is_apple_silicon_property(self, reset_singleton, clean_env, temp_data_dir):
        """Test is_apple_silicon property"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        # Just verify it returns a boolean
        assert isinstance(settings.is_apple_silicon, bool)

    def test_total_ram_gb_property(self, reset_singleton, clean_env, temp_data_dir):
        """Test total_ram_gb property"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        # Should return positive float
        assert isinstance(settings.total_ram_gb, float)
        assert settings.total_ram_gb > 0

    def test_cpu_cores_property(self, reset_singleton, clean_env, temp_data_dir):
        """Test cpu_cores property"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        # Should return positive integer
        assert isinstance(settings.cpu_cores, int)
        assert settings.cpu_cores >= 1


# ========== Helper Methods Tests ==========

class TestHelperMethods:
    """Tests for helper methods"""

    def test_get_ollama_generation_options_defaults(self, reset_singleton, clean_env, temp_data_dir):
        """Test get_ollama_generation_options with defaults"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        options = settings.get_ollama_generation_options()

        assert "num_ctx" in options
        assert "num_gpu" in options
        assert "num_thread" in options
        assert options["num_ctx"] == settings.ollama_num_ctx

    def test_get_ollama_generation_options_with_overrides(self, reset_singleton, clean_env, temp_data_dir):
        """Test get_ollama_generation_options with overrides"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        options = settings.get_ollama_generation_options(num_ctx=8192, temperature=0.7)

        assert options["num_ctx"] == 8192  # Overridden
        assert options["temperature"] == 0.7  # Added
        assert options["num_gpu"] == settings.ollama_num_gpu_layers  # Default

    def test_get_rate_limit_global(self, reset_singleton, clean_env, temp_data_dir):
        """Test get_rate_limit for global"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.get_rate_limit("global") == "100/minute"

    def test_get_rate_limit_auth(self, reset_singleton, clean_env, temp_data_dir):
        """Test get_rate_limit for auth"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.get_rate_limit("auth") == "5/minute"

    def test_get_rate_limit_chat(self, reset_singleton, clean_env, temp_data_dir):
        """Test get_rate_limit for chat"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.get_rate_limit("chat") == "20/minute"

    def test_get_rate_limit_unknown_defaults_to_global(self, reset_singleton, clean_env, temp_data_dir):
        """Test get_rate_limit for unknown type defaults to global"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.get_rate_limit("unknown") == "100/minute"

    def test_get_rate_limit_dev_mode_multiplier(self, reset_singleton, clean_env, temp_data_dir):
        """Test get_rate_limit applies dev mode multiplier"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_DEV_MODE": "true",
            "ELOHIMOS_DEV_RATE_LIMIT_MULTIPLIER": "5",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        # 100/minute * 5 = 500/minute
        assert settings.get_rate_limit("global") == "500/minute"

    def test_detect_optimal_ollama_settings(self, reset_singleton, clean_env, temp_data_dir):
        """Test detect_optimal_ollama_settings returns dict"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        result = settings.detect_optimal_ollama_settings()

        assert isinstance(result, dict)
        # Should have some settings
        assert len(result) > 0

    def test_detect_optimal_ollama_settings_apple_silicon(self, reset_singleton, clean_env, temp_data_dir):
        """Test detect_optimal_ollama_settings for Apple Silicon"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        # Mock platform.processor and psutil for Apple Silicon with 64GB
        mock_mem = MagicMock()
        mock_mem.total = 64 * (1024 ** 3)  # 64GB in bytes

        with patch('platform.processor', return_value='arm'), \
             patch('platform.system', return_value='Darwin'), \
             patch('psutil.virtual_memory', return_value=mock_mem), \
             patch('psutil.cpu_count', return_value=10):

            result = settings.detect_optimal_ollama_settings()

            assert result["num_gpu_layers"] == 100
            assert result["use_mmap"] is True
            assert result["use_mlock"] is True  # >= 64GB RAM
            assert result["num_ctx"] == 200000  # >= 64GB RAM

    def test_detect_optimal_ollama_settings_32gb_ram(self, reset_singleton, clean_env, temp_data_dir):
        """Test detect_optimal_ollama_settings for 32GB RAM"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        # Mock Apple Silicon with 32GB
        mock_mem = MagicMock()
        mock_mem.total = 32 * (1024 ** 3)  # 32GB in bytes

        with patch('platform.processor', return_value='arm'), \
             patch('platform.system', return_value='Darwin'), \
             patch('psutil.virtual_memory', return_value=mock_mem), \
             patch('psutil.cpu_count', return_value=8):

            result = settings.detect_optimal_ollama_settings()

            assert result["num_ctx"] == 128000  # 32GB RAM

    def test_detect_optimal_ollama_settings_low_ram(self, reset_singleton, clean_env, temp_data_dir):
        """Test detect_optimal_ollama_settings for low RAM"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        # Mock Apple Silicon with 16GB
        mock_mem = MagicMock()
        mock_mem.total = 16 * (1024 ** 3)  # 16GB in bytes

        with patch('platform.processor', return_value='arm'), \
             patch('platform.system', return_value='Darwin'), \
             patch('psutil.virtual_memory', return_value=mock_mem), \
             patch('psutil.cpu_count', return_value=8):

            result = settings.detect_optimal_ollama_settings()

            assert result["num_ctx"] == 32000  # < 32GB RAM

    def test_detect_optimal_ollama_settings_non_apple(self, reset_singleton, clean_env, temp_data_dir):
        """Test detect_optimal_ollama_settings for non-Apple Silicon"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        # Mock non-Apple Silicon (x86)
        with patch('platform.processor', return_value='x86_64'), \
             patch('platform.system', return_value='Linux'):

            result = settings.detect_optimal_ollama_settings()

            assert result["num_gpu_layers"] == 50
            assert result["num_ctx"] == 8192
            assert result["batch_size"] == 256

    def test_to_dict(self, reset_singleton, clean_env, temp_data_dir):
        """Test to_dict method"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        result = settings.to_dict()

        assert isinstance(result, dict)
        assert "environment" in result
        assert "debug" in result
        assert "api_host" in result
        assert "ollama_base_url" in result


# ========== Singleton Tests ==========

class TestSingleton:
    """Tests for singleton pattern"""

    def test_get_settings_returns_instance(self, reset_singleton, clean_env, temp_data_dir):
        """Test get_settings returns ElohimOSSettings instance"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            result = get_settings()

        assert isinstance(result, ElohimOSSettings)

    def test_get_settings_returns_same_instance(self, reset_singleton, clean_env, temp_data_dir):
        """Test get_settings returns same instance on multiple calls"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings1 = get_settings()
            settings2 = get_settings()

        assert settings1 is settings2

    def test_paths_alias_is_settings(self, reset_singleton, clean_env, temp_data_dir):
        """Test PATHS is an alias for settings"""
        # PATHS is a module-level variable
        assert isinstance(PATHS, ElohimOSSettings)


# ========== Air-Gap Mode Tests ==========

class TestAirgapMode:
    """Tests for is_airgap_mode function"""

    def test_airgap_disabled_by_default(self, reset_singleton, clean_env, temp_data_dir):
        """Test airgap mode is disabled by default"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            result = is_airgap_mode()

        assert result is False

    def test_airgap_enabled_via_elohimos(self, reset_singleton, clean_env, temp_data_dir):
        """Test airgap mode enabled via ELOHIMOS_AIRGAP_MODE"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_AIRGAP_MODE": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            result = is_airgap_mode()

        assert result is True

    def test_airgap_enabled_via_magnetar(self, reset_singleton, clean_env, temp_data_dir):
        """Test airgap mode enabled via legacy MAGNETAR_AIRGAP_MODE"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "MAGNETAR_AIRGAP_MODE": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            result = is_airgap_mode()

        assert result is True

    def test_airgap_enabled_via_elohim_offline(self, reset_singleton, clean_env, temp_data_dir):
        """Test airgap mode enabled via legacy ELOHIM_OFFLINE_MODE"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIM_OFFLINE_MODE": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            result = is_airgap_mode()

        assert result is True

    def test_airgap_truthy_values(self, reset_singleton, clean_env, temp_data_dir):
        """Test various truthy values for airgap mode"""
        truthy_values = ["true", "1", "yes", "on", "TRUE", "Yes", "ON"]

        for value in truthy_values:
            env = {
                "ELOHIMOS_DATA_DIR": str(temp_data_dir),
                "MAGNETAR_AIRGAP_MODE": value,
            }
            with patch.dict(os.environ, env, clear=False):
                get_settings.cache_clear()
                result = is_airgap_mode()

            assert result is True, f"Expected True for value '{value}'"


# ========== Offline Mode Tests ==========

class TestOfflineMode:
    """Tests for is_offline_mode function"""

    def test_offline_disabled_by_default(self, reset_singleton, clean_env, temp_data_dir):
        """Test offline mode is disabled by default"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            result = is_offline_mode()

        assert result is False

    def test_offline_enabled_via_elohimos(self, reset_singleton, clean_env, temp_data_dir):
        """Test offline mode enabled via ELOHIMOS_OFFLINE_MODE"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_OFFLINE_MODE": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            result = is_offline_mode()

        assert result is True

    def test_offline_enabled_via_elohim(self, reset_singleton, clean_env, temp_data_dir):
        """Test offline mode enabled via legacy ELOHIM_OFFLINE_MODE"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIM_OFFLINE_MODE": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            result = is_offline_mode()

        assert result is True

    def test_offline_implied_by_airgap(self, reset_singleton, clean_env, temp_data_dir):
        """Test offline mode is True when airgap is enabled"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_AIRGAP_MODE": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            result = is_offline_mode()

        assert result is True


# ========== Edge Cases ==========

class TestEdgeCases:
    """Tests for edge cases"""

    def test_empty_cors_origins_list(self, reset_singleton, clean_env, temp_data_dir):
        """Test handling of empty CORS origins"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_CORS_ORIGINS": "[]",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        # Should accept empty list
        assert isinstance(settings.cors_origins, list)

    def test_unicode_in_data_dir(self, reset_singleton, clean_env):
        """Test unicode characters in data directory path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            unicode_dir = Path(tmpdir) / "данные_数据"
            env = {"ELOHIMOS_DATA_DIR": str(unicode_dir)}
            with patch.dict(os.environ, env, clear=False):
                settings = ElohimOSSettings()

            assert unicode_dir.exists()
            assert settings.data_dir == unicode_dir

    def test_very_long_jwt_secret(self, reset_singleton, clean_env, temp_data_dir):
        """Test handling very long JWT secret"""
        long_secret = "x" * 1000
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_JWT_SECRET_KEY": long_secret,
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.jwt_secret_key == long_secret

    def test_numeric_string_conversion(self, reset_singleton, clean_env, temp_data_dir):
        """Test numeric string conversion for integer fields"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_API_PORT": "12345",
            "ELOHIMOS_DB_TIMEOUT": "999",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.api_port == 12345
        assert settings.db_timeout == 999

    def test_boolean_string_conversion(self, reset_singleton, clean_env, temp_data_dir):
        """Test boolean string conversion"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_DEBUG": "false",
            "ELOHIMOS_P2P_ENABLED": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.debug is False
        assert settings.p2p_enabled is True


# ========== Integration Tests ==========

class TestIntegration:
    """Integration tests"""

    def test_full_settings_workflow(self, reset_singleton, clean_env, temp_data_dir):
        """Test full settings workflow"""
        jwt_secret = "integration_test_secret_" + "x" * 20
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_JWT_SECRET_KEY": jwt_secret,
            "ELOHIMOS_ENVIRONMENT": "testing",
            "ELOHIMOS_DEBUG": "false",
            "ELOHIMOS_API_PORT": "9000",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = get_settings()

        # Check all values
        assert settings.environment == "testing"
        assert settings.debug is False
        assert settings.api_port == 9000
        assert settings.jwt_secret_key == jwt_secret
        assert settings.data_dir == temp_data_dir

        # Check computed properties work
        assert settings.app_db.exists() is False  # Not created yet
        assert settings.uploads_dir.exists()  # Created on access

        # Check helper methods work
        options = settings.get_ollama_generation_options()
        assert "num_ctx" in options

        rate_limit = settings.get_rate_limit("auth")
        assert "/" in rate_limit

    def test_settings_singleton_consistency(self, reset_singleton, clean_env, temp_data_dir):
        """Test that singleton returns consistent settings"""
        env = {"ELOHIMOS_DATA_DIR": str(temp_data_dir)}
        with patch.dict(os.environ, env, clear=False):
            settings1 = get_settings()
            original_debug = settings1.debug

            settings2 = get_settings()

        # Both should have same value
        assert settings1.debug == settings2.debug
        assert settings1.debug == original_debug

    def test_cloud_storage_settings(self, reset_singleton, clean_env, temp_data_dir):
        """Test cloud storage settings"""
        env = {
            "ELOHIMOS_DATA_DIR": str(temp_data_dir),
            "ELOHIMOS_CLOUD_STORAGE_ENABLED": "true",
            "ELOHIMOS_CLOUD_STORAGE_PROVIDER": "s3",
            "ELOHIMOS_S3_BUCKET_NAME": "my-bucket",
            "ELOHIMOS_S3_REGION": "us-west-2",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElohimOSSettings()

        assert settings.cloud_storage_enabled is True
        assert settings.cloud_storage_provider == "s3"
        assert settings.s3_bucket_name == "my-bucket"
        assert settings.s3_region == "us-west-2"
