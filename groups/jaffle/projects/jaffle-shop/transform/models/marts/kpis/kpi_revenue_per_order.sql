with monthly as (
    select month_start, sum(monthly_revenue) as monthly_revenue, sum(monthly_orders) as total_orders
    from {{ ref('met_monthly_revenue_by_store') }}
    group by 1
),
final as (
    select
        month_start,
        monthly_revenue,
        total_orders,
        round(monthly_revenue * 1.0 / nullif(total_orders, 0), 2) as revenue_per_order,
        lag(round(monthly_revenue * 1.0 / nullif(total_orders, 0), 2)) over (order by month_start) as prior_month_rpo
    from monthly
)
select * from final
