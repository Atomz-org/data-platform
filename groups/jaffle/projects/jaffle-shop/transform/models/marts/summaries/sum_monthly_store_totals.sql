with 
r as (
    select * from {{ ref('met_monthly_revenue_by_store') }}
),

w as (
    select * from {{ ref('met_monthly_waste_metrics') }}
),

l as (
    select * from {{ ref('met_monthly_labor_metrics') }}
),

final as (
    select
        r.month_start,
        r.location_id,
        r.monthly_revenue,
        r.monthly_orders,
        round(r.monthly_revenue * 1.0 / nullif(r.monthly_orders, 0), 2) as avg_order_value,
        coalesce(l.monthly_labor_cost, 0) as labor_cost,
        coalesce(w.monthly_waste_cost, 0) as waste_cost,
        r.monthly_revenue - coalesce(l.monthly_labor_cost, 0) - coalesce(w.monthly_waste_cost, 0) as net_contribution,
        lag(r.monthly_revenue) over (partition by r.location_id order by r.month_start) as prior_month_revenue
    from r
    left join l
        on r.month_start = l.month_start and r.location_id = l.location_id
    left join w
        on r.month_start = w.month_start and r.location_id = w.location_id
)
select * from final
