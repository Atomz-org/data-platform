with

monthly_store as (
    select month_start, location_id, monthly_revenue
    from {{ ref('met_monthly_revenue_by_store') }}
),

with_growth as (
    select
        month_start,
        location_id,
        monthly_revenue,
        lag(monthly_revenue) over (partition by location_id order by month_start) as prior_month,
        round((monthly_revenue - lag(monthly_revenue) over (partition by location_id order by month_start)) * 100.0
            / nullif(lag(monthly_revenue) over (partition by location_id order by month_start), 0), 2) as growth_pct
    from monthly_store
),

ranked as (
    select
        month_start,
        location_id,
        monthly_revenue,
        growth_pct,
        rank() over (partition by month_start order by growth_pct desc) as growth_rank,
        ntile(4) over (partition by month_start order by growth_pct desc) as growth_quartile
    from with_growth
    where growth_pct is not null
)

select * from ranked
