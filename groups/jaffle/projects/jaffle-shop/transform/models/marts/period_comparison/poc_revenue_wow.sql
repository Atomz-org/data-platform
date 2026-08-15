with

weekly_revenue as (
    select
        week_start,
        location_id,
        weekly_revenue,
        weekly_orders
    from {{ ref('met_weekly_revenue_by_store') }}
),

compared as (
    select
        week_start,
        location_id,
        weekly_revenue as current_revenue,
        lag(weekly_revenue) over (partition by location_id order by week_start) as prior_week_revenue,
        weekly_orders as current_orders,
        lag(weekly_orders) over (partition by location_id order by week_start) as prior_week_orders,
        weekly_revenue - lag(weekly_revenue) over (partition by location_id order by week_start) as revenue_change,
        round((weekly_revenue - lag(weekly_revenue) over (partition by location_id order by week_start)) * 100.0
            / nullif(lag(weekly_revenue) over (partition by location_id order by week_start), 0), 2) as revenue_change_pct,
        case
            when weekly_revenue > lag(weekly_revenue) over (partition by location_id order by week_start) then 'up'
            when weekly_revenue < lag(weekly_revenue) over (partition by location_id order by week_start) then 'down'
            else 'flat'
        end as revenue_direction
    from weekly_revenue
)

select * from compared
