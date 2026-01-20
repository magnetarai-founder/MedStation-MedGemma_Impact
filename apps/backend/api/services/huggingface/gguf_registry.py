"""
GGUF Model Registry

Curated catalog of recommended GGUF models from HuggingFace Hub.
Includes hardware requirements and auto-selection based on available VRAM.

Focus on:
- MedGemma 1.5 4B (medical AI for Kaggle competition)
- High-quality code models
- General-purpose chat models optimized for Apple Silicon
"""

import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..model_source.types import ModelCapability, HardwareRequirements, ModelSourceType, UnifiedModel

logger = logging.getLogger(__name__)


class QuantizationLevel(str, Enum):
    """GGUF Quantization levels (lower = smaller but less accurate)"""
    Q2_K = "Q2_K"      # 2-bit, very small but significant quality loss
    Q3_K_S = "Q3_K_S"  # 3-bit small
    Q3_K_M = "Q3_K_M"  # 3-bit medium
    Q4_0 = "Q4_0"      # 4-bit legacy
    Q4_K_S = "Q4_K_S"  # 4-bit small
    Q4_K_M = "Q4_K_M"  # 4-bit medium - best quality/size balance
    Q5_0 = "Q5_0"      # 5-bit legacy
    Q5_K_S = "Q5_K_S"  # 5-bit small
    Q5_K_M = "Q5_K_M"  # 5-bit medium - high quality
    Q6_K = "Q6_K"      # 6-bit - very high quality
    Q8_0 = "Q8_0"      # 8-bit - near lossless
    F16 = "F16"        # 16-bit float - no quantization loss
    F32 = "F32"        # 32-bit float - full precision


@dataclass
class GGUFModelEntry:
    """A GGUF model entry in the registry"""
    id: str                          # Unique identifier
    name: str                        # Display name
    repo_id: str                     # HuggingFace repo ID
    filename: str                    # GGUF filename
    size_gb: float                   # Approximate file size in GB
    parameter_count: str             # Parameter count string (e.g., "4B", "7B")
    quantization: QuantizationLevel  # Quantization level
    context_length: int              # Max context window
    min_vram_gb: float              # Minimum VRAM required
    recommended_vram_gb: float      # Recommended VRAM
    capabilities: List[ModelCapability]
    description: str
    supports_metal: bool = True     # Apple Silicon support
    supports_cuda: bool = True      # NVIDIA GPU support
    cpu_only_viable: bool = False   # Can run on CPU efficiently

    def to_unified_model(self, is_downloaded: bool = False, is_running: bool = False) -> UnifiedModel:
        """Convert to UnifiedModel for API responses"""
        return UnifiedModel(
            id=f"hf:{self.id}",
            name=self.name,
            source=ModelSourceType.HUGGINGFACE,
            size_bytes=int(self.size_gb * 1024**3),
            quantization=self.quantization.value,
            parameter_count=self.parameter_count,
            is_downloaded=is_downloaded,
            is_running=is_running,
            description=self.description,
            capabilities=self.capabilities,
            context_length=self.context_length,
            repo_id=self.repo_id,
            filename=self.filename,
            hardware=HardwareRequirements(
                min_vram_gb=self.min_vram_gb,
                recommended_vram_gb=self.recommended_vram_gb,
                supports_metal=self.supports_metal,
                supports_cuda=self.supports_cuda,
                cpu_only_viable=self.cpu_only_viable,
            )
        )


# ==============================================================================
# MEDGEMMA MODELS - Primary focus for medical AI competition
# ==============================================================================

