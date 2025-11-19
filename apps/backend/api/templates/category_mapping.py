"""
Category mapping templates (CATEGORY_091-CATEGORY_120).
Moved from template_library_full.py for modular architecture.
"""

from typing import Dict, List
from .types import SQLTemplate, TemplateCategory


def _get_category_params(template_num: int) -> List[str]:
    """Get parameters for category templates"""
    if template_num == 91:
        return ['table_name', 'mapping_table', 'model_name', 'sku_column', 'category_column']
    elif template_num <= 100:
        return ['table_name', 'model_name', 'sku_column', 'product_column',
               'description_column', 'category_column', 'subcategory_column']
    else:
        return ['source_table', 'target_table', 'model_name',
               'source_category', 'target_category']


def get_templates() -> Dict[str, SQLTemplate]:
    """Return all CATEGORY_MAPPING templates (CATEGORY_091–CATEGORY_120)."""
    templates: Dict[str, SQLTemplate] = {}

    # Templates 91-100: Category Standardization
    for i in range(91, 101):
        template_id = f'CATEGORY_{i:03d}'

        if i == 91:
            name = 'Basic Category Mapper'
            template = """
            WITH category_map AS (
                SELECT original, standard, confidence FROM `{mapping_table}`
            )
            SELECT p.{sku_column} as sku,
            p.{category_column} as original_category,
            COALESCE(
                cm.standard,
                AI.GENERATE_TEXT(
                    MODEL `{model_name}`,
                    PROMPT => CONCAT('Map this to standard category: ', p.{category_column},
                    '. Choose from: ', (SELECT STRING_AGG(DISTINCT standard, ', ') FROM category_map)),
                    STRUCT(0.1 AS temperature, 50 AS max_output_tokens)
                )
            ) AS standard_category
            FROM `{table_name}` p
            LEFT JOIN category_map cm ON LOWER(p.{category_column}) = LOWER(cm.original)
            """
        elif i <= 95:
            hierarchy_level = ['Department', 'Category', 'Subcategory', 'Product Type'][i-92]
            name = f'{hierarchy_level} Classifier'
            template = f"""
            SELECT {{sku_column}} as sku,
            ML.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Classify into {hierarchy_level}: ', {{product_column}},
                '. Context: ', {{description_column}}),
                STRUCT(0.2 AS temperature, 30 AS max_output_tokens)
            ) AS {hierarchy_level.lower()}
            FROM `{{table_name}}`
            WHERE {{{hierarchy_level.lower()}_column}} IS NULL
            """
        else:
            taxonomy_types = ['Google Shopping', 'Amazon', 'Facebook', 'eBay', 'Shopify'][i-96]
            name = f'{taxonomy_types} Taxonomy Mapper'
            template = f"""
            SELECT {{sku_column}} as sku,
            ML.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Map to {taxonomy_types} taxonomy: ',
                {{category_column}}, ' > ', {{subcategory_column}},
                '. Product: ', {{product_column}}),
                STRUCT(0.1 AS temperature, 100 AS max_output_tokens)
            ) AS {taxonomy_types.lower()}_category_id
            FROM `{{table_name}}`
            """

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=name,
            category=TemplateCategory.CATEGORY_MAPPING,
            description=f'Category mapping template {i}',
            template=template,
            parameters=_get_category_params(i),
            output_schema={'sku': 'STRING', 'category': 'STRING'}
        )

    # Templates 101-110: Cross-reference Mapping
    for i in range(101, 111):
        template_id = f'CATEGORY_{i:03d}'

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=f'Category Cross-Reference {i-100}',
            category=TemplateCategory.CATEGORY_MAPPING,
            description=f'Cross-reference categories between systems',
            template="""
            WITH source_categories AS (
                SELECT DISTINCT {source_category} as category FROM `{source_table}`
            ),
            target_categories AS (
                SELECT DISTINCT {target_category} as category FROM `{target_table}`
            )
            SELECT
                sc.category as source_category,
                AI.GENERATE_TEXT(
                    MODEL `{model_name}`,
                    PROMPT => CONCAT('Find best match in target for: ', sc.category,
                    '. Target options: ', (SELECT STRING_AGG(category, ', ') FROM target_categories)),
                    STRUCT(0.1 AS temperature, 50 AS max_output_tokens)
                ) AS target_category,
                AI.GENERATE_DOUBLE(
                    MODEL `{model_name}`,
                    PROMPT => CONCAT('Confidence score (0-1) for mapping ', sc.category),
                    STRUCT(0.1 AS temperature)
                ) AS confidence_score
            FROM source_categories sc
            """,
            parameters=['source_table', 'target_table', 'model_name',
                       'source_category', 'target_category'],
            output_schema={'source_category': 'STRING', 'target_category': 'STRING',
                          'confidence_score': 'FLOAT64'}
        )

    # Templates 111-120: Industry-Specific Categories
    for i in range(111, 121):
        template_id = f'CATEGORY_{i:03d}'
        industries = [
            'Fashion', 'Electronics', 'Home & Garden', 'Sports', 'Beauty',
            'Toys', 'Automotive', 'Books', 'Food & Beverage', 'Health'
        ]

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=f'{industries[i-111]} Category Specialist',
            category=TemplateCategory.CATEGORY_MAPPING,
            description=f'Specialized categorization for {industries[i-111]}',
            template=f"""
            SELECT {{sku_column}} as sku,
            ML.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Categorize this {industries[i-111].lower()} product: ',
                {{product_column}}, '. Use industry-standard {industries[i-111]} categories.'),
                STRUCT(0.2 AS temperature, 50 AS max_output_tokens)
            ) AS industry_category,
            AI.GENERATE_TABLE(
                MODEL `{{model_name}}`,
                TABLE (SELECT * FROM `{{table_name}}` WHERE {{sku_column}} = {{sku_column}}),
                STRUCT('Extract {industries[i-111]}-specific attributes. Output relevant columns.' AS prompt)
            ).*
            FROM `{{table_name}}`
            WHERE {{industry_column}} = '{industries[i-111]}'
            """,
            parameters=['table_name', 'model_name', 'sku_column',
                       'product_column', 'industry_column'],
            output_schema={'sku': 'STRING', 'industry_category': 'STRING'}
        )

    return templates
