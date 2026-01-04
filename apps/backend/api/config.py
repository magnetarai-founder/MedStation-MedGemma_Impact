"""
Unified Configuration Management for ElohimOS

Consolidates all configuration into a single source of truth using Pydantic BaseSettings.
All settings can be overridden via environment variables with ELOHIMOS_ prefix.

Usage:
    from config import get_settings

    settings = get_settings()
    print(settings.jwt_secret_key)
    print(settings.ollama_base_url)
"""

import os
import platform
import secrets
from pathlib import Path
from typing import Optional, Literal
from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import psutil


class ElohimOSSettings(BaseSettings):
    """
    Unified configuration for ElohimOS

    All settings can be overridden via environment variables with ELOHIMOS_ prefix.
    Example: ELOHIMOS_JWT_SECRET_KEY=mysecret
    """

    model_config = SettingsConfigDict(
        env_prefix="ELOHIMOS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ============================================
    # SYSTEM SETTINGS
    # ============================================

    environment: Literal["development", "production", "testing"] = Field(
        default="development",
        description="Application environment"
    )

    debug: bool = Field(
        default=True,
        description="Enable debug mode"
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    # ============================================
    # API SERVER SETTINGS
    # ============================================

    api_host: str = Field(
        default="localhost",
        description="API server host"
    )

    api_port: int = Field(
        default=8000,
        description="API server port"
    )

    api_workers: int = Field(
        default=1,
        description="Number of API workers (Uvicorn)"
    )

    cors_origins: list[str] = Field(
        default=["http://localhost:4200", "http://127.0.0.1:4200"],
        description="Allowed CORS origins"
    )

    # ============================================
    # SECURITY SETTINGS
    # ============================================

    jwt_secret_key: str = Field(
        default="",
        description="JWT signing secret key (REQUIRED - set via ELOHIMOS_JWT_SECRET_KEY)"
    )

    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = Field(
        default="HS256",
        description="JWT signing algorithm (only HMAC algorithms allowed)"
    )

    jwt_access_token_expire_minutes: int = Field(
        default=60,  # 1 hour (OWASP recommended: 15min-1hr for access tokens)
        description="Access token expiration in minutes"
    )

    session_timeout_hours: int = Field(
        default=24,
        description="Session timeout in hours"
    )

    max_login_attempts: int = Field(
        default=5,
        description="Maximum failed login attempts before lockout"
    )

    # ============================================
    # OFFLINE / AIR-GAP SETTINGS
    # ============================================

    airgap_mode: bool = Field(
        default=False,
        description="Enable air-gap mode (disables all external network calls)"
    )

    offline_mode: bool = Field(
        default=False,
        description="Enable offline mode (skips non-essential external calls)"
    )

    # ============================================
    # WEBAUTHN SETTINGS
    # ============================================

    webauthn_rp_id: str = Field(
        default="localhost",
        description="WebAuthn Relying Party ID (must match domain)"
    )

    webauthn_rp_name: str = Field(
        default="ElohimOS",
        description="WebAuthn Relying Party name (displayed to user)"
    )

    webauthn_origin: str = Field(
        default="http://localhost:3000",
        description="WebAuthn origin (frontend URL)"
    )

    # ============================================
    # PATH CONFIGURATION
    # ============================================

    data_dir: Path = Field(
        default_factory=lambda: Path.cwd() / ".neutron_data",
        description="Base data directory for all ElohimOS data"
    )

    @field_validator("data_dir", mode="after")
    @classmethod
    def ensure_data_dir_exists(cls, v: Path) -> Path:
        """Ensure data directory exists"""
        v.mkdir(parents=True, exist_ok=True)
        return v

    @model_validator(mode="after")
    def validate_jwt_secret(self) -> "ElohimOSSettings":
        """Validate JWT secret is properly configured"""
        insecure_defaults = [
            "",
            "CHANGE_ME_IN_PRODUCTION_12345678901234567890",
            "secret",
            "changeme",
        ]

        if self.jwt_secret_key.lower() in [s.lower() for s in insecure_defaults]:
            if self.environment == "production":
                raise ValueError(
                    "JWT_SECRET_KEY must be set in production! "
                    "Set ELOHIMOS_JWT_SECRET_KEY environment variable to a secure random string (at least 32 chars)"
                )
            else:
                # In development, auto-generate a random secret
                import warnings
                object.__setattr__(self, "jwt_secret_key", secrets.token_urlsafe(32))
                warnings.warn(
                    "JWT_SECRET_KEY not set - using auto-generated secret. "
                    "This is fine for development but tokens will be invalidated on restart. "
                    "Set ELOHIMOS_JWT_SECRET_KEY for persistent sessions.",
                    UserWarning,
                    stacklevel=2
                )

        if len(self.jwt_secret_key) < 32:
            if self.environment == "production":
                raise ValueError(
                    f"JWT_SECRET_KEY is too short ({len(self.jwt_secret_key)} chars). "
                    "Must be at least 32 characters for security."
                )

        return self

    # ============================================
    # DATABASE SETTINGS
    # ============================================

    db_timeout: int = Field(
        default=300,
        description="Database operation timeout in seconds"
    )

    db_retry_count: int = Field(
        default=3,
        description="Number of retries for failed DB operations"
    )

    db_retry_delay: int = Field(
        default=5,
        description="Delay between DB retries in seconds"
    )

    # ============================================
    # OLLAMA SETTINGS
    # ============================================

    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL"
    )

    ollama_timeout: int = Field(
        default=300,
        description="Ollama request timeout in seconds"
    )

    # GPU Offload
    ollama_num_gpu_layers: int = Field(
        default=100,
        description="Number of GPU layers (100 = full GPU offload)"
    )

    # Context Window
    ollama_num_ctx: int = Field(
        default=200000,
        description="Max context window size in tokens"
    )

    # Batching
    ollama_batch_size: int = Field(
        default=512,
        description="Tokens per batch for GPU processing"
    )

    ollama_ubatch_size: int = Field(
        default=128,
        description="Micro-batch size for GPU processing"
    )

    # Memory Management
    ollama_use_mmap: bool = Field(
        default=True,
        description="Use memory-mapped files (faster model loading)"
    )

    ollama_use_mlock: bool = Field(
        default=False,
        description="Lock model in RAM (set True if enough RAM)"
    )

    # Threading
    ollama_num_thread: int = Field(
        default=8,
        description="Number of CPU threads (set to P-cores count)"
    )

    # Performance Mode
    ollama_mode: Literal["performance", "balanced", "silent"] = Field(
        default="performance",
        description="Ollama performance mode"
    )

    # ============================================
    # FILE UPLOAD SETTINGS
    # ============================================

    max_file_size_mb: int = Field(
        default=1000,
        description="Maximum file upload size in MB"
    )

    allowed_upload_extensions: list[str] = Field(
        default=[".csv", ".xlsx", ".xls", ".json", ".parquet", ".txt", ".pdf", ".png", ".jpg", ".jpeg"],
        description="Allowed file upload extensions"
    )

    chunk_size: int = Field(
        default=10000,
        description="Default chunk size for file processing"
    )

    # ============================================
    # RATE LIMITING
    # ============================================

    rate_limit_global: str = Field(
        default="100/minute",
        description="Global rate limit (requests per time window)"
    )

    rate_limit_auth: str = Field(
        default="5/minute",
        description="Auth endpoint rate limit"
    )

    rate_limit_chat: str = Field(
        default="20/minute",
        description="Chat endpoint rate limit"
    )

    # ============================================
    # AGENT/AI SETTINGS
    # ============================================

    agent_timeout: int = Field(
        default=600,
        description="Agent operation timeout in seconds"
    )

    max_agent_iterations: int = Field(
        default=10,
        description="Maximum iterations for agent reasoning loops"
    )

    orchestrator_model: str = Field(
        default="qwen2.5:1.5b",
        description="Default model for orchestrator (should be small/fast)"
    )

    # ============================================
    # EMBEDDINGS SETTINGS
    # ============================================

    embedding_model: str = Field(
        default="nomic-embed-text",
        description="Default embedding model"
    )

    embedding_dimension: int = Field(
        default=768,
        description="Embedding vector dimension"
    )

    # ============================================
    # P2P MESH NETWORKING
    # ============================================

    p2p_enabled: bool = Field(
        default=False,
        description="Enable P2P mesh networking features"
    )

    p2p_port: int = Field(
        default=9000,
        description="P2P networking port"
    )

    p2p_discovery_interval: int = Field(
        default=30,
        description="P2P discovery interval in seconds"
    )

    # ============================================
    # PERFORMANCE SETTINGS
    # ============================================

    enable_parallel_processing: bool = Field(
        default=True,
        description="Enable parallel processing for data operations"
    )

    max_workers: Optional[int] = Field(
        default=None,
        description="Max worker threads (None = CPU count)"
    )

    memory_limit_mb: int = Field(
        default=4096,
        description="Memory limit for data processing in MB"
    )

    # NLQ Performance Limits
    nlq_default_limit: int = Field(
        default=1000,
        description="Default LIMIT for NL→SQL queries when not specified"
    )

    max_query_rows: int = Field(
        default=10000,
        description="Hard cap for query result rows (server-side)"
    )

    profiler_default_sample_rows: int = Field(
        default=50000,
        description="Default sample size for Pattern Discovery profiler"
    )

    # ============================================
    # BACKUP AND SYNC SETTINGS
    # ============================================

    backup_enabled: bool = Field(
        default=False,
        description="Enable automatic backups"
    )

    backup_interval_hours: int = Field(
        default=24,
        description="Backup interval in hours"
    )

    backup_retention_days: int = Field(
        default=30,
        description="Backup retention in days"
    )

    # ============================================
    # DEVELOPER SETTINGS
    # ============================================

    dev_mode: bool = Field(
        default=False,
        description="Enable developer mode (bypass rate limits, extra logging)"
    )

    dev_rate_limit_multiplier: int = Field(
        default=10,
        description="Rate limit multiplier for dev mode"
    )

    # ============================================
    # CLOUD STORAGE (S3) SETTINGS
    # ============================================

    cloud_storage_enabled: bool = Field(
        default=False,
        description="Enable cloud storage integration (S3/compatible)"
    )

    cloud_storage_provider: Literal["s3", "local"] = Field(
        default="local",
        description="Cloud storage provider (s3 for AWS S3/compatible, local for filesystem)"
    )

    s3_bucket_name: str = Field(
        default="",
        description="S3 bucket name for cloud storage"
    )

    s3_region: str = Field(
        default="us-east-1",
        description="AWS region for S3 bucket"
    )

    s3_access_key_id: str = Field(
        default="",
        description="AWS access key ID (leave empty to use IAM roles/instance profile)"
    )

    s3_secret_access_key: str = Field(
        default="",
        description="AWS secret access key (leave empty to use IAM roles/instance profile)"
    )

    s3_endpoint_url: str = Field(
        default="",
        description="Custom S3 endpoint URL (for MinIO, LocalStack, or S3-compatible services)"
    )

    s3_presigned_url_expiry_seconds: int = Field(
        default=3600,
        description="Presigned URL expiration time in seconds (default: 1 hour)"
    )

    # ============================================
    # COMPUTED PROPERTIES
    # ============================================

    @property
    def app_db(self) -> Path:
        """Main application database path"""
        return self.data_dir / "elohimos_app.db"

    @property
    def vault_db(self) -> Path:
        """Vault database path"""
        return self.data_dir / "vault.db"

    @property
    def datasets_db(self) -> Path:
        """Datasets database path"""
        return self.data_dir / "datasets" / "datasets.db"

    @property
    def memory_db(self) -> Path:
        """Chat memory database path"""
        return self.data_dir / "memory" / "chat_memory.db"

    @property
    def uploads_dir(self) -> Path:
        """Uploads directory path"""
        path = self.data_dir / "uploads"
        path.mkdir(exist_ok=True, parents=True)
        return path

    @property
    def temp_uploads_dir(self) -> Path:
        """Temporary uploads directory"""
        path = Path(__file__).parent / "temp_uploads"
        path.mkdir(exist_ok=True)
        return path

    @property
    def temp_exports_dir(self) -> Path:
        """Temporary exports directory"""
        path = Path(__file__).parent / "temp_exports"
        path.mkdir(exist_ok=True)
        return path

    @property
    def cache_dir(self) -> Path:
        """Cache directory path"""
        path = self.data_dir / "cache"
        path.mkdir(exist_ok=True, parents=True)
        return path

    @property
    def shared_files_dir(self) -> Path:
        """P2P shared files directory"""
        path = self.data_dir / "shared_files"
        path.mkdir(exist_ok=True, parents=True)
        return path

    @property
    def model_hot_slots_file(self) -> Path:
        """Model hot slots configuration file"""
        return self.data_dir / "model_hot_slots.json"

    @property
    def is_apple_silicon(self) -> bool:
        """Check if running on Apple Silicon"""
        return platform.processor() == 'arm' and platform.system() == 'Darwin'

    @property
    def total_ram_gb(self) -> float:
        """Get total system RAM in GB"""
        return psutil.virtual_memory().total / (1024 ** 3)

    @property
    def cpu_cores(self) -> int:
        """Get number of CPU cores (P-cores only)"""
        return psutil.cpu_count(logical=False) or 1

    # ============================================
    # HELPER METHODS
    # ============================================

    def get_ollama_generation_options(self, **overrides) -> dict:
        """Get Ollama generation options with optional overrides"""
        options = {
            "num_ctx": self.ollama_num_ctx,
            "num_gpu": self.ollama_num_gpu_layers,
            "num_thread": self.ollama_num_thread,
        }
        options.update(overrides)
        return options

    def get_rate_limit(self, endpoint_type: str = "global") -> str:
        """Get rate limit for specific endpoint type"""
        limits = {
            "global": self.rate_limit_global,
            "auth": self.rate_limit_auth,
            "chat": self.rate_limit_chat,
        }

        limit = limits.get(endpoint_type, self.rate_limit_global)

        # Apply dev mode multiplier
        if self.dev_mode:
            parts = limit.split("/")
            if len(parts) == 2:
                count = int(parts[0]) * self.dev_rate_limit_multiplier
                return f"{count}/{parts[1]}"

        return limit

    def detect_optimal_ollama_settings(self) -> dict:
        """Auto-detect optimal Ollama settings for current hardware"""
        settings = {}

        if self.is_apple_silicon:
            # Apple Silicon optimizations
            settings["num_gpu_layers"] = 100  # Full GPU offload
            settings["use_mmap"] = True
            settings["batch_size"] = 512

            # Adjust based on RAM
            if self.total_ram_gb >= 64:
                settings["use_mlock"] = True  # Lock in RAM
                settings["num_ctx"] = 200000  # Full 200k context
            elif self.total_ram_gb >= 32:
                settings["num_ctx"] = 128000
            else:
                settings["num_ctx"] = 32000

            # Set threads to P-core count
            settings["num_thread"] = min(self.cpu_cores, 8)

        else:
            # Non-Apple Silicon defaults
            settings["num_gpu_layers"] = 50
            settings["num_ctx"] = 8192
            settings["batch_size"] = 256

        return settings

    def to_dict(self) -> dict:
        """Convert settings to dictionary"""
        return self.model_dump()


# ============================================
# SINGLETON PATTERN
# ============================================

@lru_cache()
def get_settings() -> ElohimOSSettings:
    """
    Get cached settings instance (singleton pattern)

    Returns:
        ElohimOSSettings: Application settings
    """
    return ElohimOSSettings()


# ============================================
# BACKWARDS COMPATIBILITY
# ============================================

# For existing code that imports PATHS from config_paths
settings = get_settings()
PATHS = settings  # Acts as a drop-in replacement for PathConfig


# ============================================
# OFFLINE / AIR-GAP MODE HELPERS
# ============================================

def is_airgap_mode() -> bool:
    """
    Check if air-gap mode is enabled (no external network calls allowed).

    Returns True if any of these conditions are met:
    - ELOHIMOS_AIRGAP_MODE=true
    - MAGNETAR_AIRGAP_MODE=true
    - ELOHIM_OFFLINE_MODE=true (deprecated, for compatibility)

    In air-gap mode:
    - All external HTTP calls are skipped
    - Cloud sync features are disabled
    - Password breach checking is skipped
    - Only local network (LAN) operations are allowed
    """
    import os

    settings = get_settings()
    if settings.airgap_mode:
        return True

    # Check legacy env vars for backwards compatibility
    legacy_vars = ["MAGNETAR_AIRGAP_MODE", "ELOHIM_OFFLINE_MODE"]
    truthy_values = {"true", "1", "yes", "on"}

    for var in legacy_vars:
        value = os.getenv(var, "").lower().strip()
        if value in truthy_values:
            return True

    return False


def is_offline_mode() -> bool:
    """
    Check if offline mode is enabled (non-essential external calls skipped).

    Returns True if:
    - Air-gap mode is enabled (which implies offline mode)
    - ELOHIMOS_OFFLINE_MODE=true
    - ELOHIM_OFFLINE_MODE=true (deprecated)

    In offline mode:
    - Password breach checking is skipped with warning
    - Cloud sync is skipped but data is queued
    - Model listing uses cache when Ollama is unreachable
    """
    import os

    if is_airgap_mode():
        return True

    settings = get_settings()
    if settings.offline_mode:
        return True

    # Check legacy env var
    value = os.getenv("ELOHIM_OFFLINE_MODE", "").lower().strip()
    return value in {"true", "1", "yes", "on"}