MEDGEMMA_MODELS: Dict[str, GGUFModelEntry] = {
    "medgemma-1.5-4b-q4": GGUFModelEntry(
        id="medgemma-1.5-4b-q4",
        name="MedGemma 1.5 4B (Q4_K_M)",
        repo_id="google/medgemma-1.5-4b-it-GGUF",
        filename="medgemma-1.5-4b-it-Q4_K_M.gguf",
        size_gb=2.8,
        parameter_count="4B",
        quantization=QuantizationLevel.Q4_K_M,
        context_length=8192,
        min_vram_gb=4.0,
        recommended_vram_gb=6.0,
        capabilities=[ModelCapability.CHAT, ModelCapability.MEDICAL],
        description="Medical-specialized model trained on clinical data. Optimized for medical Q&A, diagnosis assistance, and healthcare documentation. Q4_K_M offers best size/quality balance.",
        cpu_only_viable=True,
    ),
    "medgemma-1.5-4b-q5": GGUFModelEntry(
        id="medgemma-1.5-4b-q5",
        name="MedGemma 1.5 4B (Q5_K_M)",
        repo_id="google/medgemma-1.5-4b-it-GGUF",
        filename="medgemma-1.5-4b-it-Q5_K_M.gguf",
        size_gb=3.4,
        parameter_count="4B",
        quantization=QuantizationLevel.Q5_K_M,
        context_length=8192,
        min_vram_gb=5.0,
        recommended_vram_gb=8.0,
        capabilities=[ModelCapability.CHAT, ModelCapability.MEDICAL],
        description="Medical-specialized model with higher quantization for improved accuracy. Better for nuanced medical reasoning at slight size increase.",
    ),
    "medgemma-1.5-4b-q8": GGUFModelEntry(
        id="medgemma-1.5-4b-q8",
        name="MedGemma 1.5 4B (Q8_0)",
        repo_id="google/medgemma-1.5-4b-it-GGUF",
        filename="medgemma-1.5-4b-it-Q8_0.gguf",
        size_gb=4.5,
        parameter_count="4B",
        quantization=QuantizationLevel.Q8_0,
        context_length=8192,
        min_vram_gb=6.0,
        recommended_vram_gb=10.0,
        capabilities=[ModelCapability.CHAT, ModelCapability.MEDICAL],
        description="Near-lossless quantization for maximum medical accuracy. Use when quality is critical and VRAM is available.",
    ),
}


# ==============================================================================
# CODE MODELS - For development and code assistance
# ==============================================================================

CODE_MODELS: Dict[str, GGUFModelEntry] = {
    "qwen2.5-coder-7b-q4": GGUFModelEntry(
        id="qwen2.5-coder-7b-q4",
        name="Qwen 2.5 Coder 7B (Q4_K_M)",
        repo_id="Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
        filename="qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        size_gb=4.4,
        parameter_count="7B",
        quantization=QuantizationLevel.Q4_K_M,
        context_length=32768,
        min_vram_gb=6.0,
        recommended_vram_gb=8.0,
        capabilities=[ModelCapability.CHAT, ModelCapability.CODE],
        description="Excellent code generation and understanding. Strong at multiple languages, debugging, and code review.",
    ),
    "deepseek-coder-v2-lite-q4": GGUFModelEntry(
        id="deepseek-coder-v2-lite-q4",
        name="DeepSeek Coder V2 Lite (Q4_K_M)",
        repo_id="DeepSeek-AI/DeepSeek-Coder-V2-Lite-Instruct-GGUF",
        filename="deepseek-coder-v2-lite-instruct-q4_k_m.gguf",
        size_gb=9.5,
        parameter_count="16B",
        quantization=QuantizationLevel.Q4_K_M,
        context_length=128000,
        min_vram_gb=12.0,
        recommended_vram_gb=16.0,
        capabilities=[ModelCapability.CHAT, ModelCapability.CODE],
        description="Advanced code model with 128K context. Excellent for large codebase understanding and complex refactoring.",
    ),
    "codellama-13b-q4": GGUFModelEntry(
        id="codellama-13b-q4",
        name="Code Llama 13B (Q4_K_M)",
        repo_id="TheBloke/CodeLlama-13B-Instruct-GGUF",
        filename="codellama-13b-instruct.Q4_K_M.gguf",
        size_gb=7.9,
        parameter_count="13B",
        quantization=QuantizationLevel.Q4_K_M,
        context_length=16384,
        min_vram_gb=10.0,
        recommended_vram_gb=12.0,
        capabilities=[ModelCapability.CHAT, ModelCapability.CODE],
        description="Meta's code-specialized Llama. Strong at Python, robust code completion.",
    ),
}


