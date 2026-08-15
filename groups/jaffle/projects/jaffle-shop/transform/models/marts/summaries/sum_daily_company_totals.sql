with

revenue as (
    select revenue_date, sum(total_revenue) as total_revenue, sum(order_count) as total_orders
    from {{ ref('met_daily_revenue_by_store') }}
    group by 1
),

labor as (
    select work_date, sum(total_labor_cost) as total_labor_cost, sum(total_labor_hours) as total_labor_hours
    from {{ ref('met_daily_labor_metrics') }}
    group by 1
),

waste as (
    select waste_date, sum(total_waste_cost) as total_waste_cost
    from {{ ref('met_daily_waste_metrics') }}
    group by 1
),

final as (
    select
        r.revenue_date as report_date,
        r.total_revenue,
        r.total_orders,
        round(r.total_revenue * 1.0 / nullif(r.total_orders, 0), 2) as avg_order_value,
        coalesce(l.total_labor_cost, 0) as total_labor_cost,
        coalesce(l.total_labor_hours, 0) as total_labor_hours,
        coalesce(w.total_waste_cost, 0) as total_waste_cost,
        round(coalesce(l.total_labor_cost, 0) * 100.0 / nullif(r.total_revenue, 0), 2) as labor_cost_pct,
        round(coalesce(w.total_waste_cost, 0) * 100.0 / nullif(r.total_revenue, 0), 2) as waste_cost_pct
    from revenue as r
    left join labor as l on r.revenue_date = l.work_date
    left join waste as w on r.revenue_date = w.waste_date
)

select * from final
