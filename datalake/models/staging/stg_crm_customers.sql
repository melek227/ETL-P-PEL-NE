-- Staging model for CRM customer data
{{ config(materialized='view') }}

SELECT 
    customer_id,
    TRIM(first_name) as first_name,
    TRIM(last_name) as last_name,
    LOWER(TRIM(email)) as email,
    phone,
    address,
    city,
    state,
    zip_code,
    country,
    registration_date,
    last_activity_date,
    customer_status,
    customer_type,
    CURRENT_TIMESTAMP as loaded_at
FROM {{ source('crm', 'customers') }}
WHERE customer_id IS NOT NULL