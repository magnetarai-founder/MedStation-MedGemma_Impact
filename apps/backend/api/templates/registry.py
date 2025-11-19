"""
Template registry - aggregates all category modules.
Central point for accessing SQL templates.
"""

from typing import Dict, List, Optional
from .types import SQLTemplate, TemplateCategory

# Import all category modules
from . import (
    product_enrichment,
    attribute_extraction,
    category_mapping,
    brand_standardization,
    pricing_analysis,
    inventory_optimization,
    quality_validation,
    competitor_analysis,
    trend_detection,
    customer_segmentation,
)


# Global registry cache
_TEMPLATE_REGISTRY: Optional[Dict[str, SQLTemplate]] = None


def _load_templates() -> Dict[str, SQLTemplate]:
    """Load all templates from category modules."""
    templates: Dict[str, SQLTemplate] = {}

    # Load from each category module
    templates.update(product_enrichment.get_templates())
    templates.update(attribute_extraction.get_templates())
    templates.update(category_mapping.get_templates())
    templates.update(brand_standardization.get_templates())
    templates.update(pricing_analysis.get_templates())
    templates.update(inventory_optimization.get_templates())
    templates.update(quality_validation.get_templates())
    templates.update(competitor_analysis.get_templates())
    templates.update(trend_detection.get_templates())
    templates.update(customer_segmentation.get_templates())

    return templates


def get_template_registry() -> Dict[str, SQLTemplate]:
    """Get the full template registry (cached)."""
    global _TEMPLATE_REGISTRY
    if _TEMPLATE_REGISTRY is None:
        _TEMPLATE_REGISTRY = _load_templates()
    return _TEMPLATE_REGISTRY


def get_template(template_id: str) -> Optional[SQLTemplate]:
    """Retrieve a template by ID."""
    registry = get_template_registry()
    return registry.get(template_id)


def get_templates_by_category(category: TemplateCategory) -> Dict[str, SQLTemplate]:
    """Get all templates for a specific category."""
    registry = get_template_registry()
    return {
        template_id: template
        for template_id, template in registry.items()
        if template.category == category
    }


def get_template_count() -> int:
    """Get total number of templates."""
    return len(get_template_registry())


def render_template(
    template_id: str,
    parameters: Dict[str, str]
) -> Optional[str]:
    """
    Render a template with the provided parameters.

    Args:
        template_id: The template ID (e.g., 'ENRICH_001')
        parameters: Dict of parameter names to values

    Returns:
        Rendered SQL string or None if template not found
    """
    template = get_template(template_id)
    if not template:
        return None

    sql = template.template
    for param_name, param_value in parameters.items():
        placeholder = f'{{{param_name}}}'
        sql = sql.replace(placeholder, str(param_value))

    return sql


class FullTemplateLibrary:
    """
    Backward-compatible wrapper class.
    Provides the same interface as the original monolithic class.
    """

    def __init__(self):
        """Initialize the template library."""
        self.templates = get_template_registry()

    def get_template(self, template_id: str) -> Optional[SQLTemplate]:
        """Retrieve a template by ID."""
        return get_template(template_id)

    def get_templates_by_category(self, category: TemplateCategory) -> Dict[str, SQLTemplate]:
        """Get all templates for a specific category."""
        return get_templates_by_category(category)

    def get_template_count(self) -> int:
        """Get total number of templates."""
        return get_template_count()

    def render_template(self, template_id: str, parameters: Dict[str, str]) -> Optional[str]:
        """Render a template with the provided parameters."""
        return render_template(template_id, parameters)


# Singleton instance for backward compatibility
_library_instance: Optional[FullTemplateLibrary] = None


def get_full_template_library() -> FullTemplateLibrary:
    """Get singleton instance of FullTemplateLibrary."""
    global _library_instance
    if _library_instance is None:
        _library_instance = FullTemplateLibrary()
    return _library_instance
