# Visual Understanding System - Quick Start

## 5-Minute Setup

### 1. Set API Key
```bash
export OPENAI_API_KEY="sk-..."
# OR
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 2. Basic Usage
```python
from api.services.visual import get_visual_analyzer

# Auto-configure from environment
analyzer = get_visual_analyzer()

# Analyze screenshot
result = await analyzer.analyze_screenshot("/path/to/image.png")
print(result.description)
```

## Common Tasks

### Screenshot Analysis
```python
result = await analyzer.analyze_screenshot(
    image_path="screenshot.png",
    context="User dashboard from production"
)
print(result.description)
```

### Mockup to React Code
```python
from api.services.visual import CodeFramework

result = await analyzer.mockup_to_code(
    image_path="mockup.png",
    framework=CodeFramework.REACT,
    additional_requirements="Use Tailwind CSS"
)

code = result.generated_code[0].code
print(code)
```

### Error Diagnosis
```python
result = await analyzer.extract_error_info(
    image_path="error.png",
    context="React app in development"
)

error = result.error_info
print(f"Error: {error.error_message}")
print(f"Fixes: {error.suggested_fixes}")
```

### Architecture Diagram
```python
result = await analyzer.diagram_to_architecture(
    image_path="architecture.png",
    context="Microservices system"
)

for node in result.architecture_nodes:
    print(f"{node.label}: {node.technology}")
```

### Extract Code from Image
```python
result = await analyzer.extract_code_from_image(
    image_path="code-screenshot.png",
    programming_language="python"
)

for block in result.code_blocks:
    print(block['code'])
```

## HTTP API

### Analyze Screenshot
```bash
curl -X POST http://localhost:8000/api/visual/analyze-screenshot \
  -F "file=@screenshot.png" \
  -F "context=Production dashboard"
```

### Generate Code
```bash
curl -X POST http://localhost:8000/api/visual/mockup-to-code \
  -F "file=@mockup.png" \
  -F "framework=react" \
  -F "requirements=Use Tailwind CSS"
```

### Diagnose Error
```bash
curl -X POST http://localhost:8000/api/visual/diagnose-error \
  -F "file=@error.png" \
  -F "context=React application"
```

## Vision Models

### GPT-4V (OpenAI)
```python
from api.services.visual import VisionModelConfig, VisionModelProvider

config = VisionModelConfig(
    provider=VisionModelProvider.GPT4V,
    model_name="gpt-4-vision-preview",
    api_key="sk-...",
)
analyzer = get_visual_analyzer(config, force_new=True)
```

### Claude Vision (Anthropic)
```python
config = VisionModelConfig(
    provider=VisionModelProvider.CLAUDE,
    model_name="claude-3-opus-20240229",
    api_key="sk-ant-...",
)
analyzer = get_visual_analyzer(config, force_new=True)
```

### Local LLaVA
```python
config = VisionModelConfig(
    provider=VisionModelProvider.LLAVA,
    model_name="llava-v1.5-13b",
    api_base="http://localhost:8000",
)
analyzer = get_visual_analyzer(config, force_new=True)
```

## Data Models

### ImageAnalysisResult
```python
result.image_path          # Path to analyzed image
result.description         # Text description
result.ui_components       # List[UIComponent]
result.error_info          # ErrorInfo | None
result.architecture_nodes  # List[ArchitectureNode]
result.generated_code      # List[CodeTemplate]
result.code_blocks         # List[dict] - extracted code
result.processing_time_ms  # Processing duration
result.to_dict()           # Convert to dictionary
```

### UIComponent
```python
component.component_type   # ComponentType enum
component.position         # BoundingBox
component.text_content     # Text in component
component.colors           # Color dictionary
component.semantic_label   # Semantic meaning
```

### ErrorInfo
```python
error.error_type          # Error type/name
error.error_message       # Error message
error.stack_trace         # Stack trace lines
error.file_paths          # Affected files
error.likely_cause        # Diagnosis
error.suggested_fixes     # List of fixes
error.severity            # low/medium/high/critical
```

## Configuration

### From Environment
```python
from api.services.visual.config import get_service_config

config = get_service_config()  # Loads from env vars
```

### Presets
```python
from api.services.visual.config import (
    get_development_config,
    get_production_config,
    get_high_performance_config,
)

config = get_production_config()
```

## Testing

```bash
# Run tests
pytest apps/backend/tests/services/test_visual.py -v

# Check health
curl http://localhost:8000/api/visual/health
```

## Troubleshooting

**No API key error?**
```bash
export OPENAI_API_KEY="your-key"
```

**Import errors?**
```bash
pip install httpx pillow
```

**Rate limits?**
- Reduce `max_concurrent_requests`
- Add delays between requests
- Use caching

## Next Steps

1. See `README.md` for full documentation
2. Check `examples.py` for more examples
3. Read `INTEGRATION.md` for advanced usage
4. Review `test_visual.py` for patterns

## Support

- Documentation: See README.md
- Examples: See examples.py
- Tests: See test_visual.py
- Integration: See INTEGRATION.md

Happy coding!
