with

daily_revenue as (
    select
        revenue_date,
        location_id,
        total_revenue,
        avg(total_revenue) over (
            partition by location_id order by revenue_date
            rows between 7 preceding and 1 preceding
        ) as revenue_7d_avg
    from {{ ref('met_daily_revenue_by_store') }}
),

alerts as (
    select
        revenue_date,
        location_id,
        total_revenue,
        revenue_7d_avg,
        round((revenue_7d_avg - total_revenue) * 100.0 / nullif(revenue_7d_avg, 0), 2) as drop_pct,
        'revenue_drop_daily' as alert_type,
        case
            when (revenue_7d_avg - total_revenue) * 100.0 / nullif(revenue_7d_avg, 0) > 30 then 'critical'
            when (revenue_7d_avg - total_revenue) * 100.0 / nullif(revenue_7d_avg, 0) > 15 then 'warning'
            else 'info'
        end as severity
    from daily_revenue
    where total_revenue < revenue_7d_avg * 0.85
      and revenue_7d_avg > 0
)

select * from alerts