# ==============================================================================
# GENERAL PURPOSE MODELS - Chat and reasoning
# ==============================================================================

GENERAL_MODELS: Dict[str, GGUFModelEntry] = {
    "llama-3.2-3b-q4": GGUFModelEntry(
        id="llama-3.2-3b-q4",
        name="Llama 3.2 3B (Q4_K_M)",
        repo_id="bartowski/Llama-3.2-3B-Instruct-GGUF",
        filename="Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        size_gb=2.0,
        parameter_count="3B",
        quantization=QuantizationLevel.Q4_K_M,
        context_length=128000,
        min_vram_gb=3.0,
        recommended_vram_gb=4.0,
        capabilities=[ModelCapability.CHAT],
        description="Fast, efficient model for general chat. Great for quick tasks and constrained hardware.",
        cpu_only_viable=True,
    ),
    "llama-3.1-8b-q4": GGUFModelEntry(
        id="llama-3.1-8b-q4",
        name="Llama 3.1 8B (Q4_K_M)",
        repo_id="bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
        filename="Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        size_gb=4.9,
        parameter_count="8B",
        quantization=QuantizationLevel.Q4_K_M,
        context_length=128000,
        min_vram_gb=6.0,
        recommended_vram_gb=8.0,
        capabilities=[ModelCapability.CHAT, ModelCapability.REASONING],
        description="Versatile general-purpose model with 128K context. Excellent balance of capability and efficiency.",
    ),
    "gemma-2-9b-q4": GGUFModelEntry(
        id="gemma-2-9b-q4",
        name="Gemma 2 9B (Q4_K_M)",
        repo_id="bartowski/gemma-2-9b-it-GGUF",
        filename="gemma-2-9b-it-Q4_K_M.gguf",
        size_gb=5.5,
        parameter_count="9B",
        quantization=QuantizationLevel.Q4_K_M,
        context_length=8192,
        min_vram_gb=7.0,
        recommended_vram_gb=10.0,
        capabilities=[ModelCapability.CHAT, ModelCapability.REASONING],
        description="Google's Gemma 2 with strong reasoning. Good for analytical tasks and structured outputs.",
    ),
    "phi-3-medium-q4": GGUFModelEntry(
        id="phi-3-medium-q4",
        name="Phi-3 Medium 14B (Q4_K_M)",
        repo_id="microsoft/Phi-3-medium-4k-instruct-gguf",
        filename="Phi-3-medium-4k-instruct-q4.gguf",
        size_gb=8.2,
        parameter_count="14B",
        quantization=QuantizationLevel.Q4_K_M,
        context_length=4096,
        min_vram_gb=10.0,
        recommended_vram_gb=12.0,
        capabilities=[ModelCapability.CHAT, ModelCapability.REASONING, ModelCapability.CODE],
        description="Microsoft's efficient model with strong reasoning. Punches above its weight class.",
    ),
}


# ==============================================================================
# VISION MODELS - Multimodal understanding
# ==============================================================================

VISION_MODELS: Dict[str, GGUFModelEntry] = {
    "llava-1.6-mistral-7b-q4": GGUFModelEntry(
        id="llava-1.6-mistral-7b-q4",
        name="LLaVA 1.6 Mistral 7B (Q4_K_M)",
        repo_id="cjpais/llava-1.6-mistral-7b-gguf",
        filename="llava-v1.6-mistral-7b.Q4_K_M.gguf",
        size_gb=4.4,
        parameter_count="7B",
        quantization=QuantizationLevel.Q4_K_M,
        context_length=4096,
        min_vram_gb=8.0,
        recommended_vram_gb=10.0,
        capabilities=[ModelCapability.CHAT, ModelCapability.VISION],
        description="Vision-language model for image understanding. Can describe, analyze, and reason about images.",
    ),
}


