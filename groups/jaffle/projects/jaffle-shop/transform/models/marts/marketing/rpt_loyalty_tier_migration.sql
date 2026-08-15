with

tier_progression as (

    select * from {{ ref('int_loyalty_tier_progression') }}

),

loyalty_transactions as (

    select * from {{ ref('fct_loyalty_transactions') }}

),

-- Monthly snapshots of member tier based on running balance
monthly_tier_snapshots as (

    select
        loyalty_member_id,
        {{ dbt.date_trunc('month', 'transacted_at') }} as activity_month,
        -- Use end-of-month running balance to determine tier
        max(running_points_balance) as month_end_balance

    from loyalty_transactions
    group by 1, 2

),

-- Assign tiers based on month-end points (simplified tier thresholds)
monthly_tiers as (

    select
        loyalty_member_id,
        activity_month,
        month_end_balance,
        case
            when month_end_balance >= 10000 then 'Platinum'
            when month_end_balance >= 5000 then 'Gold'
            when month_end_balance >= 1000 then 'Silver'
            else 'Bronze'
        end as monthly_tier

    from monthly_tier_snapshots

),

-- Compare each month to the previous month
tier_transitions as (

    select
        loyalty_member_id,
        activity_month,
        monthly_tier as current_month_tier,
        lag(monthly_tier) over (
            partition by loyalty_member_id
            order by activity_month
        ) as previous_month_tier,
        month_end_balance

    from monthly_tiers

),

-- Classify transitions
classified_transitions as (

    select
        activity_month,
        current_month_tier,
        previous_month_tier,
        loyalty_member_id,
        case
            when previous_month_tier is null then 'new_member'
            when current_month_tier = previous_month_tier then 'retained'
            when (
                case current_month_tier
                    when 'Platinum' then 4
                    when 'Gold' then 3
                    when 'Silver' then 2
                    else 1
                end
            ) > (
                case previous_month_tier
                    when 'Platinum' then 4
                    when 'Gold' then 3
                    when 'Silver' then 2
                    else 1
                end
            ) then 'upgraded'
            else 'downgraded'
        end as transition_type

    from tier_transitions

),

-- Aggregate migration flows per month
final as (

    select
        activity_month,
        previous_month_tier,
        current_month_tier,
        transition_type,
        count(distinct loyalty_member_id) as member_count

    from classified_transitions
    where previous_month_tier is not null
    group by 1, 2, 3, 4

)

select * from final
order by activity_month, previous_month_tier, current_month_tier
