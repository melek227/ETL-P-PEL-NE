-- Müşteri bazlı sipariş metrikleri
{{ config(materialized='view') }}

SELECT 
    c.customer_id,
    c.customer_name,
    c.email,
    c.city,
    c.customer_segment,
    c.registration_date,
    
    -- Sipariş metrikleri
    COUNT(o.order_id) as total_orders,
    COALESCE(SUM(o.total_amount), 0) as total_revenue,
    COALESCE(AVG(o.total_amount), 0) as avg_order_value,
    COALESCE(MAX(o.total_amount), 0) as max_order_value,
    COALESCE(MIN(o.total_amount), 0) as min_order_value,
    
    -- Tarih metrikleri
    MIN(o.order_date) as first_order_date,
    MAX(o.order_date) as last_order_date,
    
    -- Müşteri aktivite durumu
    CASE 
        WHEN MAX(o.order_date) >= CURRENT_DATE - INTERVAL '30 days' THEN 'Aktif'
        WHEN MAX(o.order_date) >= CURRENT_DATE - INTERVAL '90 days' THEN 'Risk'
        ELSE 'Pasif'
    END as customer_status,
    
    -- Sipariş kategorisi dağılımı
    COUNT(CASE WHEN o.order_category = 'Büyük Sipariş' THEN 1 END) as big_orders_count,
    COUNT(CASE WHEN o.order_category = 'Orta Sipariş' THEN 1 END) as medium_orders_count,
    COUNT(CASE WHEN o.order_category = 'Küçük Sipariş' THEN 1 END) as small_orders_count

FROM {{ ref('stg_crm_customers') }} c
LEFT JOIN {{ ref('stg_erp_orders') }} o ON c.customer_id = o.customer_id
GROUP BY 
    c.customer_id, c.customer_name, c.email, c.city, 
    c.customer_segment, c.registration_date