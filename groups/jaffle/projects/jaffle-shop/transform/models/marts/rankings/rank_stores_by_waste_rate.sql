with

mw as (
    select * from {{ ref('met_monthly_waste_metrics') }}
),

mr as (
    select * from {{ ref('met_monthly_revenue_by_store') }}
),

monthly_waste_rate as (
    select
        mw.month_start,
        mw.location_id,
        mw.monthly_waste_cost,
        mr.monthly_revenue,
        round(mw.monthly_waste_cost * 100.0 / nullif(mr.monthly_revenue, 0), 2) as waste_rate_pct
    from mw
    inner join mr
        on mw.month_start = mr.month_start and mw.location_id = mr.location_id
),

ranked as (
    select
        month_start,
        location_id,
        waste_rate_pct,
        monthly_waste_cost,
        rank() over (partition by month_start order by waste_rate_pct asc) as waste_rank_best_first,
        ntile(4) over (partition by month_start order by waste_rate_pct asc) as waste_quartile
    from monthly_waste_rate
)

select * from ranked
