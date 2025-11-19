"""
Product enrichment templates (ENRICH_001-ENRICH_050).
Moved from template_library_full.py for modular architecture.
"""

from typing import Dict, List
from .types import SQLTemplate, TemplateCategory


def _get_params_for_template(template_num: int) -> List[str]:
    """Get parameters for product enrichment templates 1–10."""
    if template_num <= 10:
        specific_params = [
            ['brand_column', 'name_column', 'category_column', 'attribute_column', 'description_column'],
            ['brand_column', 'name_column', 'material_column', 'size_column', 'color_column',
             'weight_column', 'features_column'],
            ['brand_column', 'name_column', 'category_column', 'key_attribute_column', 'seo_title_column'],
            ['name_column', 'brand_column', 'category_column', 'meta_desc_column'],
            ['category_column', 'size_chart_column'],
            ['material_column', 'category_column', 'care_column'],
            ['category_column', 'compat_column'],
            ['name_column', 'category_column', 'usage_column'],
            ['brand_column', 'category_column', 'price_column', 'warranty_column'],
            ['category_column', 'price_column'],
        ]
        return specific_params[template_num - 1]
    return []


def get_templates() -> Dict[str, SQLTemplate]:
    """Return all PRODUCT_ENRICHMENT templates (ENRICH_001–ENRICH_050)."""
    templates: Dict[str, SQLTemplate] = {}

    # Templates 1-10: Basic Product Enrichment
    for i in range(1, 11):
        template_id = f'ENRICH_{i:03d}'

        if i == 1:
            name = 'Basic Product Description'
            template = """
            WITH product_base AS (
                SELECT {sku_column} as sku, {brand_column} as brand, {name_column} as product_name,
                {category_column} as category, ARRAY_AGG(DISTINCT {attribute_column} IGNORE NULLS) as attributes
                FROM `{table_name}` WHERE {description_column} IS NULL GROUP BY 1,2,3,4
            ),
            context_samples AS (
                SELECT {description_column} as sample_description, {category_column} as category
                FROM `{table_name}` WHERE {description_column} IS NOT NULL LIMIT 5
            )
            SELECT p.sku, ML.GENERATE_TEXT(
                MODEL `{model_name}`,
                PROMPT => CONCAT('Generate product description for: ', p.brand, ' ', p.product_name,
                ' in category ', p.category, ' with attributes: ', ARRAY_TO_STRING(p.attributes, ', ')),
                STRUCT(0.7 AS temperature, 150 AS max_output_tokens)
            ) AS generated_description
            FROM product_base p
            """
        elif i == 2:
            name = 'Feature Bullet Generation'
            template = """
            SELECT {sku_column} as sku,
            AI.GENERATE_TABLE(
                MODEL `{model_name}`,
                TABLE (SELECT * FROM `{table_name}` WHERE {features_column} IS NULL),
                STRUCT('Generate 5 bullet points. Output columns: bullet1, bullet2, bullet3, bullet4, bullet5' AS prompt)
            ).*
            FROM `{table_name}` WHERE {features_column} IS NULL
            """
        elif i == 3:
            name = 'SEO Title Generator'
            template = """
            SELECT {sku_column} as sku,
            ML.GENERATE_TEXT(
                MODEL `{model_name}`,
                PROMPT => CONCAT('Create SEO title 50-80 chars for: ', {brand_column}, ' ', {name_column}),
                STRUCT(0.3 AS temperature, 20 AS max_output_tokens)
            ) AS seo_title
            FROM `{table_name}` WHERE {seo_title_column} IS NULL
            """
        elif i == 4:
            name = 'Meta Description Creator'
            template = """
            SELECT {sku_column} as sku,
            ML.GENERATE_TEXT(
                MODEL `{model_name}`,
                PROMPT => CONCAT('Create meta description 150-160 chars for: ', {name_column},
                '. Include brand: ', {brand_column}, ', category: ', {category_column}),
                STRUCT(0.5 AS temperature, 50 AS max_output_tokens)
            ) AS meta_description
            FROM `{table_name}` WHERE {meta_desc_column} IS NULL
            """
        elif i == 5:
            name = 'Size Chart Generator'
            template = """
            SELECT {sku_column} as sku, {category_column} as category,
            AI.GENERATE_TABLE(
                MODEL `{model_name}`,
                TABLE (SELECT * FROM `{table_name}` WHERE {size_chart_column} IS NULL),
                STRUCT('Generate size chart. Output columns: size, chest, waist, hips, length' AS prompt)
            ).*
            FROM `{table_name}` WHERE {size_chart_column} IS NULL AND {category_column} IN ('Clothing', 'Apparel')
            """
        elif i == 6:
            name = 'Care Instructions'
            template = """
            SELECT {sku_column} as sku,
            ML.GENERATE_TEXT(
                MODEL `{model_name}`,
                PROMPT => CONCAT('Generate care instructions for ', {material_column}, ' ', {category_column}),
                STRUCT(0.2 AS temperature, 100 AS max_output_tokens)
            ) AS care_instructions
            FROM `{table_name}` WHERE {care_column} IS NULL AND {material_column} IS NOT NULL
            """
        elif i == 7:
            name = 'Compatibility Info'
            template = """
            SELECT {sku_column} as sku,
            AI.GENERATE_TABLE(
                MODEL `{model_name}`,
                TABLE (SELECT * FROM `{table_name}` WHERE {compat_column} IS NULL),
                STRUCT('List compatible products. Output columns: compatible_with, compatibility_type' AS prompt)
            ).*
            FROM `{table_name}` WHERE {category_column} IN ('Electronics', 'Accessories')
            """
        elif i == 8:
            name = 'Usage Instructions'
            template = """
            SELECT {sku_column} as sku,
            ML.GENERATE_TEXT(
                MODEL `{model_name}`,
                PROMPT => CONCAT('Create usage guide for: ', {name_column}, ' in category ', {category_column}),
                STRUCT(0.4 AS temperature, 200 AS max_output_tokens)
            ) AS usage_guide
            FROM `{table_name}` WHERE {usage_column} IS NULL
            """
        elif i == 9:
            name = 'Warranty Info Generator'
            template = """
            SELECT {sku_column} as sku,
            ML.GENERATE_TEXT(
                MODEL `{model_name}`,
                PROMPT => CONCAT('Generate warranty terms for ', {brand_column}, ' ', {category_column},
                '. Price: $', CAST({price_column} AS STRING)),
                STRUCT(0.1 AS temperature, 150 AS max_output_tokens)
            ) AS warranty_info
            FROM `{table_name}` WHERE {warranty_column} IS NULL
            """
        else:  # i == 10
            name = 'Return Policy Generator'
            template = """
            SELECT {sku_column} as sku,
            AI.GENERATE_BOOL(
                MODEL `{model_name}`,
                PROMPT => CONCAT('Is this item returnable? ', {category_column}, ', Price: $', CAST({price_column} AS STRING)),
                STRUCT(0.1 AS temperature)
            ) AS is_returnable,
            AI.GENERATE_INT(
                MODEL `{model_name}`,
                PROMPT => CONCAT('Return window in days for ', {category_column}),
                STRUCT(0.1 AS temperature)
            ) AS return_days
            FROM `{table_name}`
            """

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=name,
            category=TemplateCategory.PRODUCT_ENRICHMENT,
            description=f'Enrichment template {i}',
            template=template,
            parameters=['table_name', 'model_name', 'sku_column'] + _get_params_for_template(i),
            output_schema={'sku': 'STRING', 'result': 'STRING'}
        )

    # Templates 11-20: Advanced Product Content
    for i in range(11, 21):
        template_id = f'ENRICH_{i:03d}'
        enrichment_types = [
            'Ingredient List', 'Nutritional Info', 'Technical Specs',
            'Safety Warnings', 'Assembly Instructions', 'Video Script',
            'Social Media Caption', 'Email Subject Line', 'Ad Copy', 'FAQ Section'
        ]

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=f'{enrichment_types[i-11]} Generator',
            category=TemplateCategory.PRODUCT_ENRICHMENT,
            description=f'Generate {enrichment_types[i-11].lower()}',
            template=f"""
            SELECT {{sku_column}} as sku,
            ML.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Generate {enrichment_types[i-11].lower()} for: ',
                {{name_column}}, ' by ', {{brand_column}}),
                STRUCT(0.6 AS temperature, 150 AS max_output_tokens)
            ) AS generated_content
            FROM `{{table_name}}`
            WHERE {{content_column}} IS NULL
            """,
            parameters=['table_name', 'model_name', 'sku_column', 'name_column',
                       'brand_column', 'content_column'],
            output_schema={'sku': 'STRING', 'generated_content': 'STRING'}
        )

    # Templates 21-30: Localization & Translation
    for i in range(21, 31):
        template_id = f'ENRICH_{i:03d}'
        languages = ['Spanish', 'French', 'German', 'Italian', 'Portuguese',
                    'Japanese', 'Chinese', 'Korean', 'Arabic', 'Hindi']

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=f'{languages[i-21]} Translation',
            category=TemplateCategory.PRODUCT_ENRICHMENT,
            description=f'Translate to {languages[i-21]}',
            template=f"""
            SELECT {{sku_column}} as sku,
            ML.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Translate to {languages[i-21]}: ', {{text_column}}),
                STRUCT(0.1 AS temperature, 200 AS max_output_tokens)
            ) AS translated_text
            FROM `{{table_name}}`
            WHERE {{target_lang_column}} = '{languages[i-21]}'
            """,
            parameters=['table_name', 'model_name', 'sku_column',
                       'text_column', 'target_lang_column'],
            output_schema={'sku': 'STRING', 'translated_text': 'STRING'}
        )

    # Templates 31-40: Marketing Content
    for i in range(31, 41):
        template_id = f'ENRICH_{i:03d}'
        marketing_types = [
            'Instagram Post', 'Twitter Thread', 'Blog Intro', 'Press Release',
            'Product Launch Email', 'Discount Banner', 'Push Notification',
            'SMS Campaign', 'Affiliate Description', 'Marketplace Listing'
        ]

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=f'{marketing_types[i-31]} Creator',
            category=TemplateCategory.PRODUCT_ENRICHMENT,
            description=f'Create {marketing_types[i-31].lower()}',
            template=f"""
            SELECT {{sku_column}} as sku,
            ML.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Create {marketing_types[i-31].lower()} for: ',
                {{product_column}}, '. Target audience: ', {{audience_column}}),
                STRUCT(0.8 AS temperature, 100 AS max_output_tokens)
            ) AS marketing_content
            FROM `{{table_name}}`
            WHERE {{campaign_type}} = '{marketing_types[i-31]}'
            """,
            parameters=['table_name', 'model_name', 'sku_column',
                       'product_column', 'audience_column', 'campaign_type'],
            output_schema={'sku': 'STRING', 'marketing_content': 'STRING'}
        )

    # Templates 41-50: Personalization
    for i in range(41, 51):
        template_id = f'ENRICH_{i:03d}'
        personas = [
            'Budget Conscious', 'Premium Shopper', 'Eco Friendly', 'Tech Savvy',
            'Fashion Forward', 'Health Conscious', 'Parent', 'Student',
            'Professional', 'Senior'
        ]

        templates[template_id] = SQLTemplate(
            id=template_id,
            name=f'{personas[i-41]} Persona Content',
            category=TemplateCategory.PRODUCT_ENRICHMENT,
            description=f'Personalized for {personas[i-41]}',
            template=f"""
            SELECT {{sku_column}} as sku,
            ML.GENERATE_TEXT(
                MODEL `{{model_name}}`,
                PROMPT => CONCAT('Create description for {personas[i-41]} customer: ',
                {{product_column}}, '. Emphasize: ',
                CASE '{personas[i-41]}'
                    WHEN 'Budget Conscious' THEN 'value and savings'
                    WHEN 'Premium Shopper' THEN 'quality and exclusivity'
                    WHEN 'Eco Friendly' THEN 'sustainability and environmental impact'
                    ELSE 'key benefits'
                END),
                STRUCT(0.7 AS temperature, 150 AS max_output_tokens)
            ) AS personalized_content
            FROM `{{table_name}}`
            WHERE {{persona_column}} = '{personas[i-41]}'
            """,
            parameters=['table_name', 'model_name', 'sku_column',
                       'product_column', 'persona_column'],
            output_schema={'sku': 'STRING', 'personalized_content': 'STRING'}
        )

    return templates
