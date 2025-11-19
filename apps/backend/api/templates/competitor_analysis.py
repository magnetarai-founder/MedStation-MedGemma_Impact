"""
Competitor analysis templates (COMP_206-COMP_220).
Moved from template_library_full.py for modular architecture.
"""

from typing import Dict, List
from .types import SQLTemplate, TemplateCategory


def _get_competitor_params(template_num: int) -> List[str]:
    """Get parameters for competitor templates"""
    if template_num == 206:
        return ['our_table', 'competitor_table', 'model_name', 'sku_column',
               'name_column', 'price_column', 'brand_column', 'comp_name_column',
               'comp_price_column', 'comp_source_column']
    else:
        return ['table_name', 'model_name', 'sku_column', 'category_column',
               'brand_column']


def get_templates() -> Dict[str, SQLTemplate]:
    """Return all COMPETITOR_ANALYSIS templates (COMP_206–COMP_220)."""
    templates: Dict[str, SQLTemplate] = {}

    # Templates 206-215: Competitive Intelligence
    for i in range(206, 216):
        template_id = f'COMP_{i:03d}'

        if i == 206:
            name = 'Competitor Price Comparison'
            template = """
            WITH our_products AS (
                SELECT {sku_column} as sku, {name_column} as product_name,
                {price_column} as our_price, {brand_column} as brand
                FROM `{our_table}`
            ),
            competitor_matches AS (
                SELECT o.sku, o.product_name, o.our_price,
                c.{comp_name_column} as comp_product,
                c.{comp_price_column} as comp_price,
                c.{comp_source_column} as competitor
                FROM our_products o
                LEFT JOIN `{competitor_table}` c
                ON AI.GENERATE_BOOL(
                    MODEL `{model_name}`,
                    PROMPT => CONCAT('Are these the same product? ',
                    o.product_name, ' vs ', c.{comp_name_column}),
                    STRUCT(0.1 AS temperature)
                )
            )
            SELECT sku, product_name, our_price, comp_price,
            (our_price - comp_price) as price_diff,
            (our_price - comp_price) / comp_price * 100 as price_diff_pct,
            competitor
            FROM competitor_matches
            WHERE comp_price IS NOT NULL
            """
        elif i <= 210:
            comp_types = ['Feature Comparison', 'Market Position', 'Assortment Gap',
                         'Promotion Analysis', 'Review Comparison'][i-207]
            name = f'{comp_types} Analyzer'
            template = f"""
            SELECT {{sku_column}} as sku,
            AI.GENERATE_TABLE(
                MODEL `{{model_name}}`,
                TABLE (SELECT * FROM `{{table_name}}`),
                STRUCT('Compare {comp_types.lower()} with competitors. Output: competitor, our_value, their_value, gap' AS prompt)
            ).*
            FROM `{{table_name}}`
            """
        else:
            intel_types = ['New Product Alert', 'Price Change Monitor', 'Out of Stock Tracker',
                          'Trend Spotter', 'Market Share Estimate'][i-211]
            name = f'{intel_types}'
            template = f"""
            WITH market_data AS (
                SELECT {{category_column}} as category,
                {{brand_column}} as brand,
                COUNT(DISTINCT {{sku_column}}) as product_count,
                AVG({{price_column}}) as avg_price
                FROM `{{table_name}}`
                GROUP BY category, brand
            )
            SELECT category, brand,
            AI.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Generate {intel_types.lower()} for ', brand,
                ' in ', category, ' with ', CAST(product_count AS STRING), ' products'),
                STRUCT(0.5 AS temperature, 150 AS max_output_tokens)
            ) AS intelligence_report
            FROM market_data
            """

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=name,
            category=TemplateCategory.COMPETITOR_ANALYSIS,
            description=f'Competitor template {i}',
            template=template,
            parameters=_get_competitor_params(i),
            output_schema={'sku': 'STRING', 'analysis': 'STRING'}
        )

    # Templates 216-220: Strategic Analysis
    for i in range(216, 221):
        template_id = f'COMP_{i:03d}'
        strategy_types = [
            'Competitive Advantage', 'SWOT Analysis', 'Market Opportunity',
            'Threat Assessment', 'Differentiation Strategy'
        ]

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=f'{strategy_types[i-216]} Generator',
            category=TemplateCategory.COMPETITOR_ANALYSIS,
            description=f'Strategic: {strategy_types[i-216]}',
            template=f"""
            WITH strategic_context AS (
                SELECT {{brand_column}} as brand,
                {{category_column}} as category,
                COUNT(DISTINCT {{sku_column}}) as sku_count,
                AVG({{price_column}}) as avg_price,
                AVG({{rating_column}}) as avg_rating
                FROM `{{table_name}}`
                GROUP BY brand, category
            )
            SELECT brand, category,
            AI.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Create {strategy_types[i-216].lower()} for ', brand,
                ' in ', category, ' market. SKUs: ', CAST(sku_count AS STRING),
                ', Avg Price: $', CAST(avg_price AS STRING),
                ', Avg Rating: ', CAST(avg_rating AS STRING)),
                STRUCT(0.7 AS temperature, 300 AS max_output_tokens)
            ) AS strategic_analysis
            FROM strategic_context
            """,
            parameters=['table_name', 'model_name', 'brand_column', 'category_column',
                       'sku_column', 'price_column', 'rating_column'],
            output_schema={'brand': 'STRING', 'category': 'STRING', 'strategic_analysis': 'STRING'}
        )

    return templates
