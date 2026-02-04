# Visual Understanding System - Integration Guide

Complete guide for integrating the visual understanding system into MagnetarCode.

## Quick Start

### 1. Install Dependencies

The visual system uses dependencies already in `requirements.txt`:
- `httpx` - For API calls to cloud vision models
- `Pillow` (optional) - For image metadata extraction

```bash
pip install httpx pillow
```

### 2. Configure API Keys

Set environment variables for your chosen vision model:

```bash
# Option 1: OpenAI GPT-4V (Recommended)
export OPENAI_API_KEY="sk-..."

# Option 2: Anthropic Claude Vision
export ANTHROPIC_API_KEY="sk-ant-..."

# Option 3: Local LLaVA Server
export LLAVA_ENDPOINT="http://localhost:8000"
```

### 3. Basic Usage

```python
from api.services.visual import get_visual_analyzer, VisionModelConfig, VisionModelProvider

# Auto-configure from environment
analyzer = get_visual_analyzer()

# Or configure manually
config = VisionModelConfig(
    provider=VisionModelProvider.GPT4V,
    model_name="gpt-4-vision-preview",
    api_key="your-key",
)
analyzer = get_visual_analyzer(config)

# Analyze an image
result = await analyzer.analyze_screenshot("/path/to/screenshot.png")
print(result.description)
```

## Integration Points

### 1. FastAPI Endpoints

Add the visual API router to your FastAPI application:

```python
# In your main.py or app.py
from api.services.visual.api_integration import router as visual_router

app = FastAPI()
app.include_router(visual_router)
```

Now you have these endpoints:
- `POST /api/visual/analyze-screenshot`
- `POST /api/visual/mockup-to-code`
- `POST /api/visual/diagnose-error`
- `POST /api/visual/parse-architecture`
- `POST /api/visual/extract-code`
- `GET /api/visual/health`

### 2. Agent Integration

Integrate with MagnetarCode's agent system:

```python
# In agent_executor.py or agent tools
from api.services.visual import get_visual_analyzer

class VisualAnalysisTool:
    """Agent tool for visual understanding"""

    async def analyze_screenshot(self, image_path: str, context: str = "") -> dict:
        """Analyze screenshot for agent"""
        analyzer = get_visual_analyzer()
        result = await analyzer.analyze_screenshot(image_path, context)
        return result.to_dict()

    async def mockup_to_code(self, image_path: str, framework: str = "react") -> dict:
        """Generate code from mockup"""
        from api.services.visual import CodeFramework
        analyzer = get_visual_analyzer()
        result = await analyzer.mockup_to_code(
            image_path,
            framework=CodeFramework(framework),
        )
        return result.to_dict()

    async def diagnose_error(self, image_path: str, context: str = "") -> dict:
        """Diagnose error from screenshot"""
        analyzer = get_visual_analyzer()
        result = await analyzer.extract_error_info(image_path, context)
        return result.to_dict()
```

### 3. Chat Memory Integration

Store visual analysis results in chat memory:

```python
from api.services.chat_memory import get_memory_manager
from api.services.visual import get_visual_analyzer

async def analyze_and_store(session_id: str, image_path: str):
    """Analyze image and store in memory"""
    # Analyze
    analyzer = get_visual_analyzer()
    result = await analyzer.analyze_screenshot(image_path)

    # Store in memory
    memory = get_memory_manager()
    await memory.add_message(
        session_id=session_id,
        role="system",
        content=f"Visual analysis: {result.description}",
        metadata={
            "type": "visual_analysis",
            "image_path": image_path,
            "analysis_type": result.analysis_type,
            "confidence": result.confidence_score,
        },
    )

    return result
```

### 4. Code Editor Integration

Insert generated code into files:

```python
from api.services.visual import get_visual_analyzer, CodeFramework
from pathlib import Path

async def mockup_to_component_file(
    mockup_path: str,
    output_path: Path,
    framework: CodeFramework = CodeFramework.REACT,
):
    """Generate component from mockup and save to file"""
    analyzer = get_visual_analyzer()

    result = await analyzer.mockup_to_code(mockup_path, framework)

    if result.generated_code:
        template = result.generated_code[0]

        # Write component file
        with open(output_path, "w") as f:
            # Add imports
            if template.imports:
                f.write("\n".join(template.imports))
                f.write("\n\n")

            # Add main code
            f.write(template.code)

        # Write CSS if present
        if template.css:
            css_path = output_path.with_suffix(".css")
            with open(css_path, "w") as f:
                f.write(template.css)

        return output_path

    return None
```

### 5. Error Tracking Integration

Automatically diagnose errors from screenshots:

