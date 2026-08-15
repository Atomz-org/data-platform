with

weekly_revenue as (
    select
        week_start,
        location_id,
        weekly_revenue,
        weekly_orders
    from {{ ref('met_weekly_revenue_by_store') }}
),

trended as (
    select
        week_start,
        location_id,
        weekly_revenue,
        weekly_orders,
        round(weekly_revenue * 1.0 / nullif(weekly_orders, 0), 2) as aov,
        avg(round(weekly_revenue * 1.0 / nullif(weekly_orders, 0), 2)) over (
            partition by location_id order by week_start
            rows between 3 preceding and current row
        ) as aov_4w_ma,
        round(weekly_revenue * 1.0 / nullif(weekly_orders, 0), 2) - lag(
            round(weekly_revenue * 1.0 / nullif(weekly_orders, 0), 2)
        ) over (partition by location_id order by week_start) as aov_wow_change
    from weekly_revenue
)

select * from trended
