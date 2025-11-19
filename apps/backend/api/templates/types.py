"""
Shared types for SQL template library.
Moved from template_library_full.py for modular architecture.
"""

from typing import Dict, List
from dataclasses import dataclass
from enum import Enum


class TemplateCategory(Enum):
    """Categories of SQL templates"""
    PRODUCT_ENRICHMENT = "product_enrichment"
    ATTRIBUTE_EXTRACTION = "attribute_extraction"
    CATEGORY_MAPPING = "category_mapping"
    BRAND_STANDARDIZATION = "brand_standardization"
    PRICING_ANALYSIS = "pricing_analysis"
    INVENTORY_OPTIMIZATION = "inventory_optimization"
    QUALITY_VALIDATION = "quality_validation"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    TREND_DETECTION = "trend_detection"
    CUSTOMER_SEGMENTATION = "customer_segmentation"


@dataclass
class SQLTemplate:
    """A reusable SQL template with metadata"""
    id: str
    name: str
    category: TemplateCategory
    description: str
    template: str
    parameters: List[str]
    output_schema: Dict[str, str]
    confidence_threshold: float = 0.8
