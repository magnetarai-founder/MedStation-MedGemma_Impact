WITH sales_data AS (
SELECT *,
SALES,
SUM(SALES) OVER () AS TOTAL_SALES,
SUM(SALES) OVER (ORDER BY SALES DESC) AS RUNNING_TOTAL
FROM excel_file
)

SELECT
VARIABLE_WEIGHT::int as variable_weight
,MERCHANT_NAME::text as merchant_name
,LPAD(MERCHANT_SKU::text, 12, '0') as sku
,'UPC'::text as type_of_barcode
,LPAD(BARCODE::text, 12, '0') as barcode
,PRODUCT_NAME::text as product_name
,CASE
    WHEN BRAND_NAME IS NOT NULL AND TRIM(LOWER(BRAND_NAME)) NOT IN ('', 'no brand', 'nan', 'na', 'null')
        THEN BRAND_NAME
    WHEN VARIABLE_WEIGHT = 1 THEN
        CASE 
            WHEN LOWER(CATEGORY) LIKE '%produce%' THEN 'Fresh Produce'
            WHEN LOWER(CATEGORY) LIKE '%meat%' THEN 'Fresh Meat'
            WHEN LOWER(CATEGORY) LIKE '%seafood%' THEN 'Fresh Seafood'
            ELSE ''
        END
    ELSE ''
END::text as brand_name

,DESCRIPTION::text as description
,BULLET_POINT_1::text as bullet_point_1
,FAMILY::text as family
,CATEGORY::text as category
,SUB_CATEGORY::text as subcategory

-- Handle unit size
,case
    when UNIT_SIZE::decimal % 1 = 0 then trim(leading '0' from UNIT_SIZE::decimal::int::text)
    else trim(leading '0' from UNIT_SIZE)
end::text as unit_size

,trim(UNIT_OF_MEASURE)::text as unit_of_measure

-- Handle pack quantity
,case
    when upper(PRODUCT_NAME) ~ '[0-9]+\s*(PACK|PK)\b' then
        TRIM(REGEXP_EXTRACT(upper(PRODUCT_NAME), '([0-9]+)\s*(PACK|PK)', 1))::int
    when upper(PRODUCT_NAME) ~ '[0-9]+\s*(COUNT|CT)\b' then
        TRIM(REGEXP_EXTRACT(upper(PRODUCT_NAME), '([0-9]+)\s*(COUNT|CT)', 1))::int
    else 1
end as item_pack_quantity

,TOTAL_EACHES::int as total_eaches
,MAX_ORDER_QUANTITY::int as max_order_quantity

-- Handle images
,coalesce(nullif(MAIN_IMAGE_URL, 'nan'), nullif(IMAGE_URL_2, 'nan'), nullif(IMAGE_URL_3, 'nan'), nullif(IMAGE_URL_4, 'nan'), '')::text as main_image_url
,case when coalesce(nullif(MAIN_IMAGE_URL, 'nan'), '') != '' then coalesce(nullif(IMAGE_URL_2, 'nan'), '')
      when coalesce(nullif(IMAGE_URL_2, 'nan'), '') != '' then coalesce(nullif(IMAGE_URL_3, 'nan'), '')
      when coalesce(nullif(IMAGE_URL_3, 'nan'), '') != '' then coalesce(nullif(IMAGE_URL_4, 'nan'), '')
      else ''
end::text as other_image_url_1
,case when coalesce(nullif(MAIN_IMAGE_URL, 'nan'), '') != '' and coalesce(nullif(IMAGE_URL_2, 'nan'), '') != '' then coalesce(nullif(IMAGE_URL_3, 'nan'), '')
      when coalesce(nullif(IMAGE_URL_2, 'nan'), '') != '' and coalesce(nullif(IMAGE_URL_3, 'nan'), '') != '' then coalesce(nullif(IMAGE_URL_4, 'nan'), '')
      else ''
end::text as other_image_url_2
,case when coalesce(nullif(MAIN_IMAGE_URL, 'nan'), '') != '' and coalesce(nullif(IMAGE_URL_2, 'nan'), '') != '' and coalesce(nullif(IMAGE_URL_3, 'nan'), '') != '' then coalesce(nullif(IMAGE_URL_4, 'nan'), '')
      else ''
end::text as other_image_url_3

,case when VARIABLE_WEIGHT = 1 then PRICING_STRATEGY else null end::text as pricing_strategy
,COALESCE(
    CASE
        when VARIABLE_WEIGHT = 1 and PRICING_STRATEGY = 'catch_by_uom' then '0.5'
        when VARIABLE_WEIGHT = 1 and PRICING_STRATEGY = 'produce_by_uom' then '1'
        else ''
    END, 'null'
)::text as minimum_order_amount
,case 
    when VARIABLE_WEIGHT = 1 then MAX_ORDER_QUANTITY::decimal(9,2)
    else null
end::decimal(9,2) as maximum_order_amount

,case
    when VARIABLE_WEIGHT = 1 then AVERAGE_WEIGHT::decimal(9,2)
    else null
end::decimal(9,2) as average_size_per_merchant_uom

,case
    when VARIABLE_WEIGHT = 1 and PRICING_STRATEGY = 'catch_by_uom' then 0.5
    when VARIABLE_WEIGHT = 1 and PRICING_STRATEGY = 'produce_by_uom' then 1
    else null
end::decimal(9,2) as order_increment

,SALES::decimal(18,2) as sales
,(RUNNING_TOTAL / TOTAL_SALES * 100)::decimal(5,2) as cumulative_sales_percentage

FROM sales_data
ORDER BY SALES DESC