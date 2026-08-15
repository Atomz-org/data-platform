-- adv_consecutive_growth.sql
-- Technique: Islands and Gaps with Window Functions
-- Finds the longest streak of consecutive month-over-month revenue growth per store.
-- Uses the classic "conditional running count" technique: when growth stops, the
-- counter resets, creating groups of consecutive growth months.

with daily_orders as (

    select * from {{ ref('int_daily_orders_by_store') }}

),

-- Aggregate to monthly revenue per store
monthly_revenue as (

    select
        location_id,
        location_name,
        {{ dbt.date_trunc('month', 'order_date') }} as revenue_month,
        sum(total_revenue) as monthly_revenue
    from daily_orders
    group by 1, 2, 3

),

-- Calculate month-over-month change
with_mom_change as (

    select
        *,
        lag(monthly_revenue) over (
            partition by location_id
            order by revenue_month
        ) as prev_month_revenue,
        case
            when monthly_revenue > lag(monthly_revenue) over (
                partition by location_id order by revenue_month
            ) then 1
            else 0
        end as is_growth
    from monthly_revenue

),

-- Islands and gaps: create streak groups.
-- Each time is_growth = 0, the running count of non-growth months increases,
-- and subtracting it from the row number creates a new group for each streak.
streak_groups as (

    select
        *,
        -- Count non-growth months up to this point; changes at each non-growth boundary
        sum(case when is_growth = 0 then 1 else 0 end) over (
            partition by location_id
            order by revenue_month
            rows between unbounded preceding and current row
        ) as non_growth_counter
    from with_mom_change

),

-- Measure each growth streak
streak_lengths as (

    select
        location_id,
        location_name,
        non_growth_counter as streak_group,
        min(revenue_month) as streak_start_month,
        max(revenue_month) as streak_end_month,
        count(*) as streak_length_months,
        min(monthly_revenue) as min_monthly_revenue,
        max(monthly_revenue) as max_monthly_revenue,
        sum(monthly_revenue) as streak_total_revenue
    from streak_groups
    where is_growth = 1
    group by 1, 2, 3

),

-- Rank streaks to find the longest per store
ranked_streaks as (

    select
        *,
        row_number() over (
            partition by location_id
            order by streak_length_months desc, streak_start_month
        ) as streak_rank
    from streak_lengths

)

select
    location_id,
    location_name,
    streak_start_month,
    streak_end_month,
    streak_length_months,
    min_monthly_revenue,
    max_monthly_revenue,
    streak_total_revenue,
    streak_rank
from ranked_streaks
-- Show top 3 longest streaks per store
where streak_rank <= 3
order by location_id, streak_rank
