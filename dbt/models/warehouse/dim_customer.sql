-- Customer Dimension Table
{{ config(materialized='table') }}

SELECT
    customer_id,
    customer_name,
    email,
    city,
    customer_segment,
    registration_date
FROM {{ ref('int_customer_cleaned') }}
WHERE customer_id IS NOT NULL