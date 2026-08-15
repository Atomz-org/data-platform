with

weekly_orders as (
    select
        week_start,
        location_id,
        weekly_orders,
        weekly_revenue
    from {{ ref('met_weekly_revenue_by_store') }}
),

compared as (
    select
        week_start,
        location_id,
        weekly_orders as current_orders,
        lag(weekly_orders) over (partition by location_id order by week_start) as prior_week_orders,
        weekly_orders - lag(weekly_orders) over (partition by location_id order by week_start) as orders_change,
        round((weekly_orders - lag(weekly_orders) over (partition by location_id order by week_start)) * 100.0
            / nullif(lag(weekly_orders) over (partition by location_id order by week_start), 0), 2) as orders_change_pct,
        round(weekly_revenue * 1.0 / nullif(weekly_orders, 0), 2) as current_aov,
        round(lag(weekly_revenue) over (partition by location_id order by week_start) * 1.0
            / nullif(lag(weekly_orders) over (partition by location_id order by week_start), 0), 2) as prior_aov
    from weekly_orders
)

select * from compared
