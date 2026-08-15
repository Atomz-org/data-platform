with

loyalty_members as (

    select * from {{ ref('dim_loyalty_members') }}

)

select
    loyalty_member_id,
    customer_id,
    current_tier_name,
    current_points_balance,
    enrolled_at,
    membership_status,
    current_timestamp as synced_at,
    'recce_dw' as source_system

from loyalty_members
where membership_status = 'active'
