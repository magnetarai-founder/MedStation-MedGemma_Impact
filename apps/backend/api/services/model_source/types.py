"""
Model Source Types - Unified model abstraction for multiple inference backends

Supports:
- Ollama models (local inference server)
- HuggingFace GGUF models (llama.cpp inference)
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class ModelSourceType(str, Enum):
    """Source/backend for a model"""
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"


class ModelCapability(str, Enum):
    """Model capabilities/specializations"""
    CHAT = "chat"
    CODE = "code"
    VISION = "vision"
    MEDICAL = "medical"
    EMBEDDING = "embedding"
    REASONING = "reasoning"


class HardwareRequirements(BaseModel):
    """Hardware requirements for running a model"""
    min_vram_gb: float = Field(description="Minimum VRAM in GB")
    recommended_vram_gb: float = Field(description="Recommended VRAM in GB")
    min_ram_gb: float = Field(default=8.0, description="Minimum system RAM in GB")
    supports_metal: bool = Field(default=True, description="Supports Apple Metal GPU")
    supports_cuda: bool = Field(default=True, description="Supports NVIDIA CUDA")
    cpu_only_viable: bool = Field(default=False, description="Can run efficiently on CPU only")


class UnifiedModel(BaseModel):
    """
    Unified model representation across all sources

    This abstraction allows the frontend to display and manage models
    from different backends (Ollama, HuggingFace/llama.cpp) uniformly.
    """
    id: str = Field(description="Unique identifier (e.g., 'hf:medgemma-1.5-4b-q4' or 'ollama:llama3.2')")
    name: str = Field(description="Human-readable display name")
    source: ModelSourceType = Field(description="Model source backend")

    # Size and quantization
    size_bytes: Optional[int] = Field(default=None, description="Model file size in bytes")
    quantization: Optional[str] = Field(default=None, description="Quantization level (Q4_K_M, Q5_K_M, Q8_0, etc.)")
    parameter_count: Optional[str] = Field(default=None, description="Parameter count (e.g., '4B', '7B', '70B')")

    # Status
    is_downloaded: bool = Field(default=False, description="Whether model is available locally")
    is_running: bool = Field(default=False, description="Whether model is currently loaded for inference")
    download_progress: Optional[float] = Field(default=None, description="Download progress (0-100) if downloading")

    # Metadata
    description: Optional[str] = Field(default=None, description="Model description")
    capabilities: List[ModelCapability] = Field(default_factory=list, description="Model capabilities")
    context_length: Optional[int] = Field(default=None, description="Maximum context window size")

    # Source-specific identifiers
    repo_id: Optional[str] = Field(default=None, description="HuggingFace repo ID")
    filename: Optional[str] = Field(default=None, description="GGUF filename for HuggingFace models")
    ollama_name: Optional[str] = Field(default=None, description="Ollama model name (e.g., 'llama3.2:latest')")

    # Hardware requirements
    hardware: Optional[HardwareRequirements] = Field(default=None, description="Hardware requirements")

    @property
    def size_formatted(self) -> str:
        """Return human-readable size string"""
        if not self.size_bytes:
            return "Unknown"

        gb = self.size_bytes / (1024 ** 3)
        if gb >= 1:
            return f"{gb:.1f} GB"

        mb = self.size_bytes / (1024 ** 2)
        return f"{mb:.0f} MB"

    @property
    def display_id(self) -> str:
        """User-friendly ID for display"""
        if self.source == ModelSourceType.OLLAMA and self.ollama_name:
            return self.ollama_name
        if self.source == ModelSourceType.HUGGINGFACE and self.filename:
            return self.filename.replace(".gguf", "")
        return self.id


class GGUFDownloadStatus(str, Enum):
    """Download status for GGUF models"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    PAUSED = "paused"


class GGUFDownloadJob(BaseModel):
    """
    Tracks a GGUF model download from HuggingFace

    Supports resumable downloads with progress tracking.
    """
    job_id: str = Field(description="Unique job identifier")
    model_id: str = Field(description="Model ID being downloaded")
    repo_id: str = Field(description="HuggingFace repository ID")
    filename: str = Field(description="GGUF filename")

    status: GGUFDownloadStatus = Field(default=GGUFDownloadStatus.PENDING)
    progress: float = Field(default=0.0, description="Download progress 0-100")
    downloaded_bytes: int = Field(default=0, description="Bytes downloaded so far")
    total_bytes: Optional[int] = Field(default=None, description="Total file size in bytes")

    speed_bps: Optional[int] = Field(default=None, description="Current download speed in bytes/sec")
    eta_seconds: Optional[int] = Field(default=None, description="Estimated time remaining")

    error: Optional[str] = Field(default=None, description="Error message if failed")
    local_path: Optional[str] = Field(default=None, description="Local file path when completed")

    @property
    def speed_formatted(self) -> str:
        """Human-readable download speed"""
        if not self.speed_bps:
            return "—"

        mbps = self.speed_bps / (1024 * 1024)
        if mbps >= 1:
            return f"{mbps:.1f} MB/s"

        kbps = self.speed_bps / 1024
        return f"{kbps:.0f} KB/s"

    @property
    def eta_formatted(self) -> str:
        """Human-readable ETA"""
        if not self.eta_seconds:
            return "—"

        if self.eta_seconds < 60:
            return f"{self.eta_seconds}s"
        if self.eta_seconds < 3600:
            mins = self.eta_seconds // 60
            return f"{mins}m"

        hours = self.eta_seconds // 3600
        mins = (self.eta_seconds % 3600) // 60
        return f"{hours}h {mins}m"


__all__ = [
    "ModelSourceType",
    "ModelCapability",
    "HardwareRequirements",
    "UnifiedModel",
    "GGUFDownloadStatus",
    "GGUFDownloadJob",
]
