-- Product performance mart
{{ config(materialized='table') }}

SELECT 
    p.product_id,
    p.product_name,
    p.product_category,
    p.product_subcategory,
    p.brand,
    p.cost_price,
    p.list_price,
    COALESCE(sales_metrics.total_quantity_sold, 0) as total_quantity_sold,
    COALESCE(sales_metrics.total_revenue, 0) as total_revenue,
    COALESCE(sales_metrics.total_gross_profit, 0) as total_gross_profit,
    COALESCE(sales_metrics.avg_selling_price, 0) as avg_selling_price,
    COALESCE(sales_metrics.total_orders, 0) as total_orders,
    COALESCE(sales_metrics.unique_customers, 0) as unique_customers,
    COALESCE(inv.quantity_on_hand, 0) as current_inventory,
    COALESCE(inv.quantity_available, 0) as available_inventory,
    CASE 
        WHEN sales_metrics.total_quantity_sold > 0 THEN 'Active'
        ELSE 'Inactive'
    END as sales_status,
    CURRENT_TIMESTAMP as last_updated
FROM {{ ref('stg_erp_products') }} p
LEFT JOIN (
    SELECT 
        product_id,
        SUM(quantity) as total_quantity_sold,
        SUM(net_amount) as total_revenue,
        SUM(gross_profit) as total_gross_profit,
        AVG(unit_price) as avg_selling_price,
        COUNT(DISTINCT sale_id) as total_orders,
        COUNT(DISTINCT customer_id) as unique_customers
    FROM {{ ref('int_sales_enriched') }}
    GROUP BY product_id
) sales_metrics ON p.product_id = sales_metrics.product_id
LEFT JOIN {{ ref('stg_erp_inventory') }} inv ON p.product_id = inv.product_id