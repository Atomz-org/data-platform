select count(distinct customer_id) as total_customers from {{ ref('stg_customers') }}
