with 
r as (
    select * from {{ ref('met_monthly_revenue_by_store') }}
),

l as (
    select * from {{ ref('met_monthly_labor_metrics') }}
),

final as (
    select
        r.month_start as metric_month,
        r.location_id,
        r.monthly_revenue,
        l.monthly_labor_hours,
        round(r.monthly_revenue * 1.0 / nullif(l.monthly_labor_hours, 0), 2) as revenue_per_labor_hour,
        r.monthly_orders,
        round(r.monthly_orders * 1.0 / nullif(l.monthly_labor_hours, 0), 2) as orders_per_labor_hour
    from r
    inner join l
        on r.month_start = l.month_start and r.location_id = l.location_id
)
select * from final
