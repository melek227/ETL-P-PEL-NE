-- Staging ERP orders - temizleme ve zenginleştirme
{{ config(materialized='view') }}

WITH cleaned_orders AS (
    SELECT 
        order_id,
        customer_id,
        TRIM(product_name) as product_name_clean,
        quantity,
        unit_price,
        order_date,
        extracted_at,
        -- Hesaplanan alanlar
        quantity * unit_price as calculated_total,
        -- Veri kalite kontrolleri
        CASE 
            WHEN quantity > 0 AND unit_price > 0 THEN TRUE
            ELSE FALSE 
        END as has_valid_amounts,
        CASE 
            WHEN product_name IS NULL OR TRIM(product_name) = '' THEN FALSE
            ELSE TRUE 
        END as has_valid_product,
        -- Tarih bazlı alanlar
        EXTRACT(year FROM order_date) as order_year,
        EXTRACT(month FROM order_date) as order_month,
        EXTRACT(quarter FROM order_date) as order_quarter,
        TO_CHAR(order_date, 'YYYY-MM') as order_year_month
    FROM {{ source('raw', 'erp_orders') }}
)

SELECT 
    order_id,
    customer_id,
    product_name_clean as product_name,
    quantity,
    unit_price,
    calculated_total as total_amount,
    order_date,
    extracted_at,
    has_valid_amounts,
    has_valid_product,
    order_year,
    order_month,
    order_quarter,
    order_year_month,
    -- Sipariş kategorileri
    CASE 
        WHEN calculated_total < 1000 THEN 'Küçük Sipariş'
        WHEN calculated_total < 10000 THEN 'Orta Sipariş'
        ELSE 'Büyük Sipariş'
    END as order_category
FROM cleaned_orders
WHERE has_valid_amounts AND has_valid_product