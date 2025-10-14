-- Executive dashboard için ana metrikler
{{ config(materialized='table') }}

SELECT 
    'Toplam Müşteri Sayısı' as metric_name,
    COALESCE(COUNT(DISTINCT customer_id)::text, '0') as metric_value,
    'Adet' as unit,
    CURRENT_DATE as calculation_date
FROM {{ ref('int_customer_metrics') }}

UNION ALL

SELECT 
    'Toplam Gelir',
    COALESCE(TO_CHAR(SUM(total_revenue), 'FM999,999,999.00'), '0'),
    'TL',
    CURRENT_DATE
FROM {{ ref('int_customer_metrics') }}

UNION ALL

SELECT 
    'Ortalama Sipariş Değeri',
    CASE 
        WHEN COUNT(*) > 0 AND COUNT(CASE WHEN total_orders > 0 THEN 1 END) > 0 THEN
            COALESCE(TO_CHAR(AVG(CASE WHEN total_orders > 0 THEN avg_order_value END), 'FM999,999.00'), '0')
        ELSE '0'
    END,
    'TL',
    CURRENT_DATE
FROM {{ ref('int_customer_metrics') }}

UNION ALL

SELECT 
    'Aktif Müşteri Oranı',
    CASE 
        WHEN COUNT(*) > 0 THEN 
            COALESCE(ROUND(
                COUNT(CASE WHEN customer_status = 'Aktif' THEN 1 END) * 100.0 / COUNT(*), 2
            )::text || '%', '0%')
        ELSE '0%'
    END,
    'Yüzde',
    CURRENT_DATE
FROM {{ ref('int_customer_metrics') }}

UNION ALL

SELECT 
    'Toplam Sipariş Sayısı',
    COALESCE(SUM(total_orders)::text, '0'),
    'Adet', 
    CURRENT_DATE
FROM {{ ref('int_customer_metrics') }}