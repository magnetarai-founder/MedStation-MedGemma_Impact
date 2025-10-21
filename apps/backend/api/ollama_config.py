#!/usr/bin/env python3
"""
Ollama Configuration Manager
Provides fine-grained control over Ollama performance tuning
Optimized for Apple Silicon (M1/M2/M3/M4)
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class OllamaConfig:
    """Ollama performance configuration"""

    # GPU Offload
    num_gpu_layers: int = 100          # 100 = full GPU offload (recommended for M-series)

    # Context Window
    num_ctx: int = 200000              # Max 200k context

    # Batching (bigger = better GPU utilization)
    batch_size: int = 512              # Tokens per batch
    ubatch_size: int = 128             # Micro-batch size

    # Memory Management
    use_mmap: bool = True              # Use memory-mapped files (faster loading)
    use_mlock: bool = False            # Lock model in RAM (set True if enough RAM)

    # Threading
    num_thread: int = 8                # CPU threads (set to P-cores count)

    # Quantization Preference
    preferred_quant: str = "Q6_K"      # Q6_K, Q5_K_M, Q8_0

    # KV Cache
    kv_cache_type: str = "f16"         # f16 or q8_0 or q4_0

    # Performance Mode
    mode: str = "performance"          # performance, balanced, silent

    def __post_init__(self):
        """Adjust settings based on mode"""
        if self.mode == "balanced":
            self.num_gpu_layers = 80
            self.batch_size = 256
        elif self.mode == "silent":
            self.num_gpu_layers = 60
            self.batch_size = 128
            self.num_thread = 4


class OllamaConfigManager:
    """Manages Ollama configuration and applies settings"""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path.home() / ".omnistudio" / "ollama_config.json"

        self.config_path = config_path
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load or create default config
        self.config = self.load_config()

    def load_config(self) -> OllamaConfig:
        """Load config from file or create default"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                config = OllamaConfig(**data)
                logger.info(f"✅ Loaded Ollama config from {self.config_path}")
                return config
            except Exception as e:
                logger.warning(f"Failed to load config: {e}, using defaults")

        # Create default config
        config = OllamaConfig()
        self.save_config(config)
        return config

    def save_config(self, config: Optional[OllamaConfig] = None):
        """Save config to file"""
        if config is None:
            config = self.config

        try:
            with open(self.config_path, 'w') as f:
                json.dump(asdict(config), f, indent=2)
            logger.info(f"✅ Saved Ollama config to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def get_modelfile_params(self) -> Dict[str, Any]:
        """Get parameters for Ollama Modelfile"""
        return {
            "num_ctx": self.config.num_ctx,
            "num_gpu": self.config.num_gpu_layers,
            "num_thread": self.config.num_thread,
            "batch_size": self.config.batch_size,
            "use_mmap": self.config.use_mmap,
            "use_mlock": self.config.use_mlock,
        }

    def get_generation_options(self, **overrides) -> Dict[str, Any]:
        """Get options for ollama.generate() calls"""
        options = {
            "num_ctx": self.config.num_ctx,
            "num_gpu": self.config.num_gpu_layers,
            "num_thread": self.config.num_thread,
        }
        options.update(overrides)
        return options

    def set_mode(self, mode: str):
        """Change performance mode"""
        if mode not in ["performance", "balanced", "silent"]:
            raise ValueError(f"Invalid mode: {mode}")

        self.config.mode = mode
        self.config.__post_init__()  # Reapply mode adjustments
        self.save_config()

        logger.info(f"🔧 Ollama mode set to: {mode}")
        logger.info(f"   GPU layers: {self.config.num_gpu_layers}")
        logger.info(f"   Batch size: {self.config.num_batch_size}")

    def detect_optimal_settings(self) -> OllamaConfig:
        """Auto-detect optimal settings for current hardware"""
        import platform
        import psutil

        # Get system info
        total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        cpu_count = psutil.cpu_count(logical=False)  # P-cores only

        # Detect Apple Silicon
        is_apple_silicon = platform.processor() == 'arm' and platform.system() == 'Darwin'

        config = OllamaConfig()

        if is_apple_silicon:
            # Apple Silicon optimizations
            config.num_gpu_layers = 100  # Full GPU offload
            config.use_mmap = True
            config.batch_size = 512

            # Adjust based on RAM
            if total_ram_gb >= 64:
                config.use_mlock = True  # Lock in RAM if enough memory
                config.num_ctx = 200000  # Full 200k context
            elif total_ram_gb >= 32:
                config.num_ctx = 128000
            else:
                config.num_ctx = 32000

            # Set threads to P-core count
            config.num_thread = min(cpu_count, 8)

            logger.info(f"🍎 Detected Apple Silicon with {total_ram_gb:.0f}GB RAM")
            logger.info(f"   Optimized for: {config.num_gpu_layers} GPU layers, {config.num_ctx} context")

        else:
            # Non-Apple Silicon defaults
            config.num_gpu_layers = 50
            config.num_ctx = 8192
            config.batch_size = 256

        return config

    def get_config_summary(self) -> Dict[str, Any]:
        """Get human-readable config summary"""
        return {
            "mode": self.config.mode,
            "gpu_offload": f"{self.config.num_gpu_layers} layers",
            "context_window": f"{self.config.num_ctx:,} tokens",
            "batch_size": self.config.batch_size,
            "quantization": self.config.preferred_quant,
            "memory_mapped": self.config.use_mmap,
            "memory_locked": self.config.use_mlock,
            "threads": self.config.num_thread,
        }


# Singleton instance
_config_manager = None


def get_ollama_config() -> OllamaConfigManager:
    """Get singleton config manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = OllamaConfigManager()
        logger.info("🔧 Ollama config manager initialized")
    return _config_manager
