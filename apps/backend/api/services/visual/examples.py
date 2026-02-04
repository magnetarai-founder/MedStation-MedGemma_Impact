"""
Visual Understanding System - Usage Examples

Demonstrates all features of the visual understanding system.
"""

import asyncio
import os
from pathlib import Path

from .image_analyzer import (
    CodeFramework,
    VisionModelConfig,
    VisionModelProvider,
    get_visual_analyzer,
)


async def example_screenshot_analysis():
    """Example: Analyze a general screenshot"""
    print("\n=== Screenshot Analysis Example ===\n")

    # Configure GPT-4V
    config = VisionModelConfig(
        provider=VisionModelProvider.GPT4V,
        model_name="gpt-4-vision-preview",
        api_key=os.getenv("OPENAI_API_KEY"),
        max_tokens=1500,
        temperature=0.7,
    )

    analyzer = get_visual_analyzer(config)

    # Analyze screenshot
    result = await analyzer.analyze_screenshot(
        image_path="/path/to/screenshot.png",
        context="User dashboard showing analytics and metrics",
    )

    print(f"Description: {result.description}")
    print(f"Extracted text length: {len(result.extracted_text)} chars")
    print(f"Processing time: {result.processing_time_ms}ms")
    print(f"Model: {result.model_name}")

    # Save result
    import json
    with open("screenshot_analysis.json", "w") as f:
        json.dump(result.to_dict(), f, indent=2)


async def example_mockup_to_react():
    """Example: Convert UI mockup to React code"""
    print("\n=== Mockup to React Code Example ===\n")

    config = VisionModelConfig(
        provider=VisionModelProvider.CLAUDE,
        model_name="claude-3-opus-20240229",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=3000,
    )

    analyzer = get_visual_analyzer(config, force_new=True)

    # Convert mockup
    result = await analyzer.mockup_to_code(
        image_path="/path/to/mockup.png",
        framework=CodeFramework.REACT,
        additional_requirements="""
        - Use Tailwind CSS for styling
        - Make it fully responsive
        - Use TypeScript
        - Follow React best practices (hooks, functional components)
        - Include proper accessibility attributes
        """,
    )

    print(f"Found {len(result.ui_components)} UI components")
    print(f"\nComponents:")
    for component in result.ui_components:
        print(f"  - {component.semantic_label or component.component_type.value}")
        print(f"    Position: {component.position.to_dict()}")
        if component.text_content:
            print(f"    Text: {component.text_content}")
        if component.colors:
            print(f"    Colors: {component.colors}")

    # Display generated code
    if result.generated_code:
        code_template = result.generated_code[0]
        print(f"\n{'='*60}")
        print("Generated React Component:")
        print(f"{'='*60}\n")

        # Imports
        if code_template.imports:
            print("Imports:")
            for imp in code_template.imports:
                print(f"  {imp}")
            print()

        # Main code
        print(code_template.code)

        # CSS if any
        if code_template.css:
            print(f"\n{'='*60}")
            print("CSS:")
            print(f"{'='*60}\n")
            print(code_template.css)

        # Dependencies
        if code_template.dependencies:
            print(f"\nDependencies:")
            for pkg, version in code_template.dependencies.items():
                print(f"  {pkg}: {version}")

        # Save to file
        output_dir = Path("generated_components")
        output_dir.mkdir(exist_ok=True)

        component_file = output_dir / "GeneratedComponent.tsx"
        with open(component_file, "w") as f:
            if code_template.imports:
                f.write("\n".join(code_template.imports))
                f.write("\n\n")
            f.write(code_template.code)

        if code_template.css:
            css_file = output_dir / "GeneratedComponent.css"
            with open(css_file, "w") as f:
                f.write(code_template.css)

        print(f"\nSaved to: {component_file}")


