with

weekly_revenue as (
    select
        week_start,
        location_id,
        weekly_revenue,
        lag(weekly_revenue) over (partition by location_id order by week_start) as prior_week_revenue
    from {{ ref('met_weekly_revenue_by_store') }}
),

alerts as (
    select
        week_start,
        location_id,
        weekly_revenue,
        prior_week_revenue,
        round((prior_week_revenue - weekly_revenue) * 100.0 / nullif(prior_week_revenue, 0), 2) as wow_drop_pct,
        'revenue_drop_weekly' as alert_type,
        'warning' as severity
    from weekly_revenue
    where weekly_revenue < prior_week_revenue * 0.85
      and prior_week_revenue > 0
)

select * from alerts
