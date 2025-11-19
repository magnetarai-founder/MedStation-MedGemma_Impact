"""
Inventory optimization templates (INV_166-INV_185).
Moved from template_library_full.py for modular architecture.
"""

from typing import Dict, List
from .types import SQLTemplate, TemplateCategory


def _get_inventory_params(template_num: int) -> List[str]:
    """Get parameters for inventory templates"""
    if template_num == 166:
        return ['table_name', 'sku_column', 'daily_sales_column', 'date_column',
               'lead_time_days', 'current_stock_column']
    else:
        return ['table_name', 'model_name', 'sku_column', 'sales_column',
               'stock_column', 'cost_column']


def get_templates() -> Dict[str, SQLTemplate]:
    """Return all INVENTORY_OPTIMIZATION templates (INV_166–INV_185)."""
    templates: Dict[str, SQLTemplate] = {}

    # Templates 166-175: Stock Management
    for i in range(166, 176):
        template_id = f'INV_{i:03d}'

        if i == 166:
            name = 'Reorder Point Calculator'
            template = """
            WITH inventory_stats AS (
                SELECT {sku_column} as sku,
                AVG({daily_sales_column}) as avg_daily_sales,
                STDDEV({daily_sales_column}) as stddev_sales,
                {lead_time_days} as lead_time,
                {current_stock_column} as current_stock
                FROM `{table_name}`
                WHERE {date_column} >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
                GROUP BY sku, lead_time, current_stock
            )
            SELECT sku,
            avg_daily_sales * lead_time as lead_time_demand,
            1.65 * stddev_sales * SQRT(lead_time) as safety_stock,
            (avg_daily_sales * lead_time) + (1.65 * stddev_sales * SQRT(lead_time)) as reorder_point,
            current_stock,
            CASE
                WHEN current_stock < (avg_daily_sales * lead_time) + (1.65 * stddev_sales * SQRT(lead_time))
                THEN TRUE ELSE FALSE
            END as needs_reorder
            FROM inventory_stats
            """
        elif i <= 170:
            inventory_types = ['Safety Stock', 'EOQ', 'ABC Analysis',
                              'Stockout Risk', 'Overstock Detection'][i-167]
            name = f'{inventory_types} Calculator'
            template = f"""
            SELECT {{sku_column}} as sku,
            AI.GENERATE_DOUBLE(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Calculate {inventory_types.lower()} for SKU with ',
                'sales: ', CAST({{sales_column}} AS STRING),
                ', current stock: ', CAST({{stock_column}} AS STRING),
                ', cost: $', CAST({{cost_column}} AS STRING)),
                STRUCT(0.1 AS temperature)
            ) AS calculated_value,
            AI.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Explain {inventory_types.lower()} calculation'),
                STRUCT(0.3 AS temperature, 100 AS max_output_tokens)
            ) AS explanation
            FROM `{{table_name}}`
            """
        else:
            optimization_types = ['Warehouse Allocation', 'Seasonal Adjustment',
                                 'Slow-moving Detection', 'Bundle Optimization', 'JIT Analysis'][i-171]
            name = f'{optimization_types} Optimizer'
            template = f"""
            SELECT {{sku_column}} as sku,
            AI.GENERATE_TABLE(
                MODEL `{{model_name}}`,
                TABLE (SELECT * FROM `{{table_name}}`),
                STRUCT('Optimize {optimization_types.lower()}. Output: action, quantity, priority' AS prompt)
            ).*
            FROM `{{table_name}}`
            """

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=name,
            category=TemplateCategory.INVENTORY_OPTIMIZATION,
            description=f'Inventory template {i}',
            template=template,
            parameters=_get_inventory_params(i),
            output_schema={'sku': 'STRING', 'result': 'FLOAT64'}
        )

    # Templates 176-185: Supply Chain
    for i in range(176, 186):
        template_id = f'INV_{i:03d}'
        supply_types = [
            'Supplier Performance', 'Lead Time Analysis', 'Order Frequency',
            'Multi-location Stock', 'Demand Forecasting', 'Stock Transfer',
            'Expiry Management', 'Consignment Stock', 'Drop-ship Eligibility',
            'Inventory Turnover'
        ]

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=f'{supply_types[i-176]} Analyzer',
            category=TemplateCategory.INVENTORY_OPTIMIZATION,
            description=f'Supply chain: {supply_types[i-176]}',
            template=f"""
            WITH supply_metrics AS (
                SELECT {{sku_column}} as sku,
                {{supplier_column}} as supplier,
                AVG({{metric_column}}) as avg_metric,
                COUNT(*) as data_points
                FROM `{{table_name}}`
                GROUP BY sku, supplier
            )
            SELECT sku, supplier,
            AI.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Analyze {supply_types[i-176].lower()} for ', sku,
                ' from supplier ', supplier, ' with metric: ', CAST(avg_metric AS STRING)),
                STRUCT(0.3 AS temperature, 150 AS max_output_tokens)
            ) AS analysis,
            AI.GENERATE_DOUBLE(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Score {supply_types[i-176].lower()} (0-100)'),
                STRUCT(0.2 AS temperature)
            ) AS performance_score
            FROM supply_metrics
            """,
            parameters=['table_name', 'model_name', 'sku_column',
                       'supplier_column', 'metric_column'],
            output_schema={'sku': 'STRING', 'supplier': 'STRING',
                          'analysis': 'STRING', 'performance_score': 'FLOAT64'}
        )

    return templates
