-- Monthly sales summary mart
{{ config(materialized='table') }}

SELECT 
    sale_month_year,
    sale_year,
    sale_month,
    sale_quarter,
    region,
    channel,
    product_category,
    COUNT(DISTINCT sale_id) as total_orders,
    COUNT(DISTINCT customer_id) as unique_customers,
    COUNT(DISTINCT product_id) as unique_products,
    SUM(quantity) as total_quantity,
    SUM(total_amount) as total_revenue,
    SUM(discount_amount) as total_discounts,
    SUM(net_amount) as total_net_revenue,
    SUM(gross_profit) as total_gross_profit,
    AVG(net_amount) as avg_order_value,
    (SUM(gross_profit) / NULLIF(SUM(net_amount), 0)) * 100 as gross_margin_pct,
    CURRENT_TIMESTAMP as last_updated
FROM {{ ref('int_sales_enriched') }}
GROUP BY 
    sale_month_year,
    sale_year,
    sale_month,
    sale_quarter,
    region,
    channel,
    product_category