```python
from api.services.visual import get_visual_analyzer

async def auto_diagnose_error_screenshot(screenshot_path: str, context: str):
    """Auto-diagnose error and provide fixes"""
    analyzer = get_visual_analyzer()
    result = await analyzer.extract_error_info(screenshot_path, context)

    if result.error_info:
        error = result.error_info

        # Log the error
        logger.error(
            f"Error detected: {error.error_type}",
            extra={
                "message": error.error_message,
                "files": error.file_paths,
                "severity": error.severity,
            },
        )

        # Return actionable fixes
        return {
            "error": error.error_message,
            "cause": error.likely_cause,
            "fixes": error.suggested_fixes,
            "severity": error.severity,
            "files": list(zip(error.file_paths, error.line_numbers)),
        }

    return None
```

## Advanced Integration

### Custom Vision Model

Integrate your own vision model:

```python
from api.services.visual.image_analyzer import BaseVisionModel, VisionModelConfig

class CustomVisionModel(BaseVisionModel):
    """Custom vision model implementation"""

    def __init__(self, config: VisionModelConfig):
        super().__init__(config)
        # Initialize your model here
        self.model = load_your_model(config.model_path)

    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        max_tokens: int = 2000,
    ) -> str:
        # Your implementation
        result = await self.model.process(image_data, prompt)
        return result.text

# Use it
from api.services.visual import VisualAnalyzer

config = VisionModelConfig(
    provider=VisionModelProvider.CUSTOM,
    model_name="your-model",
    model_path="/path/to/model",
)

custom_model = CustomVisionModel(config)
analyzer = VisualAnalyzer(custom_model=custom_model)
```

### Result Caching

Add caching for expensive vision API calls:

```python
import hashlib
from functools import lru_cache
from api.services.visual import get_visual_analyzer

# Simple in-memory cache
@lru_cache(maxsize=100)
def get_image_hash(image_path: str) -> str:
    """Get hash of image for cache key"""
    with open(image_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

# Redis cache (better for production)
from api.services.cache_service import get_cache

async def analyze_with_cache(image_path: str, context: str = ""):
    """Analyze image with Redis caching"""
    cache = get_cache()
    cache_key = f"visual:{get_image_hash(image_path)}:{context}"

    # Check cache
    cached = await cache.get(cache_key)
    if cached:
        return cached

    # Analyze
    analyzer = get_visual_analyzer()
    result = await analyzer.analyze_screenshot(image_path, context)

    # Store in cache (1 hour TTL)
    await cache.set(cache_key, result.to_dict(), ttl=3600)

    return result.to_dict()
```

### Batch Processing

Process multiple images efficiently:

```python
import asyncio
from pathlib import Path
from api.services.visual import get_visual_analyzer

async def batch_analyze_screenshots(image_dir: Path, concurrency: int = 3):
    """Analyze multiple screenshots with controlled concurrency"""
    analyzer = get_visual_analyzer()

    image_paths = list(image_dir.glob("*.png"))
    semaphore = asyncio.Semaphore(concurrency)

    async def analyze_one(path: Path):
        async with semaphore:
            try:
                result = await analyzer.analyze_screenshot(str(path))
                return {"path": str(path), "result": result.to_dict(), "error": None}
            except Exception as e:
                return {"path": str(path), "result": None, "error": str(e)}

    results = await asyncio.gather(*[analyze_one(p) for p in image_paths])
    return results
```

### WebSocket Streaming

Stream analysis progress via WebSocket:

```python
from fastapi import WebSocket
from api.services.visual import get_visual_analyzer

async def stream_analysis(websocket: WebSocket, image_path: str):
    """Stream analysis progress to client"""
    await websocket.accept()

    try:
        await websocket.send_json({"status": "starting", "progress": 0})

        analyzer = get_visual_analyzer()

        await websocket.send_json({"status": "analyzing", "progress": 50})

        result = await analyzer.analyze_screenshot(image_path)

        await websocket.send_json({
            "status": "complete",
            "progress": 100,
            "result": result.to_dict(),
        })

    except Exception as e:
        await websocket.send_json({"status": "error", "error": str(e)})
    finally:
        await websocket.close()
```

## Configuration Management

### Environment-based Configuration

```python
# .env file
OPENAI_API_KEY=sk-...
VISUAL_MAX_IMAGE_SIZE_MB=15
VISUAL_MAX_CONCURRENT=5
VISUAL_ENABLE_CACHE=true
VISUAL_DEFAULT_FRAMEWORK=react
VISUAL_INCLUDE_TYPESCRIPT=true

# Load in app
from api.services.visual.config import get_service_config

config = get_service_config()
print(config.to_dict())
```

### Preset Configurations

