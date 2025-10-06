-- Staging model for ERP product data
{{ config(materialized='view') }}

SELECT 
    product_id,
    TRIM(product_name) as product_name,
    TRIM(product_category) as product_category,
    TRIM(product_subcategory) as product_subcategory,
    brand,
    supplier_id,
    cost_price,
    list_price,
    weight,
    dimensions,
    product_status,
    created_date,
    updated_date,
    CURRENT_TIMESTAMP as loaded_at
FROM {{ source('erp', 'products') }}
WHERE product_id IS NOT NULL