async def example_error_diagnosis():
    """Example: Diagnose error from screenshot"""
    print("\n=== Error Diagnosis Example ===\n")

    config = VisionModelConfig(
        provider=VisionModelProvider.GPT4V,
        model_name="gpt-4-vision-preview",
        api_key=os.getenv("OPENAI_API_KEY"),
        max_tokens=2000,
    )

    analyzer = get_visual_analyzer(config, force_new=True)

    # Analyze error screenshot
    result = await analyzer.extract_error_info(
        image_path="/path/to/error-screenshot.png",
        context="React application in development mode using Vite",
    )

    if result.error_info:
        error = result.error_info

        print(f"Error Type: {error.error_type}")
        print(f"Severity: {error.severity.upper()}")
        print(f"\nError Message:")
        print(f"  {error.error_message}")

        if error.stack_trace:
            print(f"\nStack Trace:")
            for line in error.stack_trace:
                print(f"  {line}")

        if error.file_paths:
            print(f"\nAffected Files:")
            for i, (file, line) in enumerate(zip(error.file_paths, error.line_numbers)):
                print(f"  {i+1}. {file}:{line}")

        print(f"\nContext:")
        print(f"  Browser Console: {error.browser_console}")
        print(f"  Terminal Output: {error.terminal_output}")
        print(f"  Application Error: {error.application_error}")

        print(f"\nDiagnosis:")
        print(f"  Likely Cause: {error.likely_cause}")

        if error.suggested_fixes:
            print(f"\nSuggested Fixes:")
            for i, fix in enumerate(error.suggested_fixes, 1):
                print(f"  {i}. {fix}")

        print(f"\nConfidence: {error.confidence * 100:.1f}%")


async def example_architecture_diagram():
    """Example: Parse architecture diagram"""
    print("\n=== Architecture Diagram Analysis Example ===\n")

    config = VisionModelConfig(
        provider=VisionModelProvider.CLAUDE,
        model_name="claude-3-opus-20240229",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=2500,
    )

    analyzer = get_visual_analyzer(config, force_new=True)

    # Parse diagram
    result = await analyzer.diagram_to_architecture(
        image_path="/path/to/architecture-diagram.png",
        context="""
        Microservices architecture for an e-commerce platform.
        Looking to understand the service boundaries and data flow.
        """,
    )

    print(f"System Overview:")
    print(f"  {result.description}\n")

    print(f"Identified {len(result.architecture_nodes)} components:\n")

    for node in result.architecture_nodes:
        print(f"Component: {node.label}")
        print(f"  Type: {node.node_type}")
        if node.technology:
            print(f"  Technology: {node.technology}")
        if node.description:
            print(f"  Description: {node.description}")
        if node.connects_to:
            print(f"  Connects to: {', '.join(node.connects_to)}")
        print()

    # Display suggested structure
    if result.architecture_nodes and result.architecture_nodes[0].suggested_structure:
        print("Suggested Project Structure:")
        print(result.architecture_nodes[0].suggested_structure)


async def example_code_extraction():
    """Example: Extract code from screenshot"""
    print("\n=== Code Extraction Example ===\n")

    config = VisionModelConfig(
        provider=VisionModelProvider.GPT4V,
        model_name="gpt-4-vision-preview",
        api_key=os.getenv("OPENAI_API_KEY"),
        max_tokens=3000,
    )

    analyzer = get_visual_analyzer(config, force_new=True)

    # Extract code
    result = await analyzer.extract_code_from_image(
        image_path="/path/to/code-screenshot.png",
        programming_language="python",
    )

    print(f"Extracted {len(result.code_blocks)} code block(s)\n")

    for i, block in enumerate(result.code_blocks, 1):
        print(f"Block {i} ({block['language']}):")
        print(f"{'='*60}")
        print(block['code'])
        print(f"{'='*60}\n")

        # Save to file
        ext = {
            'python': 'py',
            'javascript': 'js',
            'typescript': 'ts',
            'java': 'java',
            'go': 'go',
            'rust': 'rs',
        }.get(block['language'].lower(), 'txt')

        output_file = f"extracted_code_{i}.{ext}"
        with open(output_file, "w") as f:
            f.write(block['code'])
        print(f"Saved to: {output_file}")


