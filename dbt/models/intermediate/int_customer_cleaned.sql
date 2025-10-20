-- Temizlenmiş müşteri tablosu (Intermediate)
{{ config(materialized='view') }}

SELECT
    customer_id,
    UPPER(TRIM(customer_name)) AS customer_name,
    LOWER(TRIM(email)) AS email,
    UPPER(TRIM(city)) AS city,
    customer_segment,
    registration_date
FROM {{ ref('stg_crm_customers') }}
WHERE customer_id IS NOT NULL
  AND customer_name IS NOT NULL
  AND email IS NOT NULL