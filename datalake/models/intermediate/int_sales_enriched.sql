-- Intermediate model combining sales with product information
{{ config(materialized='view') }}

SELECT 
    swc.*,
    p.product_name,
    p.product_category,
    p.product_subcategory,
    p.brand,
    p.cost_price,
    p.list_price,
    (swc.net_amount - (p.cost_price * swc.quantity)) as gross_profit
FROM {{ ref('int_sales_with_customers') }} swc
LEFT JOIN {{ ref('stg_erp_products') }} p 
    ON swc.product_id = p.product_id