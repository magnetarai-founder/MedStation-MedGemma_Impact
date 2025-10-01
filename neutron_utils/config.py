"""
Centralized configuration management
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
import json
import logging

logger = logging.getLogger(__name__)


class Config:
    """Centralized configuration for the Data Tool"""

    # Default configuration values
    DEFAULTS = {
        # File operations
        "max_file_size_mb": 1000,
        "chunk_size": 10000,
        "excel_chunk_size": 5000,
        "excel_stream_to_csv_threshold_mb": 100,  # If Excel fallback and file > this, stream to CSV
        "csv_encoding": "utf-8",
        # Excel options
        "excel_sheet_name": None,
        # Database operations
        "db_timeout": 300,
        "db_retry_count": 3,
        "db_retry_delay": 5,
        "batch_size": 1000,
        # Import behavior
        "prefer_duckdb_excel": False,  # Use DuckDB excel extension first (may infer/cast types)
        "prefer_pandas_csv": True,     # Use pandas CSV reader first for robustness
        "csv_chunk_size": 100000,      # For future streaming improvements
        "csv_stream_to_duckdb_threshold_mb": 200,
        # GUI settings
        "preview_rows": 100,
        "max_preview_columns": 50,
        "thread_pool_size": 4,
        "progress_update_interval": 100,
        # Performance settings
        "enable_parallel_processing": True,
        "max_workers": None,  # None means use CPU count
        "memory_limit_mb": 4096,
        # Logging
        "log_level": "INFO",
        "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "log_file": "data_tool.log",
        # Data processing
        "string_dtype_threshold": 0.5,  # Threshold for converting to category
        "decimal_places": 2,
        "date_format": "%Y-%m-%d",
        "datetime_format": "%Y-%m-%d %H:%M:%S",
        # Type strictness (optional hardening)
        "strict_types": False,  # Enforce consistent dtypes by content ratio
        "strict_type_numeric_ratio": 0.5,  # If >= 50% numeric-looking, coerce to numeric
        # Nudge: columns matching these patterns may cast with a lower threshold
        "prefer_numeric_patterns": [
            "sales", "revenue", "amount", "amt", "qty", "quantity",
            "price", "cost", "total", "count", "number", "num",
            "weight", "volume", "score", "rating"
        ],
        # Strict types controls (also used by auto-type inference to avoid miscasting IDs)
        "strict_types_exclude": [],
        "strict_types_exclude_patterns": [
            "sku", "barcode", "code", "wdcode", "plu", "upc", "ean", "id"
        ],
        # Mode: keep everything as strings to maximize SQL compatibility
        "string_safe_mode": True,
        # Auto type inference on load (make numeric columns numeric)
        # Disabled by default when string_safe_mode is True
        "auto_type_infer_on_load": False,
        # How many rows to sample when inferring types (0 = use all rows)
        "type_infer_sample_rows": 50000,
        # Query-time helpers
        "cast_trim_args": False,                 # Cast TRIM/LTRIM/RTRIM args to VARCHAR automatically
        "auto_cast_numeric_aggregates": True,    # Cast SUM/AVG args to DOUBLE (tolerant of $/,/spaces)
        # Regex patterns (moved from hardcoded values)
        "sql_timeout": 600,
        "sql_fetch_size": 10000,
        # Enrichment / network
        "enrichment_network_enabled": False,
        "enrichment_timeout_seconds": 5,
        "enrichment_retry_count": 1,
    }

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration

        Args:
            config_file: Path to configuration file
        """
        self._config = self.DEFAULTS.copy()

        # Load from environment variables
        self._load_from_env()

        # Load from file if provided
        if config_file:
            self._load_from_file(config_file)
        else:
            # Convenience: auto-load shared_config.yaml if present
            # This enables access to PRODUCE_TERMS and other shared lists
            try:
                default_shared = Path("shared_config.yaml")
                if default_shared.exists():
                    self._load_from_file(str(default_shared))
            except Exception:
                # Non-fatal if not present or unreadable
                pass

    def _load_from_env(self) -> None:
        """Load configuration from environment variables"""
        env_prefix = "DATA_TOOL_"

        for key in self.DEFAULTS:
            env_key = f"{env_prefix}{key.upper()}"
            if env_key in os.environ:
                value = os.environ[env_key]

                # Convert to appropriate type
                if isinstance(self.DEFAULTS[key], bool):
                    value = value.lower() in ("true", "1", "yes")
                elif isinstance(self.DEFAULTS[key], int):
                    value = int(value)
                elif isinstance(self.DEFAULTS[key], float):
                    value = float(value)

                self._config[key] = value

    def _load_from_file(self, config_file: str) -> None:
        """Load configuration from file"""
        path = Path(config_file)

        if not path.exists():
            logger.warning(f"Config file not found: {config_file}")
            return

        try:
            if path.suffix == ".yaml" or path.suffix == ".yml":
                with open(path, "r") as f:
                    file_config = yaml.safe_load(f)
            elif path.suffix == ".json":
                with open(path, "r") as f:
                    file_config = json.load(f)
            else:
                logger.error(f"Unsupported config file format: {path.suffix}")
                return

            # Update config with file values
            if file_config:
                self._config.update(file_config)

        except Exception as e:
            logger.error(f"Error loading config file: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value

        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config[key] = value

    def update(self, config_dict: Dict[str, Any]) -> None:
        """
        Update multiple configuration values

        Args:
            config_dict: Dictionary of configuration values
        """
        self._config.update(config_dict)

    def to_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return self._config.copy()

    def save_to_file(self, file_path: str, format: str = "yaml") -> None:
        """
        Save configuration to file

        Args:
            file_path: Output file path
            format: Output format ('yaml' or 'json')
        """
        try:
            with open(file_path, "w") as f:
                if format == "yaml":
                    yaml.dump(self._config, f, default_flow_style=False)
                elif format == "json":
                    json.dump(self._config, f, indent=2)
                else:
                    raise ValueError(f"Unsupported format: {format}")

            logger.info(f"Configuration saved to {file_path}")

        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise


# Global configuration instance
config = Config()


def bootstrap_logging() -> None:
    """Initialize root logging once using Config defaults.

    Safe to call multiple times; subsequent calls are no-ops if the root
    logger already has handlers.
    """
    root = logging.getLogger()
    if root.handlers:
        return
    try:
        level_name = str(config.get("log_level", "INFO")).upper()
        level = getattr(logging, level_name, logging.INFO)
        logging.basicConfig(level=level, format=config.get("log_format", "%(asctime)s %(levelname)s %(message)s"))
    except Exception:
        logging.basicConfig(level=logging.INFO)


class ConfigManager:
    """Manager for different configuration profiles"""

    def __init__(self, base_config_dir: str = "."):
        """
        Initialize configuration manager

        Args:
            base_config_dir: Base directory for configuration files
        """
        self.base_dir = Path(base_config_dir)
        self.profiles: Dict[str, Config] = {}
        self.active_profile = "default"

        # Load default profile
        self.profiles["default"] = Config()

    def load_profile(self, profile_name: str, config_file: str) -> None:
        """
        Load a configuration profile

        Args:
            profile_name: Name of the profile
            config_file: Path to configuration file
        """
        self.profiles[profile_name] = Config(config_file)

    def set_active_profile(self, profile_name: str) -> None:
        """
        Set the active configuration profile

        Args:
            profile_name: Name of the profile to activate
        """
        if profile_name not in self.profiles:
            raise ValueError(f"Profile '{profile_name}' not found")

        self.active_profile = profile_name

    def get_config(self, profile_name: Optional[str] = None) -> Config:
        """
        Get configuration for a profile

        Args:
            profile_name: Name of the profile (uses active if None)

        Returns:
            Configuration object
        """
        if profile_name is None:
            profile_name = self.active_profile

        return self.profiles.get(profile_name, self.profiles["default"])
