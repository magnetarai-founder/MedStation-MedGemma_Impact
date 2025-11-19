"""
Brand standardization templates (BRAND_121-BRAND_145).
Moved from template_library_full.py for modular architecture.
"""

from typing import Dict, List
from .types import SQLTemplate, TemplateCategory


def _get_brand_params(template_num: int) -> List[str]:
    """Get parameters for brand templates"""
    if template_num == 121:
        return ['table_name', 'brand_mapping_table', 'model_name',
               'sku_column', 'brand_column']
    else:
        return ['table_name', 'model_name', 'sku_column', 'brand_column']


def get_templates() -> Dict[str, SQLTemplate]:
    """Return all BRAND_STANDARDIZATION templates (BRAND_121–BRAND_145)."""
    templates: Dict[str, SQLTemplate] = {}

    # Templates 121-130: Brand Cleaning
    for i in range(121, 131):
        template_id = f'BRAND_{i:03d}'

        if i == 121:
            name = 'Brand Name Standardizer'
            template = """
            WITH brand_variants AS (
                SELECT brand, canonical_brand, confidence
                FROM `{brand_mapping_table}`
            )
            SELECT p.{sku_column} as sku,
            p.{brand_column} as original_brand,
            UPPER(TRIM(p.{brand_column})) as cleaned_brand,
            COALESCE(
                bv.canonical_brand,
                AI.GENERATE_TEXT(
                    MODEL `{model_name}`,
                    PROMPT => CONCAT('Standardize brand name: ', p.{brand_column},
                    '. Known brands: ', (SELECT STRING_AGG(DISTINCT canonical_brand, ', ') FROM brand_variants)),
                    STRUCT(0.1 AS temperature, 30 AS max_output_tokens)
                )
            ) AS standard_brand
            FROM `{table_name}` p
            LEFT JOIN brand_variants bv ON UPPER(TRIM(p.{brand_column})) = UPPER(bv.brand)
            """
        elif i <= 125:
            clean_types = ['Remove Special Chars', 'Fix Typos', 'Expand Abbreviations',
                          'Remove Suffixes', 'Normalize Case'][i-122]
            name = f'Brand {clean_types}'
            template = f"""
            SELECT {{sku_column}} as sku,
            {{brand_column}} as original_brand,
            ML.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('{clean_types} for brand: ', {{brand_column}}),
                STRUCT(0.1 AS temperature, 30 AS max_output_tokens)
            ) AS cleaned_brand
            FROM `{{table_name}}`
            """
        else:
            validation_types = ['Verify Exists', 'Check Spelling', 'Validate Authorization',
                               'Find Parent Company', 'Get Brand Country'][i-126]
            name = f'Brand {validation_types}'
            template = f"""
            SELECT {{sku_column}} as sku,
            {{brand_column}} as brand,
            AI.GENERATE_BOOL(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('{validation_types}: ', {{brand_column}}),
                STRUCT(0.1 AS temperature)
            ) AS validation_result,
            ML.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('{validation_types} details for: ', {{brand_column}}),
                STRUCT(0.2 AS temperature, 50 AS max_output_tokens)
            ) AS validation_details
            FROM `{{table_name}}`
            """

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=name,
            category=TemplateCategory.BRAND_STANDARDIZATION,
            description=f'Brand template {i}',
            template=template,
            parameters=_get_brand_params(i),
            output_schema={'sku': 'STRING', 'brand': 'STRING'}
        )

    # Templates 131-140: Brand Enrichment
    for i in range(131, 141):
        template_id = f'BRAND_{i:03d}'
        enrichment_types = [
            'Brand Story', 'Brand Values', 'Brand Tagline', 'Target Market',
            'Price Tier', 'Brand Category', 'Sustainability Score',
            'Brand Recognition', 'Market Position', 'Brand Age'
        ]

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=f'{enrichment_types[i-131]} Generator',
            category=TemplateCategory.BRAND_STANDARDIZATION,
            description=f'Generate {enrichment_types[i-131].lower()}',
            template=f"""
            SELECT {{brand_column}} as brand,
            AI.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Generate {enrichment_types[i-131].lower()} for brand: ',
                {{brand_column}}, '. Industry: ', {{industry_column}}),
                STRUCT(0.6 AS temperature, 100 AS max_output_tokens)
            ) AS {enrichment_types[i-131].lower().replace(' ', '_')},
            COUNT(DISTINCT {{sku_column}}) as product_count
            FROM `{{table_name}}`
            GROUP BY {{brand_column}}
            """,
            parameters=['table_name', 'model_name', 'brand_column',
                       'sku_column', 'industry_column'],
            output_schema={'brand': 'STRING', 'enrichment': 'STRING', 'product_count': 'INT64'}
        )

    # Templates 141-145: Brand Analytics
    for i in range(141, 146):
        template_id = f'BRAND_{i:03d}'
        analytics_types = [
            'Brand Strength Score', 'Competitor Analysis', 'Brand Consistency',
            'Cross-sell Potential', 'Brand Loyalty Index'
        ]

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=f'{analytics_types[i-141]} Calculator',
            category=TemplateCategory.BRAND_STANDARDIZATION,
            description=f'Calculate {analytics_types[i-141].lower()}',
            template=f"""
            WITH brand_metrics AS (
                SELECT {{brand_column}} as brand,
                COUNT(DISTINCT {{sku_column}}) as sku_count,
                AVG({{price_column}}) as avg_price,
                COUNT(DISTINCT {{category_column}}) as category_count
                FROM `{{table_name}}` GROUP BY brand
            )
            SELECT brand,
            sku_count, avg_price, category_count,
            AI.GENERATE_DOUBLE(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Calculate {analytics_types[i-141].lower()} (0-100) for: ',
                brand, ' with ', CAST(sku_count AS STRING), ' products, avg price $',
                CAST(avg_price AS STRING), ' in ', CAST(category_count AS STRING), ' categories'),
                STRUCT(0.2 AS temperature)
            ) AS {analytics_types[i-141].lower().replace(' ', '_')}
            FROM brand_metrics
            """,
            parameters=['table_name', 'model_name', 'brand_column', 'sku_column',
                       'price_column', 'category_column'],
            output_schema={'brand': 'STRING', 'sku_count': 'INT64', 'avg_price': 'FLOAT64',
                          'category_count': 'INT64', 'score': 'FLOAT64'}
        )

    return templates
