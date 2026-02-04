"""
Image Analysis and Visual Understanding System

Provides comprehensive visual understanding capabilities:
- Screenshot analysis and error detection
- UI mockup to code conversion
- Architecture diagram parsing
- Text/code extraction from images
- Visual debugging and diagnosis

Supports multiple vision model backends with abstracted interface.
"""

import base64
import io
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)


# ============================================================================
# Enums and Types
# ============================================================================


class VisionModelProvider(Enum):
    """Supported vision model providers"""

    LLAVA = "llava"  # Local LLaVA model
    GPT4V = "gpt4v"  # OpenAI GPT-4 Vision
    CLAUDE = "claude"  # Anthropic Claude Vision
    GEMINI = "gemini"  # Google Gemini Vision
    QWEN_VL = "qwen_vl"  # Local Qwen-VL
    COGVLM = "cogvlm"  # Local CogVLM
    CUSTOM = "custom"  # Custom model endpoint


class ComponentType(Enum):
    """UI component types that can be detected"""

    BUTTON = "button"
    INPUT = "input"
    TEXT = "text"
    IMAGE = "image"
    CARD = "card"
    MODAL = "modal"
    NAVBAR = "navbar"
    SIDEBAR = "sidebar"
    FOOTER = "footer"
    LIST = "list"
    TABLE = "table"
    FORM = "form"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    SLIDER = "slider"
    TABS = "tabs"
    ACCORDION = "accordion"
    CONTAINER = "container"
    GRID = "grid"
    ICON = "icon"
    UNKNOWN = "unknown"


class ImageFormat(Enum):
    """Supported image formats"""

    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    SVG = "svg"
    WEBP = "webp"


class CodeFramework(Enum):
    """Target code frameworks"""

    REACT = "react"
    VUE = "vue"
    SVELTE = "svelte"
    HTML = "html"
    TAILWIND = "tailwind_react"
    MUI = "material_ui"


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class BoundingBox:
    """Bounding box for component position"""

    x: int  # Left edge (pixels from left)
    y: int  # Top edge (pixels from top)
    width: int
    height: int

    @property
    def center(self) -> tuple[int, int]:
        """Get center point of bounding box"""
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def area(self) -> int:
        """Calculate area in pixels"""
        return self.width * self.height

    def contains_point(self, x: int, y: int) -> bool:
        """Check if point is inside bounding box"""
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)

    def to_dict(self) -> dict[str, int]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class UIComponent:
    """
    Detected UI component from mockup/screenshot.

    Represents a single UI element with position, type, and properties.
    """

    component_type: ComponentType
    position: BoundingBox
    properties: dict[str, Any] = field(default_factory=dict)

    # Visual properties
    text_content: str | None = None
    placeholder_text: str | None = None
    icon_name: str | None = None
    image_url: str | None = None

    # Styling hints
    colors: dict[str, str] = field(default_factory=dict)  # bg, fg, border, etc.
    font_size: str | None = None
    font_weight: str | None = None

    # Hierarchy
    parent_id: str | None = None
    children_ids: list[str] = field(default_factory=list)
    z_index: int = 0

    # Metadata
    confidence: float = 1.0  # Model confidence (0-1)
    component_id: str = ""
    semantic_label: str = ""  # Semantic meaning (e.g., "login button")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.component_id,
            "type": self.component_type.value,
            "position": self.position.to_dict(),
            "properties": self.properties,
            "text": self.text_content,
            "placeholder": self.placeholder_text,
            "icon": self.icon_name,
            "colors": self.colors,
            "confidence": self.confidence,
            "semantic_label": self.semantic_label,
            "parent": self.parent_id,
            "children": self.children_ids,
        }


@dataclass
class CodeTemplate:
    """Generated code from UI component"""

    framework: CodeFramework
    code: str
    component_id: str

    # Dependencies
    imports: list[str] = field(default_factory=list)
    dependencies: dict[str, str] = field(default_factory=dict)  # package: version

    # Additional files that might be needed
    css: str | None = None
    types: str | None = None  # TypeScript definitions

    # Metadata
    description: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "framework": self.framework.value,
            "code": self.code,
            "component_id": self.component_id,
            "imports": self.imports,
            "dependencies": self.dependencies,
            "css": self.css,
            "types": self.types,
            "description": self.description,
            "notes": self.notes,
        }


