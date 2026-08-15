with

members as (
    select * from {{ ref('stg_loyalty_members') }}
),

tiers as (
    select tier_id, tier_name, minimum_points, maximum_points from {{ ref('stg_loyalty_tiers') }}
),

final as (
    select
        m.loyalty_member_id,
        m.customer_id,
        m.current_tier_id,
        t.tier_name,
        t.minimum_points,
        t.maximum_points,
        m.enrolled_at,
        m.membership_status
    from members as m
    left join tiers as t on m.current_tier_id = t.tier_id
)

select * from final
