with

customer_360 as (

    select * from {{ ref('dim_customer_360') }}

)

select
    customer_id,
    customer_name,
    lifetime_spend,
    total_orders,
    ltv_tier,
    preferred_store_id,
    'high_value' as email_segment,
    current_timestamp as exported_at

from customer_360
where ltv_tier = 'high_value'
