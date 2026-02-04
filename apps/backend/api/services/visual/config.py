"""
Configuration for Visual Understanding System

Provides configuration management for vision models and analysis settings.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .image_analyzer import VisionModelConfig, VisionModelProvider


@dataclass
class VisualServiceConfig:
    """
    Configuration for the visual understanding service.

    Manages model settings, performance options, and feature flags.
    """

    # Primary model configuration
    primary_model: VisionModelConfig | None = None

    # Fallback model (if primary fails)
    fallback_model: VisionModelConfig | None = None

    # Processing options
    max_image_size_mb: int = 10
    max_concurrent_requests: int = 5
    default_timeout_seconds: int = 60

    # Caching
    enable_result_cache: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour
    cache_max_entries: int = 1000

    # Feature flags
    enable_mockup_generation: bool = True
    enable_error_diagnosis: bool = True
    enable_architecture_parsing: bool = True
    enable_code_extraction: bool = True

    # Code generation settings
    default_framework: str = "react"
    include_typescript: bool = True
    include_tests: bool = False

    # Quality settings
    min_confidence_threshold: float = 0.5
    max_retries: int = 2

    # Storage
    temp_dir: Path = field(default_factory=lambda: Path("/tmp/visual_analysis"))
    save_results: bool = False
    results_dir: Path | None = None

    def __post_init__(self):
        """Validate configuration"""
        if self.max_image_size_mb <= 0:
            raise ValueError("max_image_size_mb must be positive")

        if self.max_concurrent_requests <= 0:
            raise ValueError("max_concurrent_requests must be positive")

        if not 0.0 <= self.min_confidence_threshold <= 1.0:
            raise ValueError("min_confidence_threshold must be between 0 and 1")

        # Create directories if saving results
        if self.save_results:
            if self.results_dir is None:
                self.results_dir = Path("./visual_results")
            self.results_dir.mkdir(parents=True, exist_ok=True)

        self.temp_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "VisualServiceConfig":
        """
        Create configuration from environment variables.

        Environment variables:
        - OPENAI_API_KEY: OpenAI API key for GPT-4V
        - ANTHROPIC_API_KEY: Anthropic API key for Claude
        - LLAVA_ENDPOINT: LLaVA server endpoint for local model
        - VISUAL_MAX_IMAGE_SIZE_MB: Maximum image size (default: 10)
        - VISUAL_MAX_CONCURRENT: Max concurrent requests (default: 5)
        - VISUAL_ENABLE_CACHE: Enable result caching (default: true)
        - VISUAL_DEFAULT_FRAMEWORK: Default code framework (default: react)
        """
        # Determine primary model from available keys
        primary_model = None
        fallback_model = None

        openai_key = os.getenv("OPENAI_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        llava_endpoint = os.getenv("LLAVA_ENDPOINT")

        # Prefer GPT-4V as primary if available
        if openai_key:
            primary_model = VisionModelConfig(
                provider=VisionModelProvider.GPT4V,
                model_name=os.getenv("OPENAI_MODEL", "gpt-4-vision-preview"),
                api_key=openai_key,
                max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "2500")),
                temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            )

            # Use Claude as fallback if available
            if anthropic_key:
                fallback_model = VisionModelConfig(
                    provider=VisionModelProvider.CLAUDE,
                    model_name=os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229"),
                    api_key=anthropic_key,
                    max_tokens=int(os.getenv("ANTHROPIC_MAX_TOKENS", "2500")),
                )

        # Use Claude as primary if no OpenAI key
        elif anthropic_key:
            primary_model = VisionModelConfig(
                provider=VisionModelProvider.CLAUDE,
                model_name=os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229"),
                api_key=anthropic_key,
                max_tokens=int(os.getenv("ANTHROPIC_MAX_TOKENS", "2500")),
                temperature=float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7")),
            )

        # Use LLaVA if endpoint provided
        elif llava_endpoint:
            primary_model = VisionModelConfig(
                provider=VisionModelProvider.LLAVA,
                model_name=os.getenv("LLAVA_MODEL", "llava-v1.5-13b"),
                api_base=llava_endpoint,
                device=os.getenv("LLAVA_DEVICE", "auto"),
                max_tokens=int(os.getenv("LLAVA_MAX_TOKENS", "2500")),
            )

        return cls(
            primary_model=primary_model,
            fallback_model=fallback_model,
            max_image_size_mb=int(os.getenv("VISUAL_MAX_IMAGE_SIZE_MB", "10")),
            max_concurrent_requests=int(os.getenv("VISUAL_MAX_CONCURRENT", "5")),
            enable_result_cache=os.getenv("VISUAL_ENABLE_CACHE", "true").lower() == "true",
            cache_ttl_seconds=int(os.getenv("VISUAL_CACHE_TTL", "3600")),
            default_framework=os.getenv("VISUAL_DEFAULT_FRAMEWORK", "react"),
            include_typescript=os.getenv("VISUAL_INCLUDE_TYPESCRIPT", "true").lower() == "true",
            save_results=os.getenv("VISUAL_SAVE_RESULTS", "false").lower() == "true",
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "primary_model": self.primary_model.to_dict() if self.primary_model else None,
            "fallback_model": self.fallback_model.to_dict() if self.fallback_model else None,
            "max_image_size_mb": self.max_image_size_mb,
            "max_concurrent_requests": self.max_concurrent_requests,
            "enable_result_cache": self.enable_result_cache,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "features": {
                "mockup_generation": self.enable_mockup_generation,
                "error_diagnosis": self.enable_error_diagnosis,
                "architecture_parsing": self.enable_architecture_parsing,
                "code_extraction": self.enable_code_extraction,
            },
            "code_generation": {
                "default_framework": self.default_framework,
                "include_typescript": self.include_typescript,
                "include_tests": self.include_tests,
            },
            "quality": {
                "min_confidence_threshold": self.min_confidence_threshold,
                "max_retries": self.max_retries,
            },
        }


# ============================================================================
# Preset Configurations
# ============================================================================


def get_development_config() -> VisualServiceConfig:
    """
    Development configuration.

    - Relaxed settings
    - More verbose output
    - Result saving enabled
    """
    return VisualServiceConfig(
        max_image_size_mb=20,  # Larger images allowed
        max_concurrent_requests=2,  # Fewer concurrent to avoid rate limits
        enable_result_cache=True,
        cache_ttl_seconds=7200,  # 2 hours
        min_confidence_threshold=0.3,  # Lower threshold for testing
        save_results=True,
        include_tests=True,  # Generate tests in dev
    )


def get_production_config() -> VisualServiceConfig:
    """
    Production configuration.

    - Strict limits
    - Performance optimized
    - High quality threshold
    """
    return VisualServiceConfig(
        max_image_size_mb=10,
        max_concurrent_requests=10,  # Higher throughput
        enable_result_cache=True,
        cache_ttl_seconds=3600,  # 1 hour
        cache_max_entries=5000,  # Larger cache
        min_confidence_threshold=0.7,  # Higher quality
        max_retries=3,
        save_results=False,  # Don't save in prod
    )


def get_high_performance_config() -> VisualServiceConfig:
    """
    High-performance configuration for batch processing.

    - Maximum concurrency
    - Aggressive caching
    - Lower quality for speed
    """
    return VisualServiceConfig(
        max_image_size_mb=5,  # Smaller images process faster
        max_concurrent_requests=20,
        enable_result_cache=True,
        cache_ttl_seconds=7200,
        cache_max_entries=10000,
        min_confidence_threshold=0.5,
        default_timeout_seconds=30,  # Shorter timeout
    )


def get_high_quality_config() -> VisualServiceConfig:
    """
    High-quality configuration for critical analysis.

    - Lower concurrency for stability
    - Longer timeouts
    - High quality threshold
    - Multiple retries
    """
    return VisualServiceConfig(
        max_image_size_mb=15,  # Allow high-res images
        max_concurrent_requests=3,  # Controlled concurrency
        enable_result_cache=True,
        min_confidence_threshold=0.85,  # Very high quality
        max_retries=5,  # More retries
        default_timeout_seconds=120,  # Longer timeout
        save_results=True,  # Save for review
    )


# ============================================================================
# Singleton Configuration
# ============================================================================


_service_config: VisualServiceConfig | None = None


def get_service_config(force_reload: bool = False) -> VisualServiceConfig:
    """
    Get or create service configuration.

    By default, loads from environment variables.

    Args:
        force_reload: Force reload from environment

    Returns:
        Service configuration
    """
    global _service_config

    if force_reload or _service_config is None:
        _service_config = VisualServiceConfig.from_env()

    return _service_config


def set_service_config(config: VisualServiceConfig) -> None:
    """
    Set service configuration.

    Args:
        config: Configuration to use
    """
    global _service_config
    _service_config = config


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Load from environment
    config = VisualServiceConfig.from_env()
    print("Environment Configuration:")
    print(config.to_dict())

    # Use preset
    dev_config = get_development_config()
    print("\nDevelopment Configuration:")
    print(dev_config.to_dict())

    # Custom configuration
    custom_config = VisualServiceConfig(
        primary_model=VisionModelConfig(
            provider=VisionModelProvider.GPT4V,
            model_name="gpt-4-vision-preview",
            api_key="your-key-here",
        ),
        max_image_size_mb=15,
        enable_result_cache=True,
        save_results=True,
    )
    print("\nCustom Configuration:")
    print(custom_config.to_dict())