@dataclass
class ErrorInfo:
    """
    Extracted error information from screenshot.

    Analyzes error messages, stack traces, and context.
    """

    error_type: str  # Exception type or error code
    error_message: str

    # Stack trace information
    stack_trace: list[str] = field(default_factory=list)
    file_paths: list[str] = field(default_factory=list)
    line_numbers: list[int] = field(default_factory=list)

    # Context
    browser_console: bool = False
    terminal_output: bool = False
    application_error: bool = False

    # Diagnosis
    likely_cause: str = ""
    suggested_fixes: list[str] = field(default_factory=list)
    severity: str = "medium"  # low, medium, high, critical

    # Related code
    code_snippets: dict[str, str] = field(default_factory=dict)  # file: code

    # Metadata
    extracted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.error_type,
            "message": self.error_message,
            "stack_trace": self.stack_trace,
            "files": self.file_paths,
            "line_numbers": self.line_numbers,
            "context": {
                "browser": self.browser_console,
                "terminal": self.terminal_output,
                "application": self.application_error,
            },
            "diagnosis": {
                "cause": self.likely_cause,
                "fixes": self.suggested_fixes,
                "severity": self.severity,
            },
            "confidence": self.confidence,
            "extracted_at": self.extracted_at,
        }


@dataclass
class ArchitectureNode:
    """
    Node in an architecture diagram.

    Represents services, databases, APIs, etc.
    """

    node_id: str
    node_type: str  # service, database, api, frontend, cache, queue, etc.
    label: str
    position: BoundingBox

    # Technical details
    technology: str | None = None  # React, PostgreSQL, Redis, etc.
    description: str = ""

    # Connections
    connects_to: list[str] = field(default_factory=list)  # Node IDs
    connection_labels: dict[str, str] = field(default_factory=dict)  # target_id: label

    # Properties
    properties: dict[str, Any] = field(default_factory=dict)

    # Code generation hints
    suggested_structure: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "type": self.node_type,
            "label": self.label,
            "position": self.position.to_dict(),
            "technology": self.technology,
            "description": self.description,
            "connections": self.connects_to,
            "connection_labels": self.connection_labels,
            "properties": self.properties,
            "suggested_structure": self.suggested_structure,
        }


@dataclass
class ImageAnalysisResult:
    """
    Complete result from image analysis.

    Aggregates all information extracted from an image.
    """

    image_path: str
    image_format: ImageFormat
    analysis_type: str  # mockup, error, diagram, code, general

    # Image metadata
    width: int
    height: int
    file_size: int  # bytes

    # Analysis results
    description: str = ""
    ui_components: list[UIComponent] = field(default_factory=list)
    error_info: ErrorInfo | None = None
    architecture_nodes: list[ArchitectureNode] = field(default_factory=list)

    # Code generation
    generated_code: list[CodeTemplate] = field(default_factory=list)

    # Text extraction (OCR-like)
    extracted_text: str = ""
    code_blocks: list[dict[str, str]] = field(default_factory=list)  # lang, code

    # Model information
    model_provider: VisionModelProvider | None = None
    model_name: str = ""
    processing_time_ms: int = 0

    # Metadata
    analyzed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    confidence_score: float = 1.0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "image": {
                "path": self.image_path,
                "format": self.image_format.value,
                "width": self.width,
                "height": self.height,
                "size_bytes": self.file_size,
            },
            "analysis": {
                "type": self.analysis_type,
                "description": self.description,
                "confidence": self.confidence_score,
                "warnings": self.warnings,
            },
            "ui_components": [c.to_dict() for c in self.ui_components],
            "error_info": self.error_info.to_dict() if self.error_info else None,
            "architecture": [n.to_dict() for n in self.architecture_nodes],
            "generated_code": [c.to_dict() for c in self.generated_code],
            "extracted_text": self.extracted_text,
            "code_blocks": self.code_blocks,
            "model": {
                "provider": self.model_provider.value if self.model_provider else None,
                "name": self.model_name,
                "processing_time_ms": self.processing_time_ms,
            },
            "analyzed_at": self.analyzed_at,
        }


