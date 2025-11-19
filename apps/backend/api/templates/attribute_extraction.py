"""
Attribute extraction templates (EXTRACT_051-EXTRACT_090).
Moved from template_library_full.py for modular architecture.
"""

from typing import Dict, List
from .types import SQLTemplate, TemplateCategory


def get_templates() -> Dict[str, SQLTemplate]:
    """Return all ATTRIBUTE_EXTRACTION templates (EXTRACT_051–EXTRACT_090)."""
    templates: Dict[str, SQLTemplate] = {}

    # Templates 51-60: Basic Extractions
    for i in range(51, 61):
        template_id = f'EXTRACT_{i:03d}'
        extraction_types = [
            ('Size', r'(\d+(?:\.\d+)?)\s*(?:x|X)\s*(\d+(?:\.\d+)?)'),
            ('Color', r'(?i)(black|white|red|blue|green|yellow|purple|orange|pink|gray|brown)'),
            ('Material', r'(?i)(cotton|polyester|leather|wool|silk|nylon|denim|suede|canvas|linen)'),
            ('Weight', r'(\d+(?:\.\d+)?)\s*(?:lb|lbs|pound|pounds|kg|kilogram|g|gram|oz|ounce)'),
            ('Dimensions', r'(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)'),
            ('Model Number', r'(?i)(?:model|part)\s*(?:number|#|no\.?)?:?\s*([A-Z0-9\-]+)'),
            ('SKU', r'(?i)(?:sku|item)\s*(?:number|#|no\.?)?:?\s*([A-Z0-9\-]+)'),
            ('Price', r'\$?\s*(\d+(?:\.\d{2})?)'),
            ('Quantity', r'(\d+)\s*(?:pack|count|pieces|pcs|units)'),
            ('Voltage', r'(\d+(?:\.\d+)?)\s*[vV](?:olts?)?')
        ]

        extraction_type, pattern = extraction_types[i-51]

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=f'{extraction_type} Extraction',
            category=TemplateCategory.ATTRIBUTE_EXTRACTION,
            description=f'Extract {extraction_type.lower()} from text',
            template=f"""
            WITH extracted AS (
                SELECT {{sku_column}} as sku, {{text_column}} as full_text,
                REGEXP_EXTRACT({{text_column}}, r'{pattern}') as regex_extract,
                REGEXP_EXTRACT_ALL({{text_column}}, r'{pattern}') as all_matches
                FROM `{{table_name}}` WHERE {{{extraction_type.lower()}_column}} IS NULL
            )
            SELECT sku,
            COALESCE(
                regex_extract,
                CASE WHEN ARRAY_LENGTH(all_matches) > 0 THEN all_matches[OFFSET(0)] ELSE NULL END,
                ML.GENERATE_TEXT(
                    MODEL `{{model_name}}`,
                    PROMPT => CONCAT('Extract {extraction_type.lower()} from: ', full_text),
                    STRUCT(0.1 AS temperature, 20 AS max_output_tokens)
                )
            ) AS extracted_{extraction_type.lower()}
            FROM extracted
            """,
            parameters=['table_name', 'model_name', 'sku_column', 'text_column',
                       f'{extraction_type.lower()}_column'],
            output_schema={'sku': 'STRING', f'extracted_{extraction_type.lower()}': 'STRING'}
        )

    # Templates 61-70: Advanced Extractions
    for i in range(61, 71):
        template_id = f'EXTRACT_{i:03d}'
        advanced_types = [
            'Certification', 'Warranty Period', 'Battery Life', 'Screen Size',
            'Storage Capacity', 'Processor Speed', 'Camera Resolution',
            'Water Resistance', 'Energy Rating', 'Noise Level'
        ]

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=f'{advanced_types[i-61]} Extractor',
            category=TemplateCategory.ATTRIBUTE_EXTRACTION,
            description=f'Extract {advanced_types[i-61].lower()}',
            template=f"""
            SELECT {{sku_column}} as sku,
            ML.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Extract {advanced_types[i-61].lower()} from: ', {{text_column}},
                '. Return only the value, no explanation.'),
                STRUCT(0.1 AS temperature, 30 AS max_output_tokens)
            ) AS extracted_value,
            AI.GENERATE_BOOL(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Does this text mention {advanced_types[i-61].lower()}? ', {{text_column}}),
                STRUCT(0.1 AS temperature)
            ) AS has_attribute
            FROM `{{table_name}}`
            WHERE {{attribute_column}} IS NULL
            """,
            parameters=['table_name', 'model_name', 'sku_column',
                       'text_column', 'attribute_column'],
            output_schema={'sku': 'STRING', 'extracted_value': 'STRING', 'has_attribute': 'BOOL'}
        )

    # Templates 71-80: Multi-value Extractions
    for i in range(71, 81):
        template_id = f'EXTRACT_{i:03d}'
        multi_types = [
            'All Colors', 'All Sizes', 'All Materials', 'Features List',
            'Included Items', 'Compatible Devices', 'Available Variants',
            'Allergens', 'Ingredients', 'Benefits'
        ]

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=f'{multi_types[i-71]} List Extractor',
            category=TemplateCategory.ATTRIBUTE_EXTRACTION,
            description=f'Extract list of {multi_types[i-71].lower()}',
            template=f"""
            SELECT {{sku_column}} as sku,
            AI.GENERATE_TABLE(
                MODEL `{{model_name}}`,
                TABLE (SELECT {{sku_column}}, {{text_column}} FROM `{{table_name}}`),
                STRUCT('Extract all {multi_types[i-71].lower()}. Output column: value' AS prompt)
            ).value AS extracted_list
            FROM `{{table_name}}`
            WHERE {{list_column}} IS NULL
            """,
            parameters=['table_name', 'model_name', 'sku_column',
                       'text_column', 'list_column'],
            output_schema={'sku': 'STRING', 'extracted_list': 'ARRAY<STRING>'}
        )

    # Templates 81-90: Numeric Extractions
    for i in range(81, 91):
        template_id = f'EXTRACT_{i:03d}'
        numeric_types = [
            ('Length', 'inches'), ('Width', 'inches'), ('Height', 'inches'),
            ('Weight', 'pounds'), ('Volume', 'liters'), ('Speed', 'mph'),
            ('Temperature', 'fahrenheit'), ('Pressure', 'psi'),
            ('Distance', 'miles'), ('Duration', 'hours')
        ]

        measure, unit = numeric_types[i-81]

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=f'{measure} in {unit} Extractor',
            category=TemplateCategory.ATTRIBUTE_EXTRACTION,
            description=f'Extract {measure.lower()} in {unit}',
            template=f"""
            SELECT {{sku_column}} as sku,
            AI.GENERATE_DOUBLE(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Extract {measure.lower()} in {unit} from: ', {{text_column}},
                '. Return only the numeric value.'),
                STRUCT(0.1 AS temperature)
            ) AS {measure.lower()}_{unit},
            ML.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('What unit is the {measure.lower()} given in? ', {{text_column}}),
                STRUCT(0.1 AS temperature, 10 AS max_output_tokens)
            ) AS original_unit
            FROM `{{table_name}}`
            WHERE {{{measure.lower()}_column}} IS NULL
            """,
            parameters=['table_name', 'model_name', 'sku_column',
                       'text_column', f'{measure.lower()}_column'],
            output_schema={'sku': 'STRING', f'{measure.lower()}_{unit}': 'FLOAT64',
                          'original_unit': 'STRING'}
        )

    return templates
