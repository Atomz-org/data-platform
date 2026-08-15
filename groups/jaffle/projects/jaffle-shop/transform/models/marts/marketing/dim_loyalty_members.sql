with

loyalty_members as (

    select * from {{ ref('stg_loyalty_members') }}

),

tier_progression as (

    select * from {{ ref('int_loyalty_tier_progression') }}

),

final as (

    select
        loyalty_members.loyalty_member_id,
        loyalty_members.customer_id,
        loyalty_members.membership_status,
        loyalty_members.lifetime_points,
        loyalty_members.enrolled_at,
        loyalty_members.last_activity_at,

        -- Tier details from progression
        tier_progression.current_tier_name,
        tier_progression.current_multiplier,
        tier_progression.earned_tier_name,
        tier_progression.next_tier_name,
        tier_progression.points_to_next_tier,
        tier_progression.current_points_balance,
        tier_progression.total_points_earned,
        tier_progression.total_points_redeemed,

        -- Derived fields
        case
            when loyalty_members.membership_status = 'active' then true
            else false
        end as is_active_member,
        case
            when tier_progression.current_tier_name != tier_progression.earned_tier_name
            then true
            else false
        end as is_tier_mismatched

    from loyalty_members

    left join tier_progression
        on loyalty_members.loyalty_member_id = tier_progression.loyalty_member_id

)

select * from final
