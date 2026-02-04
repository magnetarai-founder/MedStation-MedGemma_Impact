# Visual Understanding System

Production-grade visual analysis system for MagnetarCode that provides comprehensive image understanding capabilities.

## Features

### 1. Screenshot Analysis
- General purpose screenshot understanding
- UI component detection
- Text extraction
- Context-aware analysis

### 2. UI Mockup to Code Conversion
- Detects UI components (buttons, inputs, forms, etc.)
- Extracts positioning and layout
- Generates production-ready code in multiple frameworks:
  - React
  - Vue
  - Svelte
  - HTML/Tailwind
  - Material-UI
- Includes styling (CSS/Tailwind)
- Provides component hierarchy

### 3. Error Screenshot Diagnosis
- Extracts error messages and types
- Parses stack traces
- Identifies file paths and line numbers
- Detects error context (browser console, terminal, UI)
- Provides diagnosis and suggested fixes
- Assigns severity levels

### 4. Architecture Diagram Understanding
- Identifies system components (services, databases, APIs)
- Extracts technology stack
- Maps connections and data flow
- Suggests code structure
- Identifies architectural patterns

### 5. Code Extraction from Images
- OCR-like extraction of code from screenshots
- Preserves formatting and indentation
- Identifies programming languages
- Extracts comments and documentation

## Supported Vision Models

### Cloud Models
- **GPT-4 Vision** (OpenAI) - High quality, API-based
- **Claude Vision** (Anthropic) - Excellent for code understanding
- **Gemini Vision** (Google) - Fast and accurate

### Local Models
- **LLaVA** - Open-source, runs locally
- **Qwen-VL** - Strong code understanding
- **CogVLM** - General purpose vision

### Custom Models
- Support for custom vision model endpoints
- Implement `VisionModel` protocol for custom integrations

## Installation

### Dependencies
```bash
# Core dependencies (already in requirements.txt)
pip install httpx pillow

# Optional: For local models
pip install transformers torch

# Optional: For image processing
pip install opencv-python
```

### API Keys
Set environment variables for cloud models:
```bash
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"
```

## Usage Examples

### Basic Screenshot Analysis

```python
from api.services.visual import (
    VisualAnalyzer,
    VisionModelConfig,
    VisionModelProvider,
    get_visual_analyzer,
)

# Configure vision model
config = VisionModelConfig(
    provider=VisionModelProvider.GPT4V,
    model_name="gpt-4-vision-preview",
    api_key=os.getenv("OPENAI_API_KEY"),
    max_tokens=2000,
    temperature=0.7,
)

# Get analyzer instance
analyzer = get_visual_analyzer(config)

# Analyze screenshot
result = await analyzer.analyze_screenshot(
    image_path="/path/to/screenshot.png",
    context="This is a user dashboard from our app"
)

print(result.description)
print(f"Processing time: {result.processing_time_ms}ms")
```

### UI Mockup to Code

```python
from api.services.visual import CodeFramework

# Convert mockup to React code
result = await analyzer.mockup_to_code(
    image_path="/path/to/mockup.png",
    framework=CodeFramework.REACT,
    additional_requirements="Use Tailwind CSS for styling, make it responsive"
)

# Access generated code
for code_template in result.generated_code:
    print(f"Framework: {code_template.framework.value}")
    print(f"Code:\n{code_template.code}")
    print(f"Imports: {code_template.imports}")
    if code_template.css:
        print(f"CSS:\n{code_template.css}")

# Access detected components
for component in result.ui_components:
    print(f"Component: {component.component_type.value}")
    print(f"Position: {component.position.to_dict()}")
    print(f"Text: {component.text_content}")
    print(f"Colors: {component.colors}")
```

### Error Diagnosis

