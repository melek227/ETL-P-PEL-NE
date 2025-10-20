-- Temizlenmiş sipariş tablosu (Intermediate)
{{ config(materialized='view') }}

SELECT
    order_id,
    customer_id,
    order_date,
    total_amount,
    order_category
FROM {{ ref('stg_erp_orders') }}
WHERE order_id IS NOT NULL
  AND customer_id IS NOT NULL
  AND total_amount >= 0