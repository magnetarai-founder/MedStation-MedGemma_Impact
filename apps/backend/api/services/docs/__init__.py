#!/usr/bin/env python3
"""
Auto-Documentation System for MagnetarCode

Provides intelligent documentation generation and maintenance:
- Automatic docstring generation for functions/classes
- Documentation sync detection and updates
- Stale documentation detection
- README generation from codebase structure
- API documentation generation
- Module-level documentation
- Support for multiple docstring styles (Google, NumPy, Sphinx)

Usage:
    from api.services.docs import DocGenerator, DocstringStyle

    # Initialize generator
    generator = DocGenerator(workspace_root="/path/to/project")

    # Generate docstring for a function
    docstring = await generator.generate_docstring(
        file_path="module.py",
        entity_name="my_function",
        style=DocstringStyle.GOOGLE
    )

    # Check documentation health
    status = await generator.scan_documentation_health()

    # Generate README
    await generator.generate_readme(output_path="README.md")

    # Generate API docs
    await generator.generate_api_docs(output_dir="docs/api")
"""

from .generator import (
    DocGenerator,
    DocstringStyle,
    DocumentationStatus,
    get_doc_generator,
)

__all__ = [
    "DocGenerator",
    "DocstringStyle",
    "DocumentationStatus",
    "get_doc_generator",
]
