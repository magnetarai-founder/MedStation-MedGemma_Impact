"""
Customer segmentation templates (SEG_236-SEG_256).
Moved from template_library_full.py for modular architecture.
"""

from typing import Dict, List
from .types import SQLTemplate, TemplateCategory


def _get_segmentation_params(template_num: int) -> List[str]:
    """Get parameters for segmentation templates"""
    if template_num == 236:
        return ['order_table', 'order_id', 'sku_column']
    else:
        return ['table_name', 'model_name', 'customer_column', 'entity_column',
               'feature_columns', 'id_column']


def get_templates() -> Dict[str, SQLTemplate]:
    """Return all CUSTOMER_SEGMENTATION templates (SEG_236–SEG_256)."""
    templates: Dict[str, SQLTemplate] = {}

    # Templates 236-245: Segmentation Analysis
    for i in range(236, 246):
        template_id = f'SEG_{i:03d}'

        if i == 236:
            name = 'Product Affinity Matrix'
            template = """
            WITH order_baskets AS (
                SELECT {order_id} as order_id,
                ARRAY_AGG(DISTINCT {sku_column}) as products
                FROM `{order_table}`
                GROUP BY order_id
                HAVING ARRAY_LENGTH(products) > 1
            ),
            product_pairs AS (
                SELECT p1 as product_a, p2 as product_b,
                COUNT(*) as co_occurrence
                FROM order_baskets,
                UNNEST(products) as p1,
                UNNEST(products) as p2
                WHERE p1 < p2
                GROUP BY product_a, product_b
                HAVING co_occurrence >= 10
            )
            SELECT product_a, product_b, co_occurrence,
            co_occurrence / (
                SELECT COUNT(DISTINCT {order_id})
                FROM `{order_table}`
                WHERE {sku_column} = product_a
            ) as confidence,
            co_occurrence / SQRT(
                (SELECT COUNT(DISTINCT {order_id}) FROM `{order_table}` WHERE {sku_column} = product_a) *
                (SELECT COUNT(DISTINCT {order_id}) FROM `{order_table}` WHERE {sku_column} = product_b)
            ) as lift
            FROM product_pairs
            ORDER BY lift DESC
            """
        elif i <= 240:
            segment_types = ['RFM Segmentation', 'Behavioral Clustering', 'Value Tiers',
                            'Lifecycle Stage', 'Preference Groups'][i-237]
            name = f'{segment_types} Builder'
            template = f"""
            WITH customer_features AS (
                SELECT {{customer_column}} as customer_id,
                {{feature_columns}}
                FROM `{{table_name}}`
            )
            SELECT customer_id,
            AI.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Assign {segment_types} segment based on: ',
                TO_JSON_STRING(STRUCT({{feature_columns}}))),
                STRUCT(0.3 AS temperature, 50 AS max_output_tokens)
            ) AS segment,
            AI.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Describe {segment_types} characteristics'),
                STRUCT(0.5 AS temperature, 100 AS max_output_tokens)
            ) AS segment_description
            FROM customer_features
            """
        else:
            behavior_types = ['Purchase Pattern', 'Channel Preference', 'Brand Loyalty',
                             'Price Sensitivity', 'Category Affinity'][i-241]
            name = f'{behavior_types} Analyzer'
            template = f"""
            SELECT {{entity_column}} as entity,
            AI.GENERATE_TABLE(
                MODEL `{{model_name}}`,
                TABLE (SELECT * FROM `{{table_name}}`),
                STRUCT('Analyze {behavior_types.lower()}. Output: pattern, score, recommendation' AS prompt)
            ).*
            FROM `{{table_name}}`
            GROUP BY entity
            """

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=name,
            category=TemplateCategory.CUSTOMER_SEGMENTATION,
            description=f'Segmentation template {i}',
            template=template,
            parameters=_get_segmentation_params(i),
            output_schema={'entity': 'STRING', 'segment': 'STRING', 'score': 'FLOAT64'}
        )

    # Templates 246-256: Advanced Segmentation
    for i in range(246, 257):
        template_id = f'SEG_{i:03d}'
        advanced_seg_types = [
            'Micro-segments', 'Predictive Segments', 'Dynamic Cohorts',
            'Cross-category Behavior', 'Multi-touch Attribution', 'CLV Segments',
            'Churn Risk Groups', 'Acquisition Channels', 'Engagement Levels',
            'Geographic Clusters', 'Psychographic Profiles'
        ]

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=f'{advanced_seg_types[i-246]} Creator',
            category=TemplateCategory.CUSTOMER_SEGMENTATION,
            description=f'Advanced: {advanced_seg_types[i-246]}',
            template=f"""
            WITH advanced_features AS (
                SELECT {{id_column}} as id,
                {{complex_features}}
                FROM `{{table_name}}`
                {{joins}}
            )
            SELECT id,
            AI.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Create {advanced_seg_types[i-246]} classification using: ',
                TO_JSON_STRING(STRUCT({{complex_features}}))),
                STRUCT(0.4 AS temperature, 100 AS max_output_tokens)
            ) AS advanced_segment,
            AI.GENERATE_DOUBLE(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Calculate {advanced_seg_types[i-246]} score (0-100)'),
                STRUCT(0.2 AS temperature)
            ) AS segment_score,
            AI.GENERATE_TABLE(
                MODEL `{{model_name}}`,
                TABLE advanced_features,
                STRUCT('Generate {advanced_seg_types[i-246]} insights. Output: insight, impact, action' AS prompt)
            ).*
            FROM advanced_features
            """,
            parameters=['table_name', 'model_name', 'id_column',
                       'complex_features', 'joins'],
            output_schema={'id': 'STRING', 'advanced_segment': 'STRING',
                          'segment_score': 'FLOAT64', 'insights': 'ARRAY<STRUCT>'}
        )

    return templates
