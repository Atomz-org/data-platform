with

weekly_rev as (
    select
        {{ sf_date_trunc('week', "revenue_date") }} as week_start,
        sum(total_revenue) as total_revenue,
        sum(order_count) as total_orders
    from {{ ref('met_daily_revenue_by_store') }}
    group by 1
),

weekly_labor as (
    select
        {{ sf_date_trunc('week', "work_date") }} as week_start,
        sum(total_labor_cost) as total_labor_cost
    from {{ ref('met_daily_labor_metrics') }}
    group by 1
),

final as (
    select
        r.week_start,
        r.total_revenue,
        r.total_orders,
        round(r.total_revenue * 1.0 / nullif(r.total_orders, 0), 2) as avg_order_value,
        coalesce(l.total_labor_cost, 0) as total_labor_cost,
        round(coalesce(l.total_labor_cost, 0) * 100.0 / nullif(r.total_revenue, 0), 2) as labor_cost_pct,
        lag(r.total_revenue) over (order by r.week_start) as prior_week_revenue,
        round((r.total_revenue - lag(r.total_revenue) over (order by r.week_start)) * 100.0
            / nullif(lag(r.total_revenue) over (order by r.week_start), 0), 2) as wow_revenue_change_pct
    from weekly_rev as r
    left join weekly_labor as l on r.week_start = l.week_start
)

select * from final
