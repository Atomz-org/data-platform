with

loyalty_members as (

    select * from {{ ref('stg_loyalty_members') }}

),

loyalty_tiers as (

    select * from {{ ref('stg_loyalty_tiers') }}

),

points_balance as (

    select * from {{ ref('int_loyalty_points_balance') }}

),

-- Determine each member's earned tier based on current points
member_tier_status as (

    select
        loyalty_members.loyalty_member_id,
        loyalty_members.customer_id,
        loyalty_members.membership_status,
        loyalty_members.enrolled_at,
        loyalty_members.last_activity_at,
        loyalty_members.lifetime_points,
        coalesce(points_balance.current_points_balance, 0) as current_points_balance,
        coalesce(points_balance.total_points_earned, 0) as total_points_earned,
        coalesce(points_balance.total_points_redeemed, 0) as total_points_redeemed,
        -- Current assigned tier
        current_tier.tier_id as current_tier_id,
        current_tier.tier_name as current_tier_name,
        current_tier.points_multiplier as current_multiplier,
        -- Earned tier based on lifetime points
        earned_tier.tier_id as earned_tier_id,
        earned_tier.tier_name as earned_tier_name,
        -- Next tier info
        next_tier.tier_id as next_tier_id,
        next_tier.tier_name as next_tier_name,
        next_tier.minimum_points as next_tier_min_points,
        case
            when next_tier.minimum_points is not null
            then next_tier.minimum_points - loyalty_members.lifetime_points
            else null
        end as points_to_next_tier

    from loyalty_members

    left join points_balance
        on loyalty_members.loyalty_member_id = points_balance.loyalty_member_id

    -- Current assigned tier
    left join loyalty_tiers as current_tier
        on loyalty_members.current_tier_id = current_tier.tier_id

    -- Earned tier based on lifetime points
    left join loyalty_tiers as earned_tier
        on loyalty_members.lifetime_points >= earned_tier.minimum_points
        and (
            loyalty_members.lifetime_points <= earned_tier.maximum_points
            or earned_tier.maximum_points is null
        )

    -- Next tier up
    left join loyalty_tiers as next_tier
        on earned_tier.maximum_points is not null
        and next_tier.minimum_points = earned_tier.maximum_points + 1

)

select * from member_tier_status