```python
# Analyze error screenshot
result = await analyzer.extract_error_info(
    image_path="/path/to/error.png",
    context="React application running in development mode"
)

if result.error_info:
    error = result.error_info
    print(f"Error Type: {error.error_type}")
    print(f"Message: {error.error_message}")
    print(f"Severity: {error.severity}")

    print("\nStack Trace:")
    for line in error.stack_trace:
        print(f"  {line}")

    print(f"\nFiles: {error.file_paths}")
    print(f"Lines: {error.line_numbers}")

    print(f"\nLikely Cause: {error.likely_cause}")
    print("\nSuggested Fixes:")
    for i, fix in enumerate(error.suggested_fixes, 1):
        print(f"{i}. {fix}")
```

### Architecture Diagram Analysis

```python
# Parse architecture diagram
result = await analyzer.diagram_to_architecture(
    image_path="/path/to/diagram.png",
    context="Microservices architecture for e-commerce platform"
)

print(f"Description: {result.description}")

# Iterate over nodes
for node in result.architecture_nodes:
    print(f"\nNode: {node.label}")
    print(f"Type: {node.node_type}")
    print(f"Technology: {node.technology}")
    print(f"Connects to: {node.connects_to}")
    print(f"Description: {node.description}")

# Get suggested structure
if result.architecture_nodes:
    structure = result.architecture_nodes[0].suggested_structure
    print(f"\nSuggested Structure: {structure}")
```

### Code Extraction

```python
# Extract code from image
result = await analyzer.extract_code_from_image(
    image_path="/path/to/code-screenshot.png",
    programming_language="python"
)

print(f"Extracted Text:\n{result.extracted_text}")

# Access code blocks
for block in result.code_blocks:
    print(f"\nLanguage: {block['language']}")
    print(f"Code:\n{block['code']}")
```

### Using Local Models (LLaVA)

```python
# Configure for local LLaVA server
config = VisionModelConfig(
    provider=VisionModelProvider.LLAVA,
    model_name="llava-v1.5-13b",
    api_base="http://localhost:8000",  # Your LLaVA server
    device="cuda",  # or "cpu", "mps"
    max_tokens=2000,
)

analyzer = get_visual_analyzer(config)

# Use same API as cloud models
result = await analyzer.analyze_screenshot("/path/to/image.png")
```

### Using Claude Vision

```python
config = VisionModelConfig(
    provider=VisionModelProvider.CLAUDE,
    model_name="claude-3-opus-20240229",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_tokens=2000,
)

analyzer = get_visual_analyzer(config)

# Claude excels at code understanding
result = await analyzer.extract_code_from_image(
    "/path/to/code.png",
    programming_language="python"
)
```

### Custom Vision Model Integration

```python
from api.services.visual.image_analyzer import BaseVisionModel

class CustomVisionModel(BaseVisionModel):
    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str,
        max_tokens: int = 2000,
    ) -> str:
        # Your custom implementation
        # Send to your model endpoint
        # Return text response
        pass

# Use custom model
custom_model = CustomVisionModel(config)
analyzer = VisualAnalyzer(custom_model=custom_model)
```

## API Integration

### FastAPI Endpoint Example

