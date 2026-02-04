"""
FastAPI Integration for Visual Understanding System

Provides HTTP endpoints for visual analysis capabilities.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from .image_analyzer import (
    CodeFramework,
    VisionModelConfig,
    VisionModelProvider,
    get_visual_analyzer,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/visual",
    tags=["visual-understanding"],
)


# ============================================================================
# Helper Functions
# ============================================================================


def get_default_analyzer():
    """Get or create default visual analyzer"""
    # Try to configure from environment
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="No vision model configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY",
        )

    # Prefer GPT-4V if OpenAI key available
    if os.getenv("OPENAI_API_KEY"):
        provider = VisionModelProvider.GPT4V
        model_name = "gpt-4-vision-preview"
        api_key = os.getenv("OPENAI_API_KEY")
    else:
        provider = VisionModelProvider.CLAUDE
        model_name = "claude-3-opus-20240229"
        api_key = os.getenv("ANTHROPIC_API_KEY")

    config = VisionModelConfig(
        provider=provider,
        model_name=model_name,
        api_key=api_key,
        max_tokens=2500,
        temperature=0.7,
    )

    return get_visual_analyzer(config)


async def save_upload_temp(file: UploadFile) -> Path:
    """Save uploaded file to temporary location"""
    # Validate file extension
    allowed_extensions = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
    file_ext = Path(file.filename or "").suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {file_ext}. Allowed: {allowed_extensions}",
        )

    # Save to temp file
    suffix = file_ext or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        return Path(tmp.name)


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/analyze-screenshot")
async def analyze_screenshot(
    file: UploadFile = File(..., description="Screenshot image file"),
    context: str = Form("", description="Additional context about the screenshot"),
):
    """
    Analyze a screenshot for general understanding.

    Extracts:
    - Overall description
    - UI components visible
    - Text content
    - Purpose/context

    Supports: PNG, JPG, SVG
    """
    temp_path = None
    try:
        # Save uploaded file
        temp_path = await save_upload_temp(file)

        # Get analyzer
        analyzer = get_default_analyzer()

        # Analyze
        result = await analyzer.analyze_screenshot(
            image_path=temp_path,
            context=context,
        )

        return JSONResponse(content=result.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Screenshot analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        # Clean up temp file
        if temp_path and temp_path.exists():
            temp_path.unlink()


@router.post("/mockup-to-code")
async def mockup_to_code(
    file: UploadFile = File(..., description="UI mockup image"),
    framework: str = Form("react", description="Target framework (react, vue, svelte, html)"),
    requirements: str = Form("", description="Additional requirements (e.g., 'Use Tailwind CSS')"),
):
    """
    Convert UI mockup to production-ready code.

    Generates:
    - Component code in chosen framework
    - Styling (CSS/Tailwind)
    - Component hierarchy
    - Imports and dependencies

    Frameworks: react, vue, svelte, html, tailwind_react, material_ui
    """
    temp_path = None
    try:
        # Validate framework
        try:
            target_framework = CodeFramework(framework.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid framework: {framework}. Choose from: {[f.value for f in CodeFramework]}",
            )

        # Save uploaded file
        temp_path = await save_upload_temp(file)

        # Get analyzer
        analyzer = get_default_analyzer()

        # Generate code
        result = await analyzer.mockup_to_code(
            image_path=temp_path,
            framework=target_framework,
            additional_requirements=requirements,
        )

        return JSONResponse(content=result.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mockup to code failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Code generation failed: {str(e)}")
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


@router.post("/diagnose-error")
async def diagnose_error(
    file: UploadFile = File(..., description="Error screenshot"),
    context: str = Form("", description="Application context (e.g., 'React dev server')"),
):
    """
    Diagnose error from screenshot.

    Extracts:
    - Error type and message
    - Stack trace
    - File paths and line numbers
    - Likely cause
    - Suggested fixes
    - Severity

    Handles: Browser console, terminal output, application errors
    """
    temp_path = None
    try:
        # Save uploaded file
        temp_path = await save_upload_temp(file)

        # Get analyzer
        analyzer = get_default_analyzer()

        # Extract error info
        result = await analyzer.extract_error_info(
            image_path=temp_path,
            context=context,
        )

        return JSONResponse(content=result.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error diagnosis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Diagnosis failed: {str(e)}")
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


@router.post("/parse-architecture")
async def parse_architecture(
    file: UploadFile = File(..., description="Architecture diagram"),
    context: str = Form("", description="System context (e.g., 'Microservices e-commerce')"),
):
    """
    Parse architecture diagram and extract system structure.

    Identifies:
    - Services, databases, APIs, caches
    - Technologies used
    - Connections and data flow
    - Architectural patterns
    - Suggested code structure

    Supports: Hand-drawn diagrams, tool-generated diagrams
    """
    temp_path = None
    try:
        # Save uploaded file
        temp_path = await save_upload_temp(file)

        # Get analyzer
        analyzer = get_default_analyzer()

        # Parse diagram
        result = await analyzer.diagram_to_architecture(
            image_path=temp_path,
            context=context,
        )

        return JSONResponse(content=result.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Architecture parsing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


@router.post("/extract-code")
async def extract_code(
    file: UploadFile = File(..., description="Screenshot containing code"),
    language: str = Form("", description="Expected programming language (optional)"),
):
    """
    Extract code from screenshot (OCR-like for code).

    Extracts:
    - Complete code with formatting
    - Programming language(s)
    - Comments and documentation
    - Multiple code blocks if present

    Preserves: Indentation, spacing, line structure
    """
    temp_path = None
    try:
        # Save uploaded file
        temp_path = await save_upload_temp(file)

        # Get analyzer
        analyzer = get_default_analyzer()

        # Extract code
        result = await analyzer.extract_code_from_image(
            image_path=temp_path,
            programming_language=language or None,
        )

        return JSONResponse(content=result.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Code extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


@router.get("/health")
async def health_check():
    """
    Check if visual understanding service is available.

    Returns model configuration and status.
    """
    try:
        # Check if any API keys are configured
        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

        if not (has_openai or has_anthropic):
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unavailable",
                    "message": "No vision model API keys configured",
                    "providers": {
                        "gpt4v": False,
                        "claude": False,
                    },
                },
            )

        # Try to create analyzer
        analyzer = get_default_analyzer()

        return JSONResponse(
            content={
                "status": "available",
                "providers": {
                    "gpt4v": has_openai,
                    "claude": has_anthropic,
                },
                "active_provider": analyzer.config.provider.value if analyzer.config else None,
                "active_model": analyzer.config.model_name if analyzer.config else None,
            }
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": str(e),
            },
        )


@router.get("/supported-formats")
async def supported_formats():
    """Get supported image formats and frameworks"""
    return JSONResponse(
        content={
            "image_formats": ["png", "jpg", "jpeg", "svg", "webp"],
            "frameworks": [f.value for f in CodeFramework],
            "analysis_types": [
                "screenshot",
                "mockup",
                "error",
                "diagram",
                "code",
            ],
            "model_providers": [p.value for p in VisionModelProvider],
        }
    )


# ============================================================================
# Example curl commands
# ============================================================================

"""
Example API Usage:

1. Analyze Screenshot:
```bash
curl -X POST http://localhost:8000/api/visual/analyze-screenshot \
  -F "file=@screenshot.png" \
  -F "context=User dashboard showing metrics"
```

2. Convert Mockup to Code:
```bash
curl -X POST http://localhost:8000/api/visual/mockup-to-code \
  -F "file=@mockup.png" \
  -F "framework=react" \
  -F "requirements=Use Tailwind CSS and make it responsive"
```

3. Diagnose Error:
```bash
curl -X POST http://localhost:8000/api/visual/diagnose-error \
  -F "file=@error.png" \
  -F "context=React application in development"
```

4. Parse Architecture Diagram:
```bash
curl -X POST http://localhost:8000/api/visual/parse-architecture \
  -F "file=@diagram.png" \
  -F "context=Microservices architecture"
```

5. Extract Code:
```bash
curl -X POST http://localhost:8000/api/visual/extract-code \
  -F "file=@code-screenshot.png" \
  -F "language=python"
```

6. Health Check:
```bash
curl http://localhost:8000/api/visual/health
```

7. Supported Formats:
```bash
curl http://localhost:8000/api/visual/supported-formats
```
"""
