with

ml as (
    select * from {{ ref('met_monthly_labor_metrics') }}
),

mr as (
    select * from {{ ref('met_monthly_revenue_by_store') }}
),

monthly_efficiency as (
    select
        ml.month_start,
        ml.location_id,
        ml.monthly_labor_cost,
        mr.monthly_revenue,
        round(mr.monthly_revenue * 1.0 / nullif(ml.monthly_labor_cost, 0), 2) as revenue_per_labor_dollar
    from ml
    inner join mr
        on ml.month_start = mr.month_start and ml.location_id = mr.location_id
),

ranked as (
    select
        month_start,
        location_id,
        monthly_labor_cost,
        monthly_revenue,
        revenue_per_labor_dollar,
        rank() over (partition by month_start order by revenue_per_labor_dollar desc) as efficiency_rank,
        ntile(4) over (partition by month_start order by revenue_per_labor_dollar desc) as efficiency_quartile
    from monthly_efficiency
)

select * from ranked
