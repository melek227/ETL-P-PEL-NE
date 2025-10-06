-- Staging model for ERP inventory data
{{ config(materialized='view') }}

SELECT 
    inventory_id,
    product_id,
    warehouse_id,
    quantity_on_hand,
    quantity_reserved,
    quantity_available,
    reorder_point,
    max_stock_level,
    last_updated,
    CURRENT_TIMESTAMP as loaded_at
FROM {{ source('erp', 'inventory') }}
WHERE inventory_id IS NOT NULL