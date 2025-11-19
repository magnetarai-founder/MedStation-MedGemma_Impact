"""
Pricing analysis templates (PRICE_146-PRICE_165).
Moved from template_library_full.py for modular architecture.
"""

from typing import Dict, List
from .types import SQLTemplate, TemplateCategory


def _get_pricing_params(template_num: int) -> List[str]:
    """Get parameters for pricing templates"""
    if template_num == 146:
        return ['table_name', 'sku_column', 'price_column', 'category_column', 'brand_column']
    else:
        return ['table_name', 'model_name', 'sku_column', 'price_column',
               'cost_column', 'category_column']


def get_templates() -> Dict[str, SQLTemplate]:
    """Return all PRICING_ANALYSIS templates (PRICE_146–PRICE_165)."""
    templates: Dict[str, SQLTemplate] = {}

    # Templates 146-155: Price Analysis
    for i in range(146, 156):
        template_id = f'PRICE_{i:03d}'

        if i == 146:
            name = 'Price Competitiveness Analyzer'
            template = """
            WITH price_stats AS (
                SELECT {category_column} as category,
                {brand_column} as brand,
                PERCENTILE_CONT({price_column}, 0.25) OVER (PARTITION BY {category_column}) as p25,
                PERCENTILE_CONT({price_column}, 0.50) OVER (PARTITION BY {category_column}) as p50,
                PERCENTILE_CONT({price_column}, 0.75) OVER (PARTITION BY {category_column}) as p75
                FROM `{table_name}`
            )
            SELECT DISTINCT p.{sku_column} as sku,
            p.{price_column} as current_price,
            ps.p50 as category_median,
            CASE
                WHEN p.{price_column} < ps.p25 THEN 'Budget'
                WHEN p.{price_column} > ps.p75 THEN 'Premium'
                ELSE 'Mid-range'
            END as price_tier,
            (p.{price_column} - ps.p50) / ps.p50 * 100 as pct_from_median
            FROM `{table_name}` p
            JOIN price_stats ps ON p.{category_column} = ps.category
            """
        elif i <= 150:
            price_types = ['Dynamic Pricing', 'Bundle Pricing', 'Discount Optimization',
                          'Price Elasticity', 'Margin Analysis'][i-147]
            name = f'{price_types} Calculator'
            template = f"""
            SELECT {{sku_column}} as sku,
            {{price_column}} as current_price,
            {{cost_column}} as cost,
            AI.GENERATE_DOUBLE(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Calculate optimal {price_types.lower()} for product with ',
                'current price $', CAST({{price_column}} AS STRING),
                ', cost $', CAST({{cost_column}} AS STRING),
                ', in category ', {{category_column}}),
                STRUCT(0.2 AS temperature)
            ) AS optimized_value
            FROM `{{table_name}}`
            """
        else:
            analysis_types = ['Psychological Pricing', 'Regional Pricing',
                             'Seasonal Adjustment', 'Competitor Match', 'Value Perception'][i-151]
            name = f'{analysis_types} Analyzer'
            template = f"""
            SELECT {{sku_column}} as sku,
            {{price_column}} as price,
            AI.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Analyze {analysis_types.lower()} for $',
                CAST({{price_column}} AS STRING), ' product in ', {{category_column}}),
                STRUCT(0.4 AS temperature, 100 AS max_output_tokens)
            ) AS pricing_analysis,
            AI.GENERATE_DOUBLE(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Suggest {analysis_types.lower()} adjusted price'),
                STRUCT(0.2 AS temperature)
            ) AS suggested_price
            FROM `{{table_name}}`
            """

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=name,
            category=TemplateCategory.PRICING_ANALYSIS,
            description=f'Pricing template {i}',
            template=template,
            parameters=_get_pricing_params(i),
            output_schema={'sku': 'STRING', 'price': 'FLOAT64', 'analysis': 'STRING'}
        )

    # Templates 156-165: Advanced Pricing
    for i in range(156, 166):
        template_id = f'PRICE_{i:03d}'
        advanced_types = [
            'Price-Volume Optimization', 'Cross-price Elasticity', 'Price Segmentation',
            'Promotional Pricing', 'Loss Leader Analysis', 'Price Matching Strategy',
            'Currency Conversion', 'Tax-inclusive Pricing', 'Shipping Cost Integration',
            'Subscription Pricing'
        ]

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=f'{advanced_types[i-156]} Model',
            category=TemplateCategory.PRICING_ANALYSIS,
            description=f'Advanced pricing: {advanced_types[i-156]}',
            template=f"""
            WITH pricing_context AS (
                SELECT {{sku_column}} as sku,
                {{price_column}} as price,
                {{sales_column}} as sales_volume,
                {{margin_column}} as margin
                FROM `{{table_name}}`
            )
            SELECT sku,
            AI.GENERATE_TABLE(
                MODEL `{{model_name}}`,
                TABLE pricing_context,
                STRUCT('Generate {advanced_types[i-156]} analysis. Output: recommendation, impact, confidence' AS prompt)
            ).*
            FROM pricing_context
            """,
            parameters=['table_name', 'model_name', 'sku_column', 'price_column',
                       'sales_column', 'margin_column'],
            output_schema={'sku': 'STRING', 'recommendation': 'STRING',
                          'impact': 'FLOAT64', 'confidence': 'FLOAT64'}
        )

    return templates
