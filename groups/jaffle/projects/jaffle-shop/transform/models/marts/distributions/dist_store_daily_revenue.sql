with

daily_rev as (
    select location_id, revenue_date, total_revenue
    from {{ ref('met_daily_revenue_by_store') }}
),

per_store as (
    select
        location_id,
        count(*) as active_days,
        round(avg(total_revenue), 2) as mean_daily_rev,
        round(percentile_cont(0.25) within group (order by total_revenue), 2) as p25_rev,
        round(percentile_cont(0.50) within group (order by total_revenue), 2) as median_rev,
        round(percentile_cont(0.75) within group (order by total_revenue), 2) as p75_rev,
        round(percentile_cont(0.90) within group (order by total_revenue), 2) as p90_rev,
        round(min(total_revenue), 2) as min_rev,
        round(max(total_revenue), 2) as max_rev
    from daily_rev
    group by 1
)

select * from per_store