# ==============================================================================
# COMBINED REGISTRY
# ==============================================================================

# All models combined
ALL_MODELS: Dict[str, GGUFModelEntry] = {
    **MEDGEMMA_MODELS,
    **CODE_MODELS,
    **GENERAL_MODELS,
    **VISION_MODELS,
}

# Recommended models for quick access (curated top picks)
RECOMMENDED_MODELS: List[str] = [
    "medgemma-1.5-4b-q4",     # Medical AI focus
    "llama-3.1-8b-q4",        # General purpose
    "qwen2.5-coder-7b-q4",    # Code generation
    "llama-3.2-3b-q4",        # Lightweight option
]


class GGUFRegistry:
    """
    Registry for discovering and selecting GGUF models

    Provides:
    - Model lookup by ID or capability
    - Hardware-based recommendations
    - Filtering by quantization level
    """

    def __init__(self):
        self._models = ALL_MODELS

    def get_model(self, model_id: str) -> Optional[GGUFModelEntry]:
        """Get a model by ID"""
        return self._models.get(model_id)

    def list_all_models(self) -> List[GGUFModelEntry]:
        """List all available models"""
        return list(self._models.values())

    def list_by_capability(self, capability: ModelCapability) -> List[GGUFModelEntry]:
        """Filter models by capability"""
        return [m for m in self._models.values() if capability in m.capabilities]

    def list_medical_models(self) -> List[GGUFModelEntry]:
        """List all medical-specialized models"""
        return self.list_by_capability(ModelCapability.MEDICAL)

    def list_code_models(self) -> List[GGUFModelEntry]:
        """List all code-specialized models"""
        return self.list_by_capability(ModelCapability.CODE)

    def list_recommended(self) -> List[GGUFModelEntry]:
        """List recommended models"""
        return [self._models[id] for id in RECOMMENDED_MODELS if id in self._models]

    def get_best_for_vram(self, vram_gb: float, capability: Optional[ModelCapability] = None) -> List[GGUFModelEntry]:
        """
        Get models that fit within available VRAM

        Args:
            vram_gb: Available VRAM in GB
            capability: Optional capability filter

        Returns:
            Models sorted by recommended VRAM (largest that fits first)
        """
        models = self._models.values()

        if capability:
            models = [m for m in models if capability in m.capabilities]

        # Filter by VRAM
        fitting = [m for m in models if m.min_vram_gb <= vram_gb]

        # Sort by recommended VRAM descending (best quality that fits)
        fitting.sort(key=lambda m: m.recommended_vram_gb, reverse=True)

        return fitting

    def recommend_medgemma_variant(self, vram_gb: float) -> Optional[GGUFModelEntry]:
        """
        Auto-select the best MedGemma variant based on available VRAM

        Args:
            vram_gb: Available VRAM in GB

        Returns:
            Best MedGemma variant, or None if none fit
        """
        # Prefer higher quantization if VRAM allows
        if vram_gb >= 6.0:
            return MEDGEMMA_MODELS.get("medgemma-1.5-4b-q8")
        elif vram_gb >= 5.0:
            return MEDGEMMA_MODELS.get("medgemma-1.5-4b-q5")
        elif vram_gb >= 4.0:
            return MEDGEMMA_MODELS.get("medgemma-1.5-4b-q4")
        else:
            return None  # Not enough VRAM for any MedGemma variant


# Singleton registry instance
_registry_instance: Optional[GGUFRegistry] = None


def get_gguf_registry() -> GGUFRegistry:
    """Get the singleton GGUF registry instance"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = GGUFRegistry()
    return _registry_instance


__all__ = [
    "GGUFModelEntry",
    "QuantizationLevel",
    "GGUFRegistry",
    "get_gguf_registry",
    "MEDGEMMA_MODELS",
    "CODE_MODELS",
    "GENERAL_MODELS",
    "VISION_MODELS",
    "ALL_MODELS",
    "RECOMMENDED_MODELS",
]
