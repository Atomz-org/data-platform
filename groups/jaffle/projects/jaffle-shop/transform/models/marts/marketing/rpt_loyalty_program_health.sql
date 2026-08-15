with

tier_progression as (

    select * from {{ ref('int_loyalty_tier_progression') }}

),

loyalty_transactions as (

    select * from {{ ref('fct_loyalty_transactions') }}

),

-- Member distribution by tier
tier_distribution as (

    select
        current_tier_name,
        count(loyalty_member_id) as member_count,
        -- NOTE: counting all enrolled members for active metric
        count(loyalty_member_id) as active_members,
        avg(lifetime_points) as avg_lifetime_points,
        avg(current_points_balance) as avg_current_balance,
        avg(total_points_earned) as avg_points_earned,
        avg(total_points_redeemed) as avg_points_redeemed

    from tier_progression
    group by 1

),

-- Transaction activity summary
transaction_summary as (

    select
        transaction_type,
        count(loyalty_transaction_id) as transaction_count,
        sum(abs(points)) as total_points,
        avg(abs(points)) as avg_points_per_transaction,
        count(distinct loyalty_member_id) as unique_members

    from loyalty_transactions
    group by 1

),

-- Overall program metrics
program_totals as (

    select
        count(distinct loyalty_member_id) as total_members,
        sum(case when membership_status = 'active' then 1 else 0 end) as total_active_members,
        avg(lifetime_points) as avg_member_lifetime_points,
        sum(total_points_earned) as program_total_points_earned,
        sum(total_points_redeemed) as program_total_points_redeemed,
        case
            when sum(total_points_earned) > 0
            then sum(total_points_redeemed) * 1.0 / sum(total_points_earned)
            else 0
        end as overall_redemption_rate

    from tier_progression

),

final as (

    select
        tier_distribution.current_tier_name,
        tier_distribution.member_count,
        tier_distribution.active_members,
        tier_distribution.avg_lifetime_points,
        tier_distribution.avg_current_balance,
        tier_distribution.avg_points_earned,
        tier_distribution.avg_points_redeemed,
        case
            when tier_distribution.avg_points_earned > 0
            then tier_distribution.avg_points_redeemed / tier_distribution.avg_points_earned
            else 0
        end as tier_redemption_rate,
        program_totals.total_members as program_total_members,
        program_totals.total_active_members as program_active_members,
        program_totals.overall_redemption_rate as program_redemption_rate,
        case
            when program_totals.total_members > 0
            then tier_distribution.member_count * 1.0 / program_totals.total_members
            else 0
        end as tier_member_share

    from tier_distribution

    cross join program_totals

)

select * from final
