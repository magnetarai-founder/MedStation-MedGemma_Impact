"""
SQL Template Library - Modular Package
Provides 256 SQL templates organized into 10 categories.
"""

# Re-export types
from .types import SQLTemplate, TemplateCategory

# Re-export registry functions and class
from .registry import (
    get_template,
    get_templates_by_category,
    get_template_count,
    render_template,
    FullTemplateLibrary,
    get_full_template_library,
)

__all__ = [
    # Types
    'SQLTemplate',
    'TemplateCategory',
    # Registry functions
    'get_template',
    'get_templates_by_category',
    'get_template_count',
    'render_template',
    # Backward compatibility
    'FullTemplateLibrary',
    'get_full_template_library',
]