```python
from api.services.visual.config import (
    get_development_config,
    get_production_config,
    get_high_performance_config,
    set_service_config,
)

# Development
if os.getenv("ENV") == "development":
    set_service_config(get_development_config())

# Production
elif os.getenv("ENV") == "production":
    set_service_config(get_production_config())

# High-performance batch processing
elif os.getenv("ENV") == "batch":
    set_service_config(get_high_performance_config())
```

## Testing

### Unit Tests

```bash
# Run visual service tests
pytest apps/backend/tests/services/test_visual.py -v

# Run with coverage
pytest apps/backend/tests/services/test_visual.py --cov=api.services.visual

# Run only integration tests
pytest apps/backend/tests/services/test_visual.py -v -m integration
```

### Manual Testing

```python
# Test with real image
import asyncio
from api.services.visual import get_visual_analyzer, VisionModelConfig, VisionModelProvider

async def test():
    config = VisionModelConfig(
        provider=VisionModelProvider.GPT4V,
        model_name="gpt-4-vision-preview",
        api_key="your-key",
    )

    analyzer = get_visual_analyzer(config, force_new=True)

    result = await analyzer.analyze_screenshot(
        "/path/to/test-image.png",
        context="Testing visual analysis"
    )

    print(f"Success! Description: {result.description}")

asyncio.run(test())
```

## Monitoring

### Performance Metrics

```python
import time
from api.services.visual import get_visual_analyzer

async def analyze_with_metrics(image_path: str):
    """Analyze with performance tracking"""
    start_time = time.time()

    analyzer = get_visual_analyzer()
    result = await analyzer.analyze_screenshot(image_path)

    duration = time.time() - start_time

    # Log metrics
    logger.info(
        "Visual analysis complete",
        extra={
            "duration_seconds": duration,
            "model_processing_ms": result.processing_time_ms,
            "image_size_bytes": result.file_size,
            "confidence": result.confidence_score,
            "model": result.model_name,
        },
    )

    return result
```

### Error Tracking

```python
from api.services.visual import get_visual_analyzer

async def analyze_with_error_tracking(image_path: str):
    """Analyze with error tracking"""
    try:
        analyzer = get_visual_analyzer()
        result = await analyzer.analyze_screenshot(image_path)
        return result
    except FileNotFoundError as e:
        logger.error(f"Image not found: {image_path}")
        raise
    except ValueError as e:
        logger.error(f"Invalid configuration: {e}")
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        # Send to error tracking service (Sentry, etc.)
        raise
```

## Production Deployment

### Environment Setup

```bash
# Production .env
OPENAI_API_KEY=sk-prod-...
VISUAL_MAX_IMAGE_SIZE_MB=10
VISUAL_MAX_CONCURRENT=10
VISUAL_ENABLE_CACHE=true
VISUAL_CACHE_TTL=3600
```

### Docker Configuration

```dockerfile
# Add to Dockerfile
RUN pip install httpx pillow

# Environment variables
ENV OPENAI_API_KEY=${OPENAI_API_KEY}
ENV VISUAL_MAX_CONCURRENT=10
ENV VISUAL_ENABLE_CACHE=true
```

### Health Checks

```python
# Add to health check endpoint
from api.services.visual.api_integration import router

app.include_router(router)

# Check at: GET /api/visual/health
```

## Best Practices

1. **Always provide context** - More context = better results
2. **Use caching** - Vision API calls are expensive
3. **Handle errors gracefully** - Models can fail
4. **Validate outputs** - Don't trust generated code blindly
5. **Monitor costs** - Track API usage
6. **Use appropriate models** - GPT-4V for code, Claude for analysis
7. **Batch when possible** - More efficient for multiple images
8. **Set timeouts** - Prevent hanging requests
9. **Log everything** - Track performance and errors
10. **Test thoroughly** - Vision models are probabilistic

## Troubleshooting

### Common Issues

**"No vision model configured"**
- Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`

**"API key required"**
- Check environment variable is set correctly

**"Unsupported image format"**
- Use PNG, JPG, or SVG
- Check file extension

**"Analysis failed"**
- Check image file exists and is readable
- Verify API key is valid
- Check rate limits

**"Invalid JSON response"**
- Model returned unstructured data
- Fallback to text analysis

### Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Analyze with verbose output
from api.services.visual import get_visual_analyzer

analyzer = get_visual_analyzer()
result = await analyzer.analyze_screenshot("/path/to/image.png")
```

## Support

For issues or questions:
1. Check the README.md for examples
2. Review test_visual.py for usage patterns
3. See examples.py for comprehensive examples
4. Open an issue on GitHub

## Next Steps

1. Set up API keys
2. Test with sample images
3. Integrate into your workflow
4. Monitor performance
5. Iterate and improve

Happy visual understanding!
