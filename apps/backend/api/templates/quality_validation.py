"""
Quality validation templates (VALID_186-VALID_205).
Moved from template_library_full.py for modular architecture.
"""

from typing import Dict, List
from .types import SQLTemplate, TemplateCategory


def _get_validation_params(template_num: int) -> List[str]:
    """Get parameters for validation templates"""
    if template_num == 186:
        return ['table_name', 'sku_column', 'name_column', 'price_column',
               'description_column', 'category_column']
    else:
        return ['table_name', 'model_name', 'sku_column', 'field_column',
               'context_column', 'validation_flag', 'content_column']


def get_templates() -> Dict[str, SQLTemplate]:
    """Return all QUALITY_VALIDATION templates (VALID_186–VALID_205)."""
    templates: Dict[str, SQLTemplate] = {}

    # Templates 186-195: Data Quality
    for i in range(186, 196):
        template_id = f'VALID_{i:03d}'

        if i == 186:
            name = 'Completeness Checker'
            template = """
            WITH field_counts AS (
                SELECT
                    COUNT(*) as total_records,
                    COUNTIF({sku_column} IS NOT NULL) as sku_filled,
                    COUNTIF({name_column} IS NOT NULL) as name_filled,
                    COUNTIF({price_column} IS NOT NULL AND {price_column} > 0) as price_valid,
                    COUNTIF({description_column} IS NOT NULL AND LENGTH({description_column}) > 20) as desc_valid,
                    COUNTIF({category_column} IS NOT NULL) as category_filled
                FROM `{table_name}`
            )
            SELECT
                'SKU' as field_name, sku_filled / total_records * 100 as completeness_pct,
                CASE WHEN sku_filled / total_records < 0.95 THEN 'FAIL' ELSE 'PASS' END as status
            FROM field_counts
            UNION ALL
            SELECT 'Name', name_filled / total_records * 100,
                CASE WHEN name_filled / total_records < 0.98 THEN 'FAIL' ELSE 'PASS' END
            FROM field_counts
            UNION ALL
            SELECT 'Price', price_valid / total_records * 100,
                CASE WHEN price_valid / total_records < 0.99 THEN 'FAIL' ELSE 'PASS' END
            FROM field_counts
            """
        elif i <= 190:
            validation_types = ['Format Validation', 'Range Validation',
                               'Consistency Check', 'Duplicate Detection', 'Anomaly Detection'][i-187]
            name = f'{validation_types}'
            template = f"""
            SELECT {{sku_column}} as sku,
            {{field_column}} as field_value,
            AI.GENERATE_BOOL(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Validate {validation_types.lower()} for: ', {{field_column}},
                ' in context of ', {{context_column}}),
                STRUCT(0.1 AS temperature)
            ) AS is_valid,
            AI.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Explain {validation_types.lower()} issues if any'),
                STRUCT(0.2 AS temperature, 100 AS max_output_tokens)
            ) AS validation_message
            FROM `{{table_name}}`
            WHERE {{validation_flag}} IS NULL
            """
        else:
            quality_types = ['Image Quality', 'Description Quality', 'SEO Quality',
                            'Data Freshness', 'Compliance Check'][i-191]
            name = f'{quality_types} Scorer'
            template = f"""
            SELECT {{sku_column}} as sku,
            AI.GENERATE_DOUBLE(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Score {quality_types.lower()} (0-100) for: ',
                {{content_column}}),
                STRUCT(0.2 AS temperature)
            ) AS quality_score,
            AI.GENERATE_TABLE(
                MODEL `{{model_name}}`,
                TABLE (SELECT {{sku_column}}, {{content_column}} FROM `{{table_name}}`),
                STRUCT('List {quality_types.lower()} issues. Output: issue, severity, suggestion' AS prompt)
            ).*
            FROM `{{table_name}}`
            """

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=name,
            category=TemplateCategory.QUALITY_VALIDATION,
            description=f'Validation template {i}',
            template=template,
            parameters=_get_validation_params(i),
            output_schema={'sku': 'STRING', 'validation_result': 'STRING'}
        )

    # Templates 196-205: Business Rules
    for i in range(196, 206):
        template_id = f'VALID_{i:03d}'
        rule_types = [
            'Pricing Rules', 'Naming Convention', 'Category Rules', 'Brand Guidelines',
            'Legal Compliance', 'Age Restriction', 'Shipping Rules', 'Tax Rules',
            'Return Policy', 'Warranty Rules'
        ]

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=f'{rule_types[i-196]} Validator',
            category=TemplateCategory.QUALITY_VALIDATION,
            description=f'Validate {rule_types[i-196].lower()}',
            template=f"""
            WITH rule_context AS (
                SELECT {{sku_column}} as sku,
                {{product_column}} as product,
                {{category_column}} as category,
                {{price_column}} as price
                FROM `{{table_name}}`
            )
            SELECT sku,
            AI.GENERATE_BOOL(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Check {rule_types[i-196].lower()} compliance for: ',
                product, ' in ', category, ' at $', CAST(price AS STRING)),
                STRUCT(0.1 AS temperature)
            ) AS rule_compliant,
            AI.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('List any {rule_types[i-196].lower()} violations'),
                STRUCT(0.2 AS temperature, 200 AS max_output_tokens)
            ) AS violations
            FROM rule_context
            """,
            parameters=['table_name', 'model_name', 'sku_column', 'product_column',
                       'category_column', 'price_column'],
            output_schema={'sku': 'STRING', 'rule_compliant': 'BOOL', 'violations': 'STRING'}
        )

    return templates
