"""
llama.cpp Configuration

Configuration settings for the llama.cpp server, optimized for Apple Silicon.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class LlamaCppConfig:
    """
    Configuration for llama.cpp server

    Optimized defaults for Apple Silicon with Metal GPU acceleration.
    """

    # Server settings
    host: str = "127.0.0.1"
    port: int = 8080
    timeout_seconds: int = 600  # 10 minutes for long generations

    # GPU settings (Apple Silicon / NVIDIA)
    n_gpu_layers: int = -1  # -1 = all layers on GPU (Metal)
    use_mmap: bool = True   # Memory-mapped file loading
    use_mlock: bool = False # Lock model in RAM (disable for Metal)

    # Context and batch settings
    context_size: int = 8192  # Default context window
    batch_size: int = 512     # Batch size for prompt processing
    ubatch_size: int = 512    # Micro-batch size

    # Threading
    n_threads: int = 0        # 0 = auto-detect
    n_threads_batch: int = 0  # 0 = auto-detect

    # Generation defaults
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    max_tokens: int = 2048

    # Server options
    embedding: bool = False   # Enable embeddings endpoint
    flash_attn: bool = True   # Flash attention (improves performance)
    cont_batching: bool = True  # Continuous batching

    # Paths
    llama_cpp_path: Optional[str] = None  # Path to llama-server binary

    def __post_init__(self):
        """Auto-detect llama.cpp binary path if not set"""
        if not self.llama_cpp_path:
            self.llama_cpp_path = self._find_llama_cpp()

    def _find_llama_cpp(self) -> Optional[str]:
        """Find llama-server binary in common locations"""
        import shutil

        # Try common binary names
        for name in ["llama-server", "llama.cpp-server", "server"]:
            path = shutil.which(name)
            if path:
                logger.info(f"Found llama.cpp at: {path}")
                return path

        # Try homebrew location
        homebrew_path = Path("/opt/homebrew/bin/llama-server")
        if homebrew_path.exists():
            logger.info(f"Found llama.cpp at: {homebrew_path}")
            return str(homebrew_path)

        # Try common build locations
        common_paths = [
            Path.home() / "llama.cpp" / "build" / "bin" / "llama-server",
            Path.home() / "llama.cpp" / "llama-server",
            Path("/usr/local/bin/llama-server"),
        ]

        for path in common_paths:
            if path.exists():
                logger.info(f"Found llama.cpp at: {path}")
                return str(path)

        logger.warning("llama-server binary not found. Install via: brew install llama.cpp")
        return None

    @property
    def base_url(self) -> str:
        """Server base URL"""
        return f"http://{self.host}:{self.port}"

    @property
    def health_url(self) -> str:
        """Health check endpoint"""
        return f"{self.base_url}/health"

    @property
    def completion_url(self) -> str:
        """Chat completion endpoint (OpenAI-compatible)"""
        return f"{self.base_url}/v1/chat/completions"

    def get_server_args(self, model_path: str) -> list:
        """
        Build command-line arguments for llama-server

        Args:
            model_path: Path to the GGUF model file

        Returns:
            List of command-line arguments
        """
        args = [
            "--model", model_path,
            "--host", self.host,
            "--port", str(self.port),
            "--ctx-size", str(self.context_size),
            "--batch-size", str(self.batch_size),
            "--ubatch-size", str(self.ubatch_size),
            "--n-gpu-layers", str(self.n_gpu_layers),
        ]

        if self.n_threads > 0:
            args.extend(["--threads", str(self.n_threads)])

        if self.n_threads_batch > 0:
            args.extend(["--threads-batch", str(self.n_threads_batch)])

        if self.use_mmap:
            args.append("--mmap")

        if self.use_mlock:
            args.append("--mlock")

        if self.flash_attn:
            args.append("--flash-attn")

        if self.cont_batching:
            args.append("--cont-batching")

        if self.embedding:
            args.append("--embedding")

        return args

    @classmethod
    def from_environment(cls) -> "LlamaCppConfig":
        """Create config from environment variables"""
        return cls(
            host=os.environ.get("LLAMACPP_HOST", "127.0.0.1"),
            port=int(os.environ.get("LLAMACPP_PORT", "8080")),
            n_gpu_layers=int(os.environ.get("LLAMACPP_GPU_LAYERS", "-1")),
            context_size=int(os.environ.get("LLAMACPP_CONTEXT_SIZE", "8192")),
            batch_size=int(os.environ.get("LLAMACPP_BATCH_SIZE", "512")),
            llama_cpp_path=os.environ.get("LLAMACPP_PATH"),
        )


# Singleton config instance
_config_instance: Optional[LlamaCppConfig] = None


def get_llamacpp_config() -> LlamaCppConfig:
    """Get the singleton config instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = LlamaCppConfig.from_environment()
    return _config_instance


__all__ = [
    "LlamaCppConfig",
    "get_llamacpp_config",
]
