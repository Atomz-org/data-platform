with 
r as (
    select * from {{ ref('met_monthly_revenue_by_store') }}
),

l as (
    select * from {{ ref('met_monthly_labor_metrics') }}
),

final as (
    select
        l.month_start,
        l.location_id,
        l.monthly_labor_cost,
        r.monthly_revenue,
        round(monthly_labor_cost * 100.0 / nullif(r.monthly_revenue, 0), 2) as labor_cost_ratio
    from l
    inner join r
        on l.month_start = r.month_start and l.location_id = r.location_id
)
select * from final
