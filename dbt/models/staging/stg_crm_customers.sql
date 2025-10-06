-- Staging CRM data - temizleme ve standardizasyon
{{ config(materialized='view') }}

WITH cleaned_customers AS (
    SELECT 
        customer_id,
        UPPER(TRIM(customer_name)) as customer_name_clean,
        LOWER(TRIM(email)) as email_clean,
        TRIM(phone) as phone_clean,
        UPPER(TRIM(city)) as city_clean,
        LOWER(TRIM(status)) as status_clean,
        registration_date,
        extracted_at,
        -- Veri kalite flagleri
        CASE 
            WHEN customer_name IS NULL OR TRIM(customer_name) = '' THEN FALSE
            ELSE TRUE 
        END as has_valid_name,
        CASE 
            WHEN email IS NULL OR email NOT LIKE '%@%' THEN FALSE
            ELSE TRUE 
        END as has_valid_email,
        -- Kayıt yaşı (gün olarak)
        EXTRACT(days FROM (CURRENT_DATE - registration_date::date)) as days_since_registration
    FROM {{ source('raw', 'crm_customers') }}
)

SELECT 
    customer_id,
    customer_name_clean as customer_name,
    email_clean as email,
    phone_clean as phone,  
    city_clean as city,
    status_clean as status,
    registration_date,
    extracted_at,
    has_valid_name,
    has_valid_email,
    days_since_registration,
    -- Müşteri segmentasyonu
    CASE 
        WHEN days_since_registration < 30 THEN 'Yeni Müşteri'
        WHEN days_since_registration < 365 THEN 'Aktif Müşteri' 
        ELSE 'Eski Müşteri'
    END as customer_segment
FROM cleaned_customers