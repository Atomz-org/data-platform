with

total_revenue as (

    select * from {{ ref('met_daily_revenue_by_store') }}

),

zone_performance as (

    select
        location_id,
        {{ dbt.date_trunc('month', 'revenue_date') }} as performance_month,
        sum(total_revenue) as zone_revenue,
        count(distinct revenue_date) as active_days,
        avg(total_revenue) as avg_total_revenue,
        min(total_revenue) as min_total_revenue,
        max(total_revenue) as max_total_revenue

    from total_revenue
    group by location_id, {{ dbt.date_trunc('month', 'revenue_date') }}

)

select
    location_id,
    performance_month,
    zone_revenue,
    active_days,
    avg_total_revenue,
    min_total_revenue,
    max_total_revenue,
    round(max_total_revenue - min_total_revenue, 2) as total_revenue_range,
    round(zone_revenue / nullif(active_days, 0), 2) as revenue_per_active_day

from zone_performance
