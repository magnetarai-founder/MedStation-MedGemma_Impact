"""
Trend detection templates (TREND_221-TREND_235).
Moved from template_library_full.py for modular architecture.
"""

from typing import Dict, List
from .types import SQLTemplate, TemplateCategory


def _get_trend_params(template_num: int) -> List[str]:
    """Get parameters for trend templates"""
    if template_num == 221:
        return ['sales_table', 'date_column', 'sku_column', 'category_column',
               'quantity_column', 'revenue_column']
    else:
        return ['table_name', 'model_name', 'time_column', 'dimension_column',
               'metric_column']


def get_templates() -> Dict[str, SQLTemplate]:
    """Return all TREND_DETECTION templates (TREND_221–TREND_235)."""
    templates: Dict[str, SQLTemplate] = {}

    # Templates 221-230: Trend Analysis
    for i in range(221, 231):
        template_id = f'TREND_{i:03d}'

        if i == 221:
            name = 'Sales Trend Detector'
            template = """
            WITH weekly_sales AS (
                SELECT DATE_TRUNC({date_column}, WEEK) as week,
                {sku_column} as sku, {category_column} as category,
                SUM({quantity_column}) as units_sold,
                SUM({revenue_column}) as revenue
                FROM `{sales_table}`
                WHERE {date_column} >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 WEEK)
                GROUP BY week, sku, category
            ),
            trend_calc AS (
                SELECT sku, category,
                units_sold,
                LAG(units_sold, 4) OVER (PARTITION BY sku ORDER BY week) as units_4w_ago,
                AVG(units_sold) OVER (PARTITION BY sku ORDER BY week ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) as avg_prev
                FROM weekly_sales
            )
            SELECT sku, category,
            SAFE_DIVIDE(units_sold - units_4w_ago, units_4w_ago) * 100 as growth_4w,
            CASE
                WHEN SAFE_DIVIDE(units_sold - avg_prev, avg_prev) > 0.5 THEN 'Hot Trend'
                WHEN SAFE_DIVIDE(units_sold - units_4w_ago, units_4w_ago) < -0.3 THEN 'Declining'
                ELSE 'Stable'
            END as trend_status
            FROM trend_calc
            WHERE week = DATE_TRUNC(CURRENT_DATE(), WEEK)
            """
        elif i <= 225:
            trend_types = ['Seasonal Pattern', 'Customer Preference', 'Price Sensitivity',
                          'Category Shift', 'Brand Momentum'][i-222]
            name = f'{trend_types} Tracker'
            template = f"""
            SELECT {{time_column}} as time_period,
            {{dimension_column}} as dimension,
            AI.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Analyze {trend_types.lower()} trend for ',
                {{dimension_column}}, ' over time'),
                STRUCT(0.4 AS temperature, 150 AS max_output_tokens)
            ) AS trend_analysis,
            AI.GENERATE_DOUBLE(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Trend strength score (0-100) for {trend_types.lower()}'),
                STRUCT(0.2 AS temperature)
            ) AS trend_score
            FROM `{{table_name}}`
            GROUP BY time_period, dimension
            """
        else:
            forecast_types = ['Demand Forecast', 'Trend Extrapolation', 'Seasonality Adjustment',
                             'Growth Projection', 'Market Saturation'][i-226]
            name = f'{forecast_types} Model'
            template = f"""
            WITH historical_data AS (
                SELECT {{time_column}} as period,
                {{metric_column}} as value
                FROM `{{table_name}}`
                ORDER BY period
            )
            SELECT
            AI.FORECAST(
                MODEL `{{model_name}}`,
                TABLE historical_data,
                STRUCT(
                    30 AS horizon,
                    0.95 AS confidence_level,
                    '{forecast_types}' AS forecast_type
                )
            ).*
            FROM historical_data
            """

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=name,
            category=TemplateCategory.TREND_DETECTION,
            description=f'Trend template {i}',
            template=template,
            parameters=_get_trend_params(i),
            output_schema={'time': 'DATE', 'trend': 'STRING', 'score': 'FLOAT64'}
        )

    # Templates 231-235: Predictive Analytics
    for i in range(231, 236):
        template_id = f'TREND_{i:03d}'
        predictive_types = [
            'Next Best Action', 'Churn Prediction', 'Cross-sell Opportunity',
            'Stock-out Risk', 'Viral Potential'
        ]

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=f'{predictive_types[i-231]} Predictor',
            category=TemplateCategory.TREND_DETECTION,
            description=f'Predict {predictive_types[i-231]}',
            template=f"""
            WITH prediction_features AS (
                SELECT {{id_column}} as id,
                {{feature1_column}} as feature1,
                {{feature2_column}} as feature2,
                {{feature3_column}} as feature3
                FROM `{{table_name}}`
            )
            SELECT id,
            AI.GENERATE_BOOL(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Predict {predictive_types[i-231]} likelihood for entity with: ',
                'Feature1: ', CAST(feature1 AS STRING),
                ', Feature2: ', CAST(feature2 AS STRING),
                ', Feature3: ', CAST(feature3 AS STRING)),
                STRUCT(0.2 AS temperature)
            ) AS prediction,
            AI.GENERATE_DOUBLE(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Confidence score (0-1) for {predictive_types[i-231]} prediction'),
                STRUCT(0.1 AS temperature)
            ) AS confidence
            FROM prediction_features
            """,
            parameters=['table_name', 'model_name', 'id_column',
                       'feature1_column', 'feature2_column', 'feature3_column'],
            output_schema={'id': 'STRING', 'prediction': 'BOOL', 'confidence': 'FLOAT64'}
        )

    return templates
