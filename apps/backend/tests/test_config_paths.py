"""
Tests for Config Paths

Tests the configuration path utilities used throughout the application.
"""

import pytest
from pathlib import Path

from api.config_paths import get_config_paths


class TestConfigPaths:
    """Tests for config paths"""

    def test_get_config_paths_returns_data_dir(self):
        """Test get_config_paths returns object with data_dir"""
        paths = get_config_paths()

        assert hasattr(paths, 'data_dir')
        assert isinstance(paths.data_dir, Path)

    def test_data_dir_is_absolute(self):
        """Test data_dir is an absolute path"""
        paths = get_config_paths()

        assert paths.data_dir.is_absolute()

    def test_data_dir_contains_neutron(self):
        """Test data_dir path contains expected component"""
        paths = get_config_paths()

        # Should contain .neutron_data or similar
        assert "neutron" in str(paths.data_dir).lower() or "data" in str(paths.data_dir).lower()

    def test_get_config_paths_returns_consistent_results(self):
        """Test get_config_paths returns consistent paths"""
        paths1 = get_config_paths()
        paths2 = get_config_paths()

        assert paths1.data_dir == paths2.data_dir

    def test_data_dir_exists_or_can_be_created(self):
        """Test data directory can be accessed"""
        paths = get_config_paths()

        paths.data_dir.mkdir(parents=True, exist_ok=True)
        assert paths.data_dir.exists()