async def example_local_llava():
    """Example: Use local LLaVA model"""
    print("\n=== Local LLaVA Model Example ===\n")

    # Assumes you have LLaVA server running on localhost:8000
    config = VisionModelConfig(
        provider=VisionModelProvider.LLAVA,
        model_name="llava-v1.5-13b",
        api_base="http://localhost:8000",
        device="cuda",  # or "cpu", "mps" for Apple Silicon
        max_tokens=2000,
        temperature=0.7,
    )

    analyzer = get_visual_analyzer(config, force_new=True)

    # Use same API as cloud models
    result = await analyzer.analyze_screenshot(
        image_path="/path/to/screenshot.png",
        context="Development environment screenshot",
    )

    print(f"Description: {result.description}")
    print(f"Model: {result.model_name} (local)")
    print(f"Processing time: {result.processing_time_ms}ms")


async def example_batch_processing():
    """Example: Process multiple images"""
    print("\n=== Batch Processing Example ===\n")

    config = VisionModelConfig(
        provider=VisionModelProvider.GPT4V,
        model_name="gpt-4-vision-preview",
        api_key=os.getenv("OPENAI_API_KEY"),
        max_tokens=1500,
    )

    analyzer = get_visual_analyzer(config, force_new=True)

    # Process multiple screenshots
    image_dir = Path("/path/to/screenshots")
    results = []

    for image_path in image_dir.glob("*.png"):
        print(f"Processing: {image_path.name}")

        result = await analyzer.analyze_screenshot(
            image_path=str(image_path),
            context="Application screenshot from user report",
        )

        results.append({
            "filename": image_path.name,
            "description": result.description,
            "processing_time_ms": result.processing_time_ms,
        })

        # Rate limiting for API
        await asyncio.sleep(1)

    # Save batch results
    import json
    with open("batch_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nProcessed {len(results)} images")
    avg_time = sum(r["processing_time_ms"] for r in results) / len(results)
    print(f"Average processing time: {avg_time:.0f}ms")


async def example_comparison():
    """Example: Compare different vision models"""
    print("\n=== Model Comparison Example ===\n")

    image_path = "/path/to/test-image.png"

    # GPT-4V
    print("Testing GPT-4V...")
    gpt4v_config = VisionModelConfig(
        provider=VisionModelProvider.GPT4V,
        model_name="gpt-4-vision-preview",
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    gpt4v_analyzer = get_visual_analyzer(gpt4v_config, force_new=True)
    gpt4v_result = await gpt4v_analyzer.analyze_screenshot(image_path)

    # Claude
    print("Testing Claude Vision...")
    claude_config = VisionModelConfig(
        provider=VisionModelProvider.CLAUDE,
        model_name="claude-3-opus-20240229",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )
    claude_analyzer = get_visual_analyzer(claude_config, force_new=True)
    claude_result = await claude_analyzer.analyze_screenshot(image_path)

    # Compare
    print("\n=== Comparison Results ===\n")
    print(f"GPT-4V:")
    print(f"  Time: {gpt4v_result.processing_time_ms}ms")
    print(f"  Description length: {len(gpt4v_result.description)} chars")
    print(f"  Confidence: {gpt4v_result.confidence_score}")

    print(f"\nClaude:")
    print(f"  Time: {claude_result.processing_time_ms}ms")
    print(f"  Description length: {len(claude_result.description)} chars")
    print(f"  Confidence: {claude_result.confidence_score}")


async def main():
    """Run all examples"""
    # Uncomment the examples you want to run

    # await example_screenshot_analysis()
    # await example_mockup_to_react()
    # await example_error_diagnosis()
    # await example_architecture_diagram()
    # await example_code_extraction()
    # await example_local_llava()
    # await example_batch_processing()
    # await example_comparison()

    print("\nExamples complete!")


if __name__ == "__main__":
    asyncio.run(main())
