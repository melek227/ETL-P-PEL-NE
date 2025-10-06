-- Intermediate model combining customer and sales data
{{ config(materialized='view') }}

SELECT 
    s.sale_id,
    s.customer_id,
    c.first_name,
    c.last_name,
    c.email,
    c.customer_type,
    c.customer_status,
    s.product_id,
    s.sale_date,
    s.quantity,
    s.unit_price,
    s.total_amount,
    s.discount_amount,
    s.net_amount,
    s.sales_rep_id,
    s.channel,
    s.region,
    EXTRACT(YEAR FROM s.sale_date) as sale_year,
    EXTRACT(MONTH FROM s.sale_date) as sale_month,
    EXTRACT(QUARTER FROM s.sale_date) as sale_quarter,
    DATE_TRUNC('month', s.sale_date) as sale_month_year
FROM {{ ref('stg_crm_sales') }} s
LEFT JOIN {{ ref('stg_crm_customers') }} c 
    ON s.customer_id = c.customer_id