# ============================================================================
# Vision Model Protocol
# ============================================================================


class VisionModel(Protocol):
    """Protocol for vision model implementations"""

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        max_tokens: int = 2000,
    ) -> str:
        """
        Analyze an image with a prompt.

        Args:
            image_data: Raw image bytes
            prompt: Analysis prompt
            max_tokens: Maximum response tokens

        Returns:
            Model's text response
        """
        ...

    async def analyze_image_structured(
        self,
        image_data: bytes,
        prompt: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Get structured JSON response from image analysis.

        Args:
            image_data: Raw image bytes
            prompt: Analysis prompt
            response_schema: JSON schema for response

        Returns:
            Structured data matching schema
        """
        ...


# ============================================================================
# Vision Model Configuration
# ============================================================================


@dataclass
class VisionModelConfig:
    """Configuration for vision model"""

    provider: VisionModelProvider
    model_name: str

    # API configuration (for cloud models)
    api_key: str | None = None
    api_base: str | None = None

    # Local model configuration
    model_path: str | None = None
    device: str = "auto"  # auto, cpu, cuda, mps

    # Generation parameters
    max_tokens: int = 2000
    temperature: float = 0.7

    # Performance
    timeout_seconds: int = 60
    max_concurrent: int = 3

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider.value,
            "model_name": self.model_name,
            "api_base": self.api_base,
            "device": self.device,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }


# ============================================================================
# Vision Model Implementations
# ============================================================================


class BaseVisionModel(ABC):
    """Base class for vision model implementations"""

    def __init__(self, config: VisionModelConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        max_tokens: int = 2000,
    ) -> str:
        """Analyze image and return text response"""
        pass

    async def analyze_image_structured(
        self,
        image_data: bytes,
        prompt: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Get structured JSON response"""
        # Add schema to prompt
        schema_prompt = f"{prompt}\n\nRespond with valid JSON matching this schema:\n{json.dumps(response_schema, indent=2)}"

        response = await self.analyze_image(image_data, schema_prompt, max_tokens=2000)

        # Try to extract JSON from response
        try:
            # Look for JSON in markdown code blocks
            if "```json" in response:
                json_text = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_text = response.split("```")[1].split("```")[0].strip()
            else:
                json_text = response.strip()

            return json.loads(json_text)
        except (json.JSONDecodeError, IndexError) as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Model returned invalid JSON: {response[:200]}")

    def _encode_image_base64(self, image_data: bytes) -> str:
        """Encode image as base64"""
        return base64.b64encode(image_data).decode("utf-8")


class GPT4VisionModel(BaseVisionModel):
    """OpenAI GPT-4 Vision implementation"""

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        max_tokens: int = 2000,
    ) -> str:
        """Analyze image using GPT-4V"""
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx required for GPT-4V. Install: pip install httpx")

        if not self.config.api_key:
            raise ValueError("OpenAI API key required for GPT-4V")

        base64_image = self._encode_image_base64(image_data)

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.config.model_name or "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            "max_tokens": max_tokens,
            "temperature": self.config.temperature,
        }

        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.post(
                self.config.api_base or "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]


class ClaudeVisionModel(BaseVisionModel):
    """Anthropic Claude Vision implementation"""

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        max_tokens: int = 2000,
    ) -> str:
        """Analyze image using Claude Vision"""
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx required for Claude Vision. Install: pip install httpx")

        if not self.config.api_key:
            raise ValueError("Anthropic API key required for Claude Vision")

        base64_image = self._encode_image_base64(image_data)

        # Detect media type
        media_type = "image/jpeg"
        if image_data.startswith(b"\x89PNG"):
            media_type = "image/png"
        elif image_data.startswith(b"<svg"):
            media_type = "image/svg+xml"

        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.config.model_name or "claude-3-opus-20240229",
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "temperature": self.config.temperature,
        }

        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.post(
                self.config.api_base or "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            return result["content"][0]["text"]


class LLaVAModel(BaseVisionModel):
    """Local LLaVA model implementation"""

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        max_tokens: int = 2000,
    ) -> str:
        """Analyze image using local LLaVA model"""
        # This would integrate with a local LLaVA server or library
        # For now, provide integration point

        if not self.config.api_base:
            raise ValueError("LLaVA server endpoint required (api_base)")

        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx required for LLaVA. Install: pip install httpx")

        base64_image = self._encode_image_base64(image_data)

        # Standard LLaVA server API format
        payload = {
            "image": base64_image,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": self.config.temperature,
        }

        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            response = await client.post(
                f"{self.config.api_base}/analyze",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", result.get("text", ""))


# ============================================================================
# Visual Analyzer
# ============================================================================


class VisualAnalyzer:
    """
    Main visual understanding system.

    Provides high-level interface for image analysis tasks.
    """

    def __init__(
        self,
        model_config: VisionModelConfig | None = None,
        custom_model: VisionModel | None = None,
    ):
        """
        Initialize visual analyzer.

        Args:
            model_config: Configuration for vision model
            custom_model: Custom vision model implementation
        """
        self.logger = logging.getLogger(__name__)

        # Initialize vision model
        if custom_model:
            self.model = custom_model
        elif model_config:
            self.model = self._create_model(model_config)
        else:
            # Default to GPT-4V if available
            self.model = None
            self.logger.warning("No vision model configured")

        self.config = model_config

    def _create_model(self, config: VisionModelConfig) -> BaseVisionModel:
        """Create vision model from configuration"""
        if config.provider == VisionModelProvider.GPT4V:
            return GPT4VisionModel(config)
        elif config.provider == VisionModelProvider.CLAUDE:
            return ClaudeVisionModel(config)
        elif config.provider == VisionModelProvider.LLAVA:
            return LLaVAModel(config)
        else:
            raise ValueError(f"Unsupported provider: {config.provider}")

    def _load_image(self, image_path: str | Path) -> tuple[bytes, ImageFormat, dict[str, int]]:
        """
        Load image from file.

        Returns:
            (image_data, format, metadata)
        """
        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Detect format
        suffix = path.suffix.lower().lstrip(".")
        try:
            image_format = ImageFormat(suffix)
        except ValueError:
            raise ValueError(f"Unsupported image format: {suffix}")

        # Read image data
        image_data = path.read_bytes()

        # Get metadata
        metadata = {
            "file_size": len(image_data),
            "width": 0,
            "height": 0,
        }

        # Try to get dimensions (requires PIL)
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_data))
            metadata["width"] = img.width
            metadata["height"] = img.height
        except ImportError:
            self.logger.debug("PIL not available, skipping dimension detection")
        except Exception as e:
            self.logger.warning(f"Failed to get image dimensions: {e}")

        return image_data, image_format, metadata

    async def analyze_screenshot(
        self,
        image_path: str | Path,
        context: str = "",
    ) -> ImageAnalysisResult:
        """
        Analyze a screenshot for general understanding.

        Args:
            image_path: Path to screenshot
            context: Additional context about what we're looking for

        Returns:
            Analysis result with description and extracted information
        """
        if not self.model:
            raise RuntimeError("No vision model configured")

        start_time = datetime.utcnow()
        image_data, image_format, metadata = self._load_image(image_path)

        prompt = f"""Analyze this screenshot in detail.

Provide:
1. A clear description of what's shown
2. Any UI components visible
3. Any text content (exact text)
4. The purpose or context of this screen
5. Any notable visual elements

{f"Context: {context}" if context else ""}

Be specific and thorough."""

        response = await self.model.analyze_image(image_data, prompt)

        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return ImageAnalysisResult(
            image_path=str(image_path),
            image_format=image_format,
            analysis_type="screenshot",
            width=metadata["width"],
            height=metadata["height"],
            file_size=metadata["file_size"],
            description=response,
            extracted_text=response,  # Full response includes text
            model_provider=self.config.provider if self.config else None,
            model_name=self.config.model_name if self.config else "",
            processing_time_ms=processing_time,
        )

    async def mockup_to_code(
        self,
        image_path: str | Path,
        framework: CodeFramework = CodeFramework.REACT,
        additional_requirements: str = "",
    ) -> ImageAnalysisResult:
        """
        Convert UI mockup to code.

        Args:
            image_path: Path to mockup image
            framework: Target framework for code generation
            additional_requirements: Additional requirements or constraints

        Returns:
            Analysis result with UI components and generated code
        """
        if not self.model:
            raise RuntimeError("No vision model configured")

        start_time = datetime.utcnow()
        image_data, image_format, metadata = self._load_image(image_path)

        # Schema for structured response
        schema = {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "components": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "position": {
                                "type": "object",
                                "properties": {
                                    "x": {"type": "number"},
                                    "y": {"type": "number"},
                                    "width": {"type": "number"},
                                    "height": {"type": "number"},
                                },
                            },
                            "text": {"type": "string"},
                            "semantic_label": {"type": "string"},
                            "colors": {"type": "object"},
                        },
                    },
                },
                "code": {"type": "string"},
                "imports": {"type": "array", "items": {"type": "string"}},
                "css": {"type": "string"},
            },
        }

        prompt = f"""Analyze this UI mockup and generate {framework.value} code.

Task:
1. Identify all UI components (buttons, inputs, text, images, containers)
2. Determine their positions and relationships
3. Extract colors, fonts, and styling
4. Generate clean, production-ready {framework.value} code

Requirements:
- Use modern best practices for {framework.value}
- Include proper component hierarchy
- Add appropriate styling (CSS or Tailwind)
- Make it responsive if applicable
- Include semantic HTML/JSX
{f"- {additional_requirements}" if additional_requirements else ""}

Provide the analysis and code as structured JSON."""

        try:
            result = await self.model.analyze_image_structured(
                image_data, prompt, schema
            )
        except Exception as e:
            self.logger.error(f"Structured analysis failed, falling back to text: {e}")
            # Fallback to text response
            text_response = await self.model.analyze_image(image_data, prompt)
            result = {"description": text_response, "components": [], "code": ""}

        # Parse components
        ui_components = []
        for i, comp_data in enumerate(result.get("components", [])):
            pos = comp_data.get("position", {})
            component = UIComponent(
                component_type=ComponentType(comp_data.get("type", "unknown")),
                position=BoundingBox(
                    x=int(pos.get("x", 0)),
                    y=int(pos.get("y", 0)),
                    width=int(pos.get("width", 0)),
                    height=int(pos.get("height", 0)),
                ),
                text_content=comp_data.get("text"),
                colors=comp_data.get("colors", {}),
                semantic_label=comp_data.get("semantic_label", ""),
                component_id=f"comp_{i}",
            )
            ui_components.append(component)

        # Create code template
        code_template = CodeTemplate(
            framework=framework,
            code=result.get("code", ""),
            component_id="root",
            imports=result.get("imports", []),
            css=result.get("css"),
            description=result.get("description", ""),
        )

        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return ImageAnalysisResult(
            image_path=str(image_path),
            image_format=image_format,
            analysis_type="mockup",
            width=metadata["width"],
            height=metadata["height"],
            file_size=metadata["file_size"],
            description=result.get("description", ""),
            ui_components=ui_components,
            generated_code=[code_template],
            model_provider=self.config.provider if self.config else None,
            model_name=self.config.model_name if self.config else "",
            processing_time_ms=processing_time,
        )

    async def extract_error_info(
        self,
        image_path: str | Path,
        context: str = "",
    ) -> ImageAnalysisResult:
        """
        Extract error information from screenshot.

        Args:
            image_path: Path to error screenshot
            context: Additional context about the application

        Returns:
            Analysis result with error information and diagnosis
        """
        if not self.model:
            raise RuntimeError("No vision model configured")

        start_time = datetime.utcnow()
        image_data, image_format, metadata = self._load_image(image_path)

        schema = {
            "type": "object",
            "properties": {
                "error_type": {"type": "string"},
                "error_message": {"type": "string"},
                "stack_trace": {"type": "array", "items": {"type": "string"}},
                "file_paths": {"type": "array", "items": {"type": "string"}},
                "line_numbers": {"type": "array", "items": {"type": "number"}},
                "is_browser_console": {"type": "boolean"},
                "is_terminal": {"type": "boolean"},
                "likely_cause": {"type": "string"},
                "suggested_fixes": {"type": "array", "items": {"type": "string"}},
                "severity": {"type": "string"},
            },
        }

        prompt = f"""Analyze this error screenshot and extract all error information.

Extract:
1. Error type/name (e.g., TypeError, 404, SyntaxError)
2. Complete error message
3. Stack trace (all lines)
4. File paths and line numbers
5. Whether it's from browser console, terminal, or application UI

Then provide:
6. Likely cause of the error
7. Suggested fixes (step by step)
8. Severity (low, medium, high, critical)

{f"Context: {context}" if context else ""}

Be precise with file paths and line numbers. Provide actionable fixes."""

        try:
            result = await self.model.analyze_image_structured(
                image_data, prompt, schema
            )
        except Exception as e:
            self.logger.error(f"Structured error extraction failed: {e}")
            # Fallback
            text_response = await self.model.analyze_image(image_data, prompt)
            result = {
                "error_type": "Unknown",
                "error_message": text_response,
                "stack_trace": [],
                "file_paths": [],
                "line_numbers": [],
                "is_browser_console": False,
                "is_terminal": False,
                "likely_cause": "",
                "suggested_fixes": [],
                "severity": "medium",
            }

        error_info = ErrorInfo(
            error_type=result.get("error_type", "Unknown"),
            error_message=result.get("error_message", ""),
            stack_trace=result.get("stack_trace", []),
            file_paths=result.get("file_paths", []),
            line_numbers=result.get("line_numbers", []),
            browser_console=result.get("is_browser_console", False),
            terminal_output=result.get("is_terminal", False),
            application_error=not (result.get("is_browser_console") or result.get("is_terminal")),
            likely_cause=result.get("likely_cause", ""),
            suggested_fixes=result.get("suggested_fixes", []),
            severity=result.get("severity", "medium"),
        )

        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return ImageAnalysisResult(
            image_path=str(image_path),
            image_format=image_format,
            analysis_type="error",
            width=metadata["width"],
            height=metadata["height"],
            file_size=metadata["file_size"],
            description=f"Error: {error_info.error_message}",
            error_info=error_info,
            model_provider=self.config.provider if self.config else None,
            model_name=self.config.model_name if self.config else "",
            processing_time_ms=processing_time,
        )

    async def diagram_to_architecture(
        self,
        image_path: str | Path,
        context: str = "",
    ) -> ImageAnalysisResult:
        """
        Parse architecture diagram and extract structure.

        Args:
            image_path: Path to architecture diagram
            context: Additional context about the system

        Returns:
            Analysis result with architecture nodes and relationships
        """
        if not self.model:
            raise RuntimeError("No vision model configured")

        start_time = datetime.utcnow()
        image_data, image_format, metadata = self._load_image(image_path)

        schema = {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "nodes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "type": {"type": "string"},
                            "label": {"type": "string"},
                            "technology": {"type": "string"},
                            "description": {"type": "string"},
                            "connects_to": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                "suggested_structure": {"type": "object"},
            },
        }

        prompt = f"""Analyze this architecture diagram and extract the system structure.

Identify:
1. All nodes/components (services, databases, APIs, frontend, caches, queues)
2. Their types (e.g., "web server", "database", "API", "frontend")
3. Technologies used (e.g., "React", "PostgreSQL", "Redis")
4. Connections between components
5. Data flow and relationships

Then provide:
6. Overall system description
7. Suggested directory/file structure for implementation
8. Key architectural patterns used

{f"Context: {context}" if context else ""}

Be thorough in identifying all components and their relationships."""

        try:
            result = await self.model.analyze_image_structured(
                image_data, prompt, schema
            )
        except Exception as e:
            self.logger.error(f"Structured diagram parsing failed: {e}")
            # Fallback
            text_response = await self.model.analyze_image(image_data, prompt)
            result = {
                "description": text_response,
                "nodes": [],
                "suggested_structure": {},
            }

        # Parse architecture nodes
        arch_nodes = []
        for node_data in result.get("nodes", []):
            node = ArchitectureNode(
                node_id=node_data.get("id", ""),
                node_type=node_data.get("type", "service"),
                label=node_data.get("label", ""),
                position=BoundingBox(0, 0, 0, 0),  # Positions not critical for text diagrams
                technology=node_data.get("technology"),
                description=node_data.get("description", ""),
                connects_to=node_data.get("connects_to", []),
                suggested_structure=result.get("suggested_structure", {}),
            )
            arch_nodes.append(node)

        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return ImageAnalysisResult(
            image_path=str(image_path),
            image_format=image_format,
            analysis_type="diagram",
            width=metadata["width"],
            height=metadata["height"],
            file_size=metadata["file_size"],
            description=result.get("description", ""),
            architecture_nodes=arch_nodes,
            model_provider=self.config.provider if self.config else None,
            model_name=self.config.model_name if self.config else "",
            processing_time_ms=processing_time,
        )

    async def extract_code_from_image(
        self,
        image_path: str | Path,
        programming_language: str | None = None,
    ) -> ImageAnalysisResult:
        """
        Extract code from screenshot/image (OCR-like for code).

        Args:
            image_path: Path to image containing code
            programming_language: Expected language (helps with parsing)

        Returns:
            Analysis result with extracted code
        """
        if not self.model:
            raise RuntimeError("No vision model configured")

        start_time = datetime.utcnow()
        image_data, image_format, metadata = self._load_image(image_path)

        prompt = f"""Extract all code from this image.

Requirements:
1. Preserve exact formatting (indentation, spacing)
2. Maintain all comments
3. Include line numbers if visible
4. Identify the programming language(s)
5. Extract any text/documentation alongside code

{f"Expected language: {programming_language}" if programming_language else ""}

Provide the exact code as it appears in the image."""

        response = await self.model.analyze_image(image_data, prompt, max_tokens=3000)

        # Try to extract code blocks
        code_blocks = []
        if "```" in response:
            parts = response.split("```")
            for i in range(1, len(parts), 2):
                block = parts[i].strip()
                # First line might be language
                lines = block.split("\n", 1)
                lang = programming_language or "unknown"
                code = block
                if len(lines) > 1 and lines[0].strip().isalpha():
                    lang = lines[0].strip()
                    code = lines[1]
                code_blocks.append({"language": lang, "code": code})

        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return ImageAnalysisResult(
            image_path=str(image_path),
            image_format=image_format,
            analysis_type="code",
            width=metadata["width"],
            height=metadata["height"],
            file_size=metadata["file_size"],
            description="Code extraction",
            extracted_text=response,
            code_blocks=code_blocks,
            model_provider=self.config.provider if self.config else None,
            model_name=self.config.model_name if self.config else "",
            processing_time_ms=processing_time,
        )


# ============================================================================
# Singleton Factory
# ============================================================================


_visual_analyzer: VisualAnalyzer | None = None


def get_visual_analyzer(
    config: VisionModelConfig | None = None,
    force_new: bool = False,
) -> VisualAnalyzer:
    """
    Get or create visual analyzer instance.

    Args:
        config: Vision model configuration
        force_new: Force creation of new instance

    Returns:
        VisualAnalyzer instance
    """
    global _visual_analyzer

    if force_new or _visual_analyzer is None:
        _visual_analyzer = VisualAnalyzer(model_config=config)

    return _visual_analyzer
