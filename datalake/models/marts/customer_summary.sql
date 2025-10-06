-- Sales summary mart by customer
{{ config(materialized='table') }}

SELECT 
    customer_id,
    first_name,
    last_name,
    email,
    customer_type,
    customer_status,
    COUNT(DISTINCT sale_id) as total_orders,
    SUM(quantity) as total_quantity,
    SUM(total_amount) as total_revenue,
    SUM(discount_amount) as total_discounts,
    SUM(net_amount) as total_net_revenue,
    SUM(gross_profit) as total_gross_profit,
    AVG(net_amount) as avg_order_value,
    MIN(sale_date) as first_purchase_date,
    MAX(sale_date) as last_purchase_date,
    COUNT(DISTINCT product_category) as categories_purchased,
    COUNT(DISTINCT brand) as brands_purchased,
    CURRENT_TIMESTAMP as last_updated
FROM {{ ref('int_sales_enriched') }}
GROUP BY 
    customer_id,
    first_name,
    last_name,
    email,
    customer_type,
    customer_status