-- Staging model for CRM sales data
{{ config(materialized='view') }}

SELECT 
    sale_id,
    customer_id,
    product_id,
    sale_date,
    quantity,
    unit_price,
    total_amount,
    discount_amount,
    net_amount,
    sales_rep_id,
    channel,
    region,
    CURRENT_TIMESTAMP as loaded_at
FROM {{ source('crm', 'sales') }}
WHERE sale_id IS NOT NULL
  AND sale_date >= '2020-01-01'