with

monthly_rev as (
    select month_start, sum(monthly_revenue) as monthly_revenue, sum(monthly_orders) as total_orders
    from {{ ref('met_monthly_revenue_by_store') }}
    group by 1
),

monthly_labor as (
    select month_start, sum(monthly_labor_cost) as monthly_labor_cost, sum(monthly_labor_hours) as monthly_labor_hours
    from {{ ref('met_monthly_labor_metrics') }}
    group by 1
),

monthly_waste as (
    select month_start, sum(monthly_waste_cost) as monthly_waste_cost
    from {{ ref('met_monthly_waste_metrics') }}
    group by 1
),

final as (
    select
        r.month_start as month_start,
        r.monthly_revenue,
        r.total_orders,
        round(r.monthly_revenue * 1.0 / nullif(r.total_orders, 0), 2) as avg_order_value,
        coalesce(l.monthly_labor_cost, 0) as monthly_labor_cost,
        coalesce(l.monthly_labor_hours, 0) as total_labor_hours,
        coalesce(w.monthly_waste_cost, 0) as monthly_waste_cost,
        r.monthly_revenue - coalesce(l.monthly_labor_cost, 0) - coalesce(w.monthly_waste_cost, 0) as operating_income_proxy,
        lag(r.monthly_revenue) over (order by r.month_start) as prior_month_revenue,
        round((r.monthly_revenue - lag(r.monthly_revenue) over (order by r.month_start)) * 100.0
            / nullif(lag(r.monthly_revenue) over (order by r.month_start), 0), 2) as mom_revenue_change_pct
    from monthly_rev as r
    left join monthly_labor as l on r.month_start = l.month_start
    left join monthly_waste as w on r.month_start = w.month_start
)

select * from final
