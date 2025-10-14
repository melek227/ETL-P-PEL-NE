-- Staging CRM data - temizleme ve standardizasyon
{{ config(materialized='view') }}

WITH cleaned_customers AS (
    SELECT 
        customer_id,
        UPPER(TRIM(customer_name)) AS customer_name_clean,
        LOWER(TRIM(email)) AS email_clean,
        TRIM(phone) AS phone_clean,
        UPPER(TRIM(city)) AS city_clean,
        LOWER(TRIM(status)) AS status_clean,
        registration_date,
        extracted_at,

        -- Veri kalite flagleri
        CASE 
            WHEN customer_name IS NULL OR TRIM(customer_name) = '' THEN FALSE
            ELSE TRUE 
        END AS has_valid_name,

        CASE 
            WHEN email IS NULL OR email NOT LIKE '%@%' THEN FALSE
            ELSE TRUE 
        END AS has_valid_email,

        -- Kayıt yaşı (gün olarak)
        (CURRENT_DATE - registration_date::date) AS days_since_registration

    FROM {{ source('raw', 'crm_customers') }}
)

SELECT 
    customer_id,
    customer_name_clean AS customer_name,
    email_clean AS email,
    phone_clean AS phone,  
    city_clean AS city,
    status_clean AS status,
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
    END AS customer_segment

FROM cleaned_customers
