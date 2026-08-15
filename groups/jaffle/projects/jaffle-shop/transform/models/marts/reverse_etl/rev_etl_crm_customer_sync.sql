with

customer_360 as (

    select * from {{ ref('dim_customer_360') }}

)

select
    customer_id,
    customer_name,
    ltv_tier,
    lifetime_spend,
    total_orders,
    first_order_at,
    last_order_at,
    preferred_store_id,
    rfm_total_score,
    current_timestamp as synced_at,
    'recce_dw' as source_system

from customer_360
