with

customer_360 as (

    select * from {{ ref('dim_customer_360') }}

)

select
    customer_id,
    customer_name,
    first_order_at,
    total_orders,
    lifetime_spend,
    preferred_store_id,
    'new_customer' as email_segment,
    current_timestamp as exported_at

from customer_360
where first_order_at >= current_date - interval '30 days'
