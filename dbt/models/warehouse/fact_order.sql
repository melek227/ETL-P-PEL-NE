-- Order Fact Table
{{ config(materialized='table') }}

SELECT
    order_id,
    customer_id,
    order_date,
    total_amount,
    order_category
FROM {{ ref('int_order_cleaned') }}
WHERE order_id IS NOT NULL AND customer_id IS NOT NULL