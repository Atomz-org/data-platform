with 
r as (
    select * from {{ ref('int_daily_revenue') }}
),

w as (
    select * from {{ ref('met_daily_waste_metrics') }}
),

l as (
    select * from {{ ref('int_labor_cost_daily') }}
),

final as (
    select
        r.revenue_date as waste_date,
        r.location_id,
        r.total_revenue,
        r.invoice_count,
        round(r.total_revenue * 1.0 / nullif(r.invoice_count, 0), 2) as avg_order_value,
        coalesce(l.total_labor_cost, 0) as labor_cost,
        coalesce(w.total_waste_cost, 0) as waste_cost,
        r.total_revenue - coalesce(l.total_labor_cost, 0) - coalesce(w.total_waste_cost, 0) as net_contribution
    from r
    left join l
        on r.revenue_date = l.work_date and r.location_id = l.location_id
    left join w
        on r.revenue_date = w.waste_date and r.location_id = w.location_id
)
select * from final
