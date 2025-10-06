-- Executive dashboard için ana metrikler
{{ config(materialized='table') }}

SELECT 
    'Toplam Müşteri Sayısı' as metric_name,
    COUNT(DISTINCT customer_id)::text as metric_value,
    'Adet' as unit,
    CURRENT_DATE as calculation_date
FROM {{ ref('int_customer_metrics') }}

UNION ALL

SELECT 
    'Toplam Gelir',
    TO_CHAR(SUM(total_revenue), 'FM999,999,999.00'),
    'TL',
    CURRENT_DATE
FROM {{ ref('int_customer_metrics') }}

UNION ALL

SELECT 
    'Ortalama Sipariş Değeri',
    TO_CHAR(AVG(avg_order_value), 'FM999,999.00'),
    'TL',
    CURRENT_DATE
FROM {{ ref('int_customer_metrics') }}
WHERE total_orders > 0

UNION ALL

SELECT 
    'Aktif Müşteri Oranı',
    ROUND(
        COUNT(CASE WHEN customer_status = 'Aktif' THEN 1 END) * 100.0 / COUNT(*), 2
    )::text || '%',
    'Yüzde',
    CURRENT_DATE
FROM {{ ref('int_customer_metrics') }}

UNION ALL

SELECT 
    'Toplam Sipariş Sayısı',
    SUM(total_orders)::text,
    'Adet', 
    CURRENT_DATE
FROM {{ ref('int_customer_metrics') }}