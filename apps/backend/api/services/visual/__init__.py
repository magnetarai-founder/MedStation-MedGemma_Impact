"""
Visual Understanding System

Provides image and diagram analysis for:
- UI mockup to code conversion
- Error screenshot diagnosis
- Architecture diagram understanding
- Code/text extraction from images
- Visual debugging assistance

Supports integration with various vision models:
- LLaVA (local)
- GPT-4V (OpenAI)
- Claude Vision (Anthropic)
- Other local vision models
"""

from .image_analyzer import (
    ArchitectureNode,
    BoundingBox,
    CodeFramework,
    CodeTemplate,
    ComponentType,
    ErrorInfo,
    ImageAnalysisResult,
    ImageFormat,
    UIComponent,
    VisionModelConfig,
    VisionModelProvider,
    VisualAnalyzer,
    get_visual_analyzer,
)

__all__ = [
    # Core analyzer
    "VisualAnalyzer",
    "get_visual_analyzer",
    # Data models
    "ImageAnalysisResult",
    "UIComponent",
    "ComponentType",
    "ErrorInfo",
    "ArchitectureNode",
    "CodeTemplate",
    "BoundingBox",
    "CodeFramework",
    "ImageFormat",
    # Configuration
    "VisionModelConfig",
    "VisionModelProvider",
]