```python
from fastapi import APIRouter, File, UploadFile, HTTPException
from api.services.visual import get_visual_analyzer, CodeFramework

router = APIRouter(prefix="/visual", tags=["visual"])

@router.post("/analyze-screenshot")
async def analyze_screenshot_endpoint(
    file: UploadFile = File(...),
    context: str = "",
):
    """Analyze a screenshot"""
    try:
        # Save uploaded file temporarily
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        # Analyze
        analyzer = get_visual_analyzer()
        result = await analyzer.analyze_screenshot(temp_path, context)

        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mockup-to-code")
async def mockup_to_code_endpoint(
    file: UploadFile = File(...),
    framework: str = "react",
    requirements: str = "",
):
    """Convert UI mockup to code"""
    try:
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        analyzer = get_visual_analyzer()
        result = await analyzer.mockup_to_code(
            temp_path,
            framework=CodeFramework(framework),
            additional_requirements=requirements,
        )

        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/diagnose-error")
async def diagnose_error_endpoint(
    file: UploadFile = File(...),
    context: str = "",
):
    """Diagnose error from screenshot"""
    try:
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        analyzer = get_visual_analyzer()
        result = await analyzer.extract_error_info(temp_path, context)

        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Data Models

### ImageAnalysisResult
Main result container with:
- Image metadata (path, format, dimensions, size)
- Analysis type (mockup, error, diagram, code, screenshot)
- Description and extracted text
- UI components (for mockups)
- Error information (for errors)
- Architecture nodes (for diagrams)
- Generated code
- Model information and timing

### UIComponent
Detected UI component with:
- Type (button, input, text, etc.)
- Position (bounding box)
- Visual properties (colors, fonts)
- Content (text, placeholder, icon)
- Hierarchy (parent, children)
- Semantic label

### ErrorInfo
Error information with:
- Error type and message
- Stack trace
- File paths and line numbers
- Context (browser/terminal/UI)
- Diagnosis (cause, fixes, severity)

### ArchitectureNode
Architecture diagram node with:
- Node type (service, database, API, etc.)
- Label and technology
- Connections to other nodes
- Description
- Suggested code structure

### CodeTemplate
Generated code with:
- Target framework
- Code content
- Imports and dependencies
- CSS/styling
- TypeScript definitions
- Documentation

## Performance Considerations

### Model Selection
- **Cloud models** (GPT-4V, Claude): Higher quality, API latency (~2-5s)
- **Local models** (LLaVA): Lower latency, requires GPU, variable quality

### Image Size
- Recommended: 1920x1080 or smaller
- Large images (4K+) may be downscaled
- PNG recommended for screenshots (preserves text clarity)
- JPG acceptable for photos/mockups

### Token Limits
- Adjust `max_tokens` based on expected response size
- Mockup-to-code: 2000-3000 tokens
- Simple screenshot: 500-1000 tokens
- Architecture diagrams: 1500-2500 tokens

### Caching
Consider caching results for identical images:
```python
# Use hash of image as cache key
import hashlib

def get_image_hash(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
```

## Error Handling

```python
from api.services.visual import VisualAnalyzer

try:
    result = await analyzer.analyze_screenshot("/path/to/image.png")
except FileNotFoundError:
    # Image file not found
    pass
except ValueError as e:
    # Unsupported format or invalid configuration
    print(f"Configuration error: {e}")
except RuntimeError as e:
    # Model not configured or not available
    print(f"Runtime error: {e}")
except Exception as e:
    # API errors, network issues, etc.
    print(f"Analysis failed: {e}")
```

## Best Practices

1. **Provide Context**: Always include relevant context for better analysis
2. **Choose Right Model**: Use GPT-4V/Claude for code, LLaVA for speed
3. **Validate Outputs**: Vision models can hallucinate - validate generated code
4. **Iterate Prompts**: Refine additional requirements for better results
5. **Handle Errors Gracefully**: Vision analysis can fail - have fallbacks
6. **Monitor Costs**: Cloud APIs charge per image - track usage
7. **Optimize Images**: Smaller, clear images process faster and cheaper

## Limitations

- Vision models are not perfect - expect ~85-95% accuracy
- Generated code may need manual refinement
- Complex diagrams might miss some connections
- OCR accuracy depends on image quality
- Stack trace extraction requires clear, readable screenshots
- Model hallucinations possible - validate outputs

## Future Enhancements

- [ ] Video frame analysis
- [ ] Multi-image comparison
- [ ] Interactive component detection (bounding box annotations)
- [ ] Style guide extraction from designs
- [ ] Accessibility analysis (contrast, labels, etc.)
- [ ] Figma/Sketch file support
- [ ] Real-time screenshot feedback
- [ ] Design system component matching

## Integration with MagnetarCode

This visual understanding system integrates with:
- **Agent Executor**: Visual debugging and UI generation
- **Chat Memory**: Store and reference visual analysis
- **Code Editor**: Insert generated code from mockups
- **Error Tracking**: Automatic error diagnosis from screenshots
- **Documentation**: Generate docs from architecture diagrams

## License

Part of MagnetarCode - see project license.
