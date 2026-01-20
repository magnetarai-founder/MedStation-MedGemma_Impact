"""
llama.cpp Server Integration

Provides:
- Server lifecycle management (start/stop)
- GGUF model loading
- Chat inference via OpenAI-compatible API
- Metal GPU optimization for Apple Silicon
- Hardware detection and validation
"""

from .config import LlamaCppConfig, get_llamacpp_config
from .server import LlamaCppServer, ServerStatus, get_llamacpp_server
from .inference import LlamaCppInference, ChatMessage, ChatCompletionChunk, get_llamacpp_inference
from .hardware import HardwareInfo, detect_hardware, validate_model_fits, get_hardware_info

__all__ = [
    "LlamaCppConfig",
    "get_llamacpp_config",
    "LlamaCppServer",
    "ServerStatus",
    "get_llamacpp_server",
    "LlamaCppInference",
    "ChatMessage",
    "ChatCompletionChunk",
    "get_llamacpp_inference",
    "HardwareInfo",
    "detect_hardware",
    "validate_model_fits",
    "get_hardware_info",